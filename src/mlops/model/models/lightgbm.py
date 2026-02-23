# LightGBM を使ったモデルクラスの実装
# BaseModel を継承し、LightGBM の勾配ブースティング木モデルで CTR を予測する
import logging
import tempfile
from pathlib import Path

import lightgbm as lgb
import numpy as np
import numpy.typing as npt
import pandas as pd

from mlops.aws import download_file_from_s3
from mlops.const import MODEL_S3_BUCKET

from .base_model import BaseModel, PdNpType

logger = logging.getLogger(__name__)


# LightGBM モデルのラッパークラス
# 訓練・推論・保存・S3 からのロードをサポートする
class LightGBMModel(BaseModel):
    def __init__(
        self,
        model: lgb.Booster | None = None,  # 訓練済みの Booster インスタンス（未訓練時は None）
        args: dict | None = None,  # LightGBM のハイパーパラメータ辞書
        num_round: int = 10,  # ブースティングの反復回数
    ) -> None:
        self.model = model
        if args is None:
            args = {}
        # ユーザー指定のパラメータに objective="binary" を強制的に追加する（二値分類タスクのため）
        self.args = args | {"objective": "binary"}
        self.num_round = num_round

    # LightGBM モデルを訓練するメソッド
    # カテゴリ型カラムを自動検出して LightGBM のネイティブカテゴリ処理に渡す
    def train(
        self,
        X_train: PdNpType,
        y_train: PdNpType,
        X_valid: PdNpType,
        y_valid: PdNpType,
    ) -> None:
        # DataFrame の場合は category 型のカラムを抽出して categorical_feature に指定する
        if isinstance(X_train, pd.DataFrame):
            category_columns = X_train.select_dtypes(include=["category"]).columns.tolist()
        # LightGBM 用のデータセット形式に変換する
        train_data = lgb.Dataset(
            X_train,
            label=y_train,
            categorical_feature=category_columns,
        )
        valid_data = lgb.Dataset(
            X_valid,
            label=y_valid,
            categorical_feature=category_columns,
        )
        # 検証データを使って早期終了可能な形で訓練する
        model = lgb.train(self.args, train_data, self.num_round, valid_sets=[valid_data])
        self.model = model

    # クリック確率を予測して NumPy 配列で返すメソッド
    def predict_proba(self, X: PdNpType) -> npt.NDArray:
        if self.model is None:
            raise ValueError("Model is not instantiated.")
        y_pred = np.asarray(self.model.predict(X))  # LightGBM の predict は直接確率を返す
        return y_pred

    # モデルを LightGBM 形式（テキスト形式）のファイルに保存するメソッド
    def save(self, file_path: Path) -> None:
        logger.info(f"Save model file at {file_path}.")
        if self.model is None:
            raise ValueError("Model is not instantiated.")
        self.model.save_model(file_path)

    # S3 からモデルファイルをダウンロードして LightGBMModel インスタンスを返すクラスメソッド
    # 一時ファイルを使ってダウンロードし、Booster に読み込んだ後に一時ファイルは自動削除される
    @classmethod
    def from_pretrained(
        cls,
        s3_key: str,
    ) -> "LightGBMModel":
        logger.info(f"Loading model from s3://{MODEL_S3_BUCKET}/{s3_key}")
        with tempfile.NamedTemporaryFile() as temp_file:
            download_file_from_s3(
                s3_bucket=MODEL_S3_BUCKET,
                s3_key=s3_key,
                file_path=temp_file.name,
            )
            # 一時ファイルからモデルを読み込む
            model = lgb.Booster(model_file=temp_file.name)
        return cls(model)
