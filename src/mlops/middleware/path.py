# アーティファクト（成果物）の保存パスを管理するミドルウェアモジュール
# ジョブタイプとバージョンからローカルディレクトリと S3 キープレフィックスを一元管理する
from pathlib import Path


# アーティファクトのパス管理クラス
# ローカルの保存ディレクトリと S3 のキープレフィックスを同一のバージョン文字列から生成することで
# ローカルと S3 のパス対応を保ちながら成果物を整理する
class Artifact:
    def __init__(self, version: str, job_type: str) -> None:
        # S3 アップロード時のキープレフィックス（例: "train/sgd_classifier_ctr/20240101120000"）
        self.key_prefix = f"{job_type}/{version}"
        # ローカルのアーティファクト保存ディレクトリ（存在しない場合は再帰的に作成する）
        self.dir_path = Path(f"./artifact/{self.key_prefix}")
        self.dir_path.mkdir(parents=True, exist_ok=True)

    # アーティファクトディレクトリ内の指定ファイル名の完全パスを返すメソッド
    def file_path(self, file_name: str) -> Path:
        return self.dir_path / file_name
