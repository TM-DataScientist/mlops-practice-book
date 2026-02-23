# 訓練実験のメタデータを収集・保存するモジュール
# モデル設定・コマンドライン引数・実行環境（Git・依存パッケージ・計算リソース・ECS情報）を一括管理する
import argparse
import json
import logging
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib import metadata
from pathlib import Path

import psutil
import requests

from .model_config import ModelConfig

logger = logging.getLogger(__name__)


# 訓練実験の全メタデータを保持するデータクラス
# 実験の再現性追跡（Reproducibility Tracking）と後からの参照のために必要な情報を集約する
@dataclass
class MetaDeta:
    model_config: ModelConfig  # 使用したモデルの設定（スキーマ・ハイパーパラメータ等）
    command_lie_arguments: argparse.Namespace  # 実行時のコマンドライン引数
    version: str  # 実験バージョン（タイムスタンプ文字列）
    start_time: datetime  # 訓練開始時刻
    end_time: datetime  # 訓練終了時刻
    artifact_key_prefix: str  # S3 上のアーティファクト保存先のキープレフィックス

    # モデル名を model_config から取得するプロパティ
    @property
    def model_name(self) -> str:
        return self.model_config.name

    # 実行時の Git コミットハッシュ（短縮形）を取得するプロパティ
    # git コマンドが存在しない環境では None を返す
    @property
    def git_commit_hash(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logger.info("git command is not installed")
            return None

    # 実行時の Git ブランチ名を取得するプロパティ
    # git コマンドが存在しない環境では None を返す
    @property
    def git_branch(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logger.info("git command is not installed")
            return None

    # 実行環境の依存パッケージ一覧と Python 実行情報を返すプロパティ
    # インストール済み全パッケージのバージョンを記録することで環境の再現性を保証する
    @property
    def dependencies(self) -> dict[str, str | dict[str, str]]:
        return {
            # Python
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "python_path": sys.executable,
            # Packages
            "installed_packages": {dist.metadata["Name"]: dist.version for dist in metadata.distributions()},
        }

    # 実行環境の計算リソース情報（OS・CPU・メモリ）を返すプロパティ
    # クラウドとローカルで異なるリソースが使われた場合の比較に役立つ
    @property
    def compute_resource(self) -> dict[str, str | int | None]:
        return {
            # OS
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            # CPU
            "cpu_count": os.cpu_count(),
            "cpu_info": platform.processor(),
            # Memory
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
        }

    # ECS タスクのコンテナメタデータを取得するプロパティ
    # ECS 環境変数 ECS_CONTAINER_METADATA_URI_V4 が設定されている場合のみメタデータを取得する
    @property
    def ecs_task_metadata(self) -> dict[str, str] | None:
        ecs_container_metadata_uri = os.getenv("ECS_CONTAINER_METADATA_URI_V4")
        if ecs_container_metadata_uri is None:
            # ECS 以外の環境（ローカル等）では None を返す
            return None

        response = requests.get(ecs_container_metadata_uri)
        if response.status_code != 200:
            return None

        return json.loads(response.text)

    # ECS コンテナのイメージ URI を取得するプロパティ
    # ECS 環境外では None を返す
    @property
    def image_uri(self) -> str | None:
        if self.ecs_task_metadata is None:
            return None
        return self.ecs_task_metadata.get("ImageID")

    # メタデータをJSONファイルとして保存するメソッド
    # dataclass のフィールドに加えて、プロパティ経由で取得した実行環境情報も含めて保存する
    def save_as_json(self, output_path: Path) -> None:
        # dataclass を辞書に変換する（ネストされた dataclass も再帰的に変換される）
        metadata_dict = asdict(self)
        # argparse.Namespace は asdict で変換できないため文字列化する
        metadata_dict["command_lie_arguments"] = str(metadata_dict["command_lie_arguments"])
        # model_config のすべての値を文字列化する（JSON シリアライズできない型を含む場合があるため）
        metadata_dict["model_config"] = {k: str(v) for k, v in metadata_dict["model_config"].items()}
        # datetime を文字列フォーマットに変換する
        metadata_dict["start_time"] = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        metadata_dict["end_time"] = self.end_time.strftime("%Y-%m-%d %H:%M:%S")
        # プロパティ経由の値を辞書に追加する
        metadata_dict["git_commit_hash"] = self.git_commit_hash
        metadata_dict["git_branch"] = self.git_branch
        metadata_dict["dependencies"] = self.dependencies
        metadata_dict["compute_resource"] = self.compute_resource
        metadata_dict["ecs_task_metadata"] = self.ecs_task_metadata

        with open(output_path, "w") as f:
            json.dump(metadata_dict, f, indent=2)

        logger.info(f"Saved metadata. {metadata_dict=}")
