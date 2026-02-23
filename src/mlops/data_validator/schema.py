# 各テーブルのデータスキーマ定義（pandera を使ったデータバリデーション）
# Athena から取得したデータのカラム構成・データ型・値域を検証するための定義を提供する
from datetime import datetime

import pandas as pd
from pandera import Check, Column, DataFrameSchema, Index

# インプレッションログテーブルのスキーマ定義
# 広告が表示されたイベントのログで、クリックラベル（is_click）を含む
IMPRESSION_LOG_SCHEMA = DataFrameSchema(
    name="impression_log",
    columns={
        "impression_id": Column(str, unique=True),  # インプレッションの一意識別子（重複不可）
        "logged_at": Column(datetime),  # ログの記録日時
        "user_id": Column(int, checks=Check.greater_than_or_equal_to(0)),  # ユーザーID（非負整数）
        "app_code": Column(int, checks=Check.greater_than_or_equal_to(0)),  # アプリ識別コード（非負整数）
        "os_version": Column(str, checks=Check.isin(["old", "latest", "intermediate"])),  # OS バージョンカテゴリ
        "is_4g": Column(int, checks=Check.isin([0, 1])),  # 4G 接続フラグ（0 or 1）
        "is_click": Column(int, checks=Check.isin([0, 1])),  # クリックラベル（0: 非クリック, 1: クリック）
    },
    index=Index(int),  # 整数インデックス
    strict=True,  # 定義外のカラムが含まれる場合はエラーにする
    coerce=True,  # 型が異なる場合は自動変換を試みる
)

# ビューログテーブルのスキーマ定義
# ユーザーが商品ページを閲覧したイベントのログ
VIEW_LOG_SCHEMA = DataFrameSchema(
    name="view_log",
    columns={
        "logged_at": Column(datetime),  # ログの記録日時
        "device_type": Column(pd.StringDtype(), checks=Check.isin(["android", "iphone", "web"])),  # 閲覧デバイス種別
        "session_id": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # セッション識別子（非負整数）
        "user_id": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # ユーザーID（非負整数）
        "item_id": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # 閲覧した商品ID（非負整数）
    },
    index=Index(int),
    strict=True,
    coerce=True,
)

# 商品マスタテーブルのスキーマ定義
# 商品の属性情報（価格・カテゴリ・商品タイプ）を管理するマスタデータ
MST_ITEM_SCHEMA = DataFrameSchema(
    name="mst_item",
    columns={
        "item_id": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # 商品ID（非負整数）
        "item_price": Column(pd.Int64Dtype(), checks=Check.greater_than(0)),  # 商品価格（1以上の正整数）
        "category_1": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # 大カテゴリ（非負整数）
        "category_2": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # 中カテゴリ（非負整数）
        "category_3": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # 小カテゴリ（非負整数）
        "product_type": Column(pd.Int64Dtype(), checks=Check.greater_than_or_equal_to(0)),  # 商品タイプ（非負整数）
    },
    index=Index(int),
    strict=True,
    coerce=True,
)
