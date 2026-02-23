# モデルの特徴量スキーマ定義データクラスモジュール
# 各特徴量のカラム名・データ型・欠損値補完用デフォルト値を保持し、前処理の設定として使用する
from dataclasses import dataclass
from typing import Any


# 単一特徴量カラムのスキーマ情報を保持するデータクラス
# ModelConfig の schemas リストの要素として使用し、apply_schema 関数での型変換・欠損補完に参照される
@dataclass
class Schema:
    name: str  # 特徴量のカラム名（DataFrame のカラム名に一致する必要がある）
    dtype: str  # 変換先のデータ型（"int", "str", "category" など）
    null_value: Any  # 欠損値を補完する際に使用するデフォルト値（数値型は -1、文字列型は "null" など）
