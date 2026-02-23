# SGD（確率的勾配降下法）分類器を使ったモデルクラスの実装
# FeatureHasher による高次元特徴量ハッシュ化と Optuna による正則化パラメータ自動チューニングを組み合わせる
import logging
import pickle
import tempfile
from pathlib import Path

import numpy as np
import numpy.typing as npt
import optuna
import pandas as pd
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import log_loss

from mlops.aws import download_file_from_s3
from mlops.const import MODEL_S3_BUCKET

from .base_model import BaseModel, PdNpType

logger = logging.getLogger(__name__)


# SGDClassifier を使った CTR 予測モデルのラッパークラス
# 訓練前にハッシュ化による特徴量変換を行い、Optuna でハイパーパラメータを探索する
class SGDClassifierModel(BaseModel):
    def __init__(
        self,
        model: SGDClassifier | None = None,  # 訓練済みの SGDClassifier インスタンス（未訓練時は None）
        is_optuna: bool = True,  # Optuna によるハイパーパラメータ探索を行うかどうか
        args: dict | None = None,  # SGDClassifier のハイパーパラメータ辞書
    ) -> None:
        self.model = model
        self.is_optuna = is_optuna
        self.args = args if args else {}

    # SGDClassifier モデルを訓練するメソッド
    # 特徴量をハッシュ化した後、Optuna で最適な alpha（正則化強度）を探索してから訓練する
    def train(
        self,
        X_train: PdNpType,
        y_train: PdNpType,
        X_valid: PdNpType,
        y_valid: PdNpType,
    ) -> None:
        # 文字列型に変換してからハッシュトリックで疎ベクトルに変換する
        X_train_hashed = hashing_feature(X_train)
        X_valid_hashed = hashing_feature(X_valid)
        _args = self.args
        if self.is_optuna:
            # Optuna で最適な正則化パラメータ alpha を探索する
            best_alpha = self._optuna_search(X_train_hashed, y_train, X_valid_hashed, y_valid)
            _args["alpha"] = best_alpha
        model = SGDClassifier(**_args)
        model.fit(X_train_hashed, y_train)
        self.model = model

    # クリック確率を予測して NumPy 配列で返すメソッド
    # 推論時も同じハッシュ変換を適用する必要がある
    def predict_proba(self, X: PdNpType) -> npt.NDArray:
        if self.model is None:
            raise ValueError("Model is not instantiated.")
        X_hashed = hashing_feature(X)
        # predict_proba の出力は [非クリック確率, クリック確率] の2列なので、クリック確率（[:,1]）を返す
        y_pred = self.model.predict_proba(X_hashed)[:, 1]
        return y_pred

    # モデルを pickle 形式でローカルファイルに保存するメソッド
    def save(self, file_path: Path) -> None:
        logger.info(f"Save model file at {file_path}.")
        if self.model is None:
            raise ValueError("Model is not instantiated.")

        with open(file_path, "wb") as f:
            pickle.dump(self.model, f)

    # Optuna を使って正則化パラメータ alpha の最適値を探索するプライベートメソッド
    # 検証データの LogLoss を最小化する alpha を10試行で探索して返す
    def _optuna_search(
        self,
        X_train: PdNpType,
        y_train: PdNpType,
        X_valid: PdNpType,
        y_valid: PdNpType,
    ) -> float:
        # Optuna のトライアル関数：alpha の候補値でモデルを訓練して検証 LogLoss を返す
        def objective(trial: optuna.trial._trial.Trial) -> float:
            max_alpha = 0.0001  # alpha の探索上限値
            alpha = trial.suggest_float("alpha", 0, max_alpha)  # 0〜0.0001 の範囲で alpha を提案
            model = SGDClassifier(loss="log_loss", penalty="l2", random_state=42, alpha=alpha)

            model.fit(X_train, y_train)
            y_pred = model.predict_proba(X_valid)[:, 1]
            score = log_loss(y_true=y_valid, y_pred=y_pred)

            return float(score)

        logger.info("Started Hyper Parameter by optuna")
        # LogLoss を最小化する方向で探索する（direction="minimize"）
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=10)  # 10回のトライアルで探索

        best_score = study.best_value
        best_alpha = study.best_params["alpha"]
        logger.info(f"Started Hyper Parameter by optuna. {best_alpha=}, {best_score=}")
        return best_alpha

    # S3 からモデルファイルをダウンロードして SGDClassifierModel インスタンスを返すクラスメソッド
    # pickle 形式で保存されたモデルを一時ファイル経由でロードする
    @classmethod
    def from_pretrained(
        cls,
        s3_key: str,
    ) -> "SGDClassifierModel":
        logger.info(f"Loading model from s3://{MODEL_S3_BUCKET}/{s3_key}")
        with tempfile.NamedTemporaryFile() as temp_file:
            download_file_from_s3(
                s3_bucket=MODEL_S3_BUCKET,
                s3_key=s3_key,
                file_path=temp_file.name,
            )

            # 一時ファイルから pickle モデルを読み込む
            with open(temp_file.name, "rb") as f:
                model = pickle.load(f)
        return cls(model)


# DataFrame を FeatureHasher でハッシュ化して疎行列に変換する関数
# 高カーディナリティなカテゴリ変数を固定サイズのベクトルにエンコードするためのハッシュトリック
def hashing_feature(df: pd.DataFrame, hash_size: int = 2**18) -> npt.NDArray:
    # 全カラムを文字列型に変換してから FeatureHasher に渡す（型の違いを吸収するため）
    feature_hasher = FeatureHasher(n_features=hash_size, input_type="string")
    # DataFrame を文字列の numpy 配列に変換して疎行列にハッシュ化する
    hashed_feature = feature_hasher.fit_transform(np.asanyarray(df.astype(str)))
    return hashed_feature
