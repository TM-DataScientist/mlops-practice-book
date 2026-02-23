# モデル設定の定義と取得関数を提供するモジュール
# 使用するモデルクラス・特徴量スキーマ・訓練パラメータを一元管理する
import logging
from dataclasses import dataclass

from .models.base_model import BaseModel
from .models.lightgbm import LightGBMModel
from .models.sgd_classifier import SGDClassifierModel
from .schema import Schema

logger = logging.getLogger(__name__)


# モデル訓練に必要な全設定を保持するデータクラス
# モデルクラス・特徴量定義・訓練期間・データ分割比率を一つにまとめて扱う
@dataclass
class ModelConfig:
    name: str  # モデルの識別名（モデルレジストリのキーとして使用）
    model_class: BaseModel  # 訓練・推論を行うモデルクラスのインスタンス
    schemas: list[Schema]  # 特徴量カラムの定義（名前・型・欠損値補完値）
    target: str  # 目的変数のカラム名（is_click）
    train_interval_days: int  # 訓練データの取得期間（日数）
    lookback_days: int  # 履歴特徴量を計算するルックバック期間（日数）
    test_valid_ratio: dict[str, float]  # テスト・検証データの分割比率

    # スキーマ定義から特徴量カラム名の一覧を返すプロパティ
    @property
    def feature_columns(self) -> list[str]:
        return [schema.name for schema in self.schemas]


# プロジェクトで使用する全モデルの設定リスト
model_configs = [
    # SGD 分類器を使った CTR 予測モデルの設定
    # Optuna による正則化パラメータ（alpha）の自動チューニングを有効にしている
    ModelConfig(
        name="sgd_classifier_ctr",
        model_class=SGDClassifierModel(
            is_optuna=True, args=dict(max_iter=1000, loss="log_loss", penalty="l2", random_state=42)
        ),
        schemas=[
            # インプレッション時刻の特徴量（時間・日・曜日）
            Schema(name="impression_hour", dtype="int", null_value=-1),
            Schema(name="impression_day", dtype="int", null_value=-1),
            Schema(name="impression_weekday", dtype="int", null_value=-1),
            # ユーザー属性特徴量
            Schema(name="user_id", dtype="int", null_value=-1),
            Schema(name="app_code", dtype="int", null_value=-1),
            Schema(name="os_version", dtype="str", null_value="null"),
            Schema(name="is_4g", dtype="int", null_value=-1),
            # ユーザー行動履歴特徴量
            Schema(name="previous_impression_count", dtype="int", null_value=-1),
            Schema(name="previous_view_count", dtype="int", null_value=-1),
            # 商品属性特徴量
            Schema(name="item_id", dtype="int", null_value=-1),
            Schema(name="device_type", dtype="str", null_value="null"),
            Schema(name="item_price", dtype="int", null_value=-1),
            Schema(name="category_1", dtype="int", null_value=-1),
            Schema(name="category_2", dtype="int", null_value=-1),
            Schema(name="category_3", dtype="int", null_value=-1),
            Schema(name="product_type", dtype="int", null_value=-1),
        ],
        target="is_click",
        train_interval_days=28,  # 直近28日間のデータで訓練する
        lookback_days=7,  # 履歴特徴量は直近7日間を参照する
        test_valid_ratio={"test_size": 0.2, "valid_size": 0.1},  # 20%テスト・10%検証
    ),
    # LightGBM を使った CTR 予測モデルの設定
    # カテゴリカル特徴量を category 型で扱い、LightGBM のネイティブカテゴリ処理を利用する
    ModelConfig(
        name="lightgbm_ctr",
        model_class=LightGBMModel(args=dict(num_leaves=31, objective="binary")),
        schemas=[
            # インプレッション時刻の特徴量（時間・日・曜日）
            Schema(name="impression_hour", dtype="int", null_value=-1),
            Schema(name="impression_day", dtype="int", null_value=-1),
            Schema(name="impression_weekday", dtype="int", null_value=-1),
            # ユーザー属性特徴量（LightGBM はカテゴリ型をネイティブサポートするため category 型を使用）
            Schema(name="user_id", dtype="category", null_value=-1),
            Schema(name="app_code", dtype="category", null_value=-1),
            Schema(name="os_version", dtype="category", null_value="null"),
            Schema(name="is_4g", dtype="int", null_value=-1),
            # ユーザー行動履歴特徴量
            Schema(name="previous_impression_count", dtype="int", null_value=-1),
            Schema(name="previous_view_count", dtype="int", null_value=-1),
            # 商品属性特徴量（カテゴリカル変数は category 型で定義）
            Schema(name="item_id", dtype="category", null_value=-1),
            Schema(name="device_type", dtype="category", null_value="null"),
            Schema(name="item_price", dtype="int", null_value=-1),
            Schema(name="category_1", dtype="category", null_value=-1),
            Schema(name="category_2", dtype="category", null_value=-1),
            Schema(name="category_3", dtype="category", null_value=-1),
            Schema(name="product_type", dtype="category", null_value=-1),
        ],
        target="is_click",
        train_interval_days=28,
        lookback_days=7,
        test_valid_ratio={"test_size": 0.2, "valid_size": 0.1},
    ),
]


# モデル名からモデル設定を取得する関数
# 存在しないモデル名が指定された場合は ValueError を発生させる
def get_model_config(model_name: str) -> ModelConfig:
    for model_config in model_configs:
        if model_config.name == model_name:
            return model_config
    raise ValueError(f"Invalid model name: {model_name}")
