# 全モデルクラスの基底となる抽象クラスを定義するモジュール
# 訓練・推論・保存・ロードのインターフェースを強制することで、複数モデルを統一的に扱えるようにする
from abc import ABC, abstractmethod
from pathlib import Path

import numpy.typing as npt
import pandas as pd

# DataFrame または NumPy 配列を受け付けるユニオン型エイリアス
type PdNpType = pd.DataFrame | npt.NDArray


# 全モデルクラスが継承すべき抽象基底クラス
# このクラスを継承することで、train.py や predictor.py がモデルの種類を意識せずに
# 統一インターフェースでモデルを操作できる（戦略パターン）
class BaseModel(ABC):
    # モデルを訓練する抽象メソッド
    # 訓練データと検証データを受け取り、モデル内部の状態を更新する
    @abstractmethod
    def train(
        self,
        X_train: PdNpType,
        y_train: PdNpType,
        X_valid: PdNpType,
        y_valid: PdNpType,
    ) -> None:
        raise NotImplementedError

    # 予測確率を返す抽象メソッド（正例である確率を 0〜1 のスカラーまたは配列で返す）
    @abstractmethod
    def predict_proba(self, X: PdNpType) -> npt.NDArray:
        raise NotImplementedError

    # モデルをローカルファイルに保存する抽象メソッド
    @abstractmethod
    def save(self, file_path: Path) -> None:
        raise NotImplementedError

    # S3 からモデルをロードしてインスタンスを返すクラスメソッド
    # 継承クラスでオーバーライドして具体的な実装を提供する必要がある
    @classmethod
    def from_pretrained(cls, s3_key: str) -> "BaseModel":
        raise NotImplementedError
