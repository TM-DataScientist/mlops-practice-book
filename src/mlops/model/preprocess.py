# 特徴量エンジニアリングおよびデータ前処理関数を提供するモジュール
# インプレッションログ・ビューログ・商品マスタから特徴量を生成し、訓練データに変換する
import logging

import pandas as pd
from sklearn.model_selection import train_test_split

from .schema import Schema

logger = logging.getLogger(__name__)


# 3テーブルを結合して訓練用の特徴量 DataFrame を生成する関数
# インプレッション時刻特徴量・インプレッション履歴特徴量・ビュー履歴特徴量・商品属性をすべて結合する
def apply_preprocess(
    df_impression_log: pd.DataFrame,
    df_view_log: pd.DataFrame,
    df_item: pd.DataFrame,
    lookback_days: int = 7,
) -> pd.DataFrame:
    logger.info(f"Start common preprocess {len(df_impression_log)=}, {len(df_view_log)=}, {len(df_item)=}, {lookback_days=}")

    # 各特徴量グループを個別に生成する
    df_impression_time_feature = _get_impression_time_feature(df_impression_log)
    df_impression_history_feature = _get_impression_history_feature(df_impression_log, lookback_days=lookback_days)
    df_view_history_feature = _get_view_history_feature(df_impression_log, df_view_log, lookback_days=lookback_days)

    # impression_id をキーとして順に左外部結合で特徴量を合体させる
    df = df_impression_log.merge(df_impression_time_feature, how="left", on="impression_id")
    df = df.merge(df_impression_history_feature, how="left", on="impression_id")
    df = df.merge(df_view_history_feature, how="left", on="impression_id")
    # item_id をキーとして商品マスタの属性を結合する
    df = df.merge(df_item, how="left", on="item_id")

    logger.info(f"Finished common preprocess {len(df)=}, {df.head()}")
    return df


# 特徴量ストア向けのインプレッション特徴量を生成する関数
# apply_preprocess との違い: インプレッション時刻特徴量は含まず、オンライン特徴量ストア用の特徴量のみを生成する
def get_impression_feature(
    df_impression_log: pd.DataFrame,
    df_view_log: pd.DataFrame,
    df_item: pd.DataFrame,
    lookback_days: int = 7,
) -> pd.DataFrame:
    logger.info(
        f"Start get impression feature {len(df_impression_log)=}, {len(df_view_log)=}, {len(df_item)=}, {lookback_days=}"
    )

    # インプレッション履歴特徴量（直近 lookback_days 日以内の過去インプレッション回数）を生成する
    df_impression_history_feature = _get_impression_history_feature(df_impression_log, lookback_days=lookback_days)
    # ビュー履歴特徴量（直近 lookback_days 日以内の閲覧回数・商品・デバイス）を生成する
    df_view_history_feature = _get_view_history_feature(df_impression_log, df_view_log, lookback_days=lookback_days)

    # impression_id をキーとして各特徴量を結合する
    df = df_impression_log.merge(df_impression_history_feature, how="left", on="impression_id")
    df = df.merge(df_view_history_feature, how="left", on="impression_id")
    # 商品マスタを item_id で結合する（item_id は view_history 側から取得されているため外部結合）
    df = pd.merge(df, df_item, on="item_id", how="left")

    logger.info(f"Finished impression feature {len(df)=}, {df.head()}")

    return df


# スキーマ定義に従って欠損補完とデータ型変換を一括適用する関数
# モデルの入力として期待する型に整形するために使用する
def apply_schema(
    df: pd.DataFrame,
    schemas: list[Schema],
) -> pd.DataFrame:
    logger.info(f"Start apply schema {len(df)=}, {len(schemas)=}")
    for schema in schemas:
        df[schema.name] = df[schema.name].fillna(schema.null_value)  # 欠損値を指定値で補完
        df[schema.name] = df[schema.name].astype(schema.dtype)  # 指定データ型にキャスト
    return df


# データを時系列順に訓練・検証・テストの3分割する関数
# shuffle=False によりデータリーケージを防ぐ（未来データが訓練に混入しない）
def apply_train_test_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    valid_size: float = 0.1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info(f"Start get train dataset. {len(df)=}, {test_size=}, {valid_size=}")

    # Sort by impression time to split data based on the impression time
    # 時系列順にソートしてから分割することで、訓練が過去・テストが未来というシミュレーションができる
    df = df.sort_values(by="logged_at")
    # TODO: valid, testを割合ではなく、日にちで分割する。今だと学習データ期間が変わると、valid, testデータが変わってしまう。

    # まず全体をテストと非テストに分割する
    df_train, df_test = train_test_split(df, test_size=test_size, random_state=42, shuffle=False)
    # 次に非テスト部分を訓練と検証に分割する
    df_train, df_valid = train_test_split(df_train, test_size=valid_size, random_state=42, shuffle=False)

    return df_train, df_valid, df_test


# 直近 lookback_days 日以内の過去インプレッション回数をユーザーごとに計算するプライベート関数
# 同一テーブルを self-join してインプレッションの自己結合を行う
def _get_impression_history_feature(
    df_impression_log: pd.DataFrame,
    lookback_days: int = 7,
) -> pd.DataFrame:
    # 同じテーブルを user_id で self-join して各インプレッションに過去のインプレッション一覧を紐づける
    df_impression_history = df_impression_log.merge(df_impression_log, how="left", on="user_id", suffixes=("", "_previous"))

    # 現在のインプレッション時刻と過去のインプレッション時刻の日数差を計算する
    df_impression_history["days_between_impressions"] = (
        df_impression_history["logged_at"] - df_impression_history["logged_at_previous"]
    ).dt.days

    # 「過去のインプレッションである」かつ「lookback_days 日以内」の条件でフィルタリングする
    df_impression_history = df_impression_history.query(
        f"(logged_at_previous < logged_at) and (days_between_impressions <= {lookback_days})"
    )

    # 各インプレッションに対して、過去インプレッション数を集計する
    df_impression_history_feature = (
        df_impression_history.groupby("impression_id")["impression_id_previous"]
        .count()
        .reset_index(name="previous_impression_count")
    )

    # Int64Dtype（Nullable 整数型）にキャストして欠損値を適切に扱えるようにする
    df_impression_history_feature["previous_impression_count"] = df_impression_history_feature[
        "previous_impression_count"
    ].astype(pd.Int64Dtype())
    return df_impression_history_feature


# 直近 lookback_days 日以内の閲覧（ビュー）履歴特徴量を計算するプライベート関数
# ユーザーの閲覧回数・最後に見た商品・最後に使ったデバイスを返す
def _get_view_history_feature(
    df_impression_log: pd.DataFrame,
    df_view_log: pd.DataFrame,
    lookback_days: int = 7,
) -> pd.DataFrame:
    # 同一ユーザーが同一時刻に複数ビューを持つ場合は最後の1件を残して重複除去する
    df_view_log_drop_duplicated = df_view_log.drop_duplicates(subset=["user_id", "logged_at"], keep="last")
    # インプレッションログとビューログを user_id で外部結合する
    df_view_history = df_impression_log.merge(
        df_view_log_drop_duplicated,
        how="left",
        on="user_id",
        suffixes=("_impression", "_view"),
    )

    # インプレッション時刻とビュー時刻の日数差を計算する
    df_view_history["days_between_impression_and_session"] = (
        df_view_history["logged_at_impression"] - df_view_history["logged_at_view"]
    ).dt.days

    # 「ビューがインプレッション以前」かつ「lookback_days 日以内」の条件でフィルタリングする
    df_view_history = df_view_history.query(
        f"(logged_at_view < logged_at_impression) and (days_between_impression_and_session <= {lookback_days})"
    )
    # インプレッションごとに: ビュー回数・最後に見た商品ID・最後に使ったデバイスタイプを集計する
    df_view_history_features = (
        df_view_history.groupby(
            "impression_id",
        )
        .agg(
            previous_view_count=("logged_at_view", "count"),  # ビュー回数
            item_id=("item_id", "last"),  # 最後に閲覧した商品ID
            device_type=("device_type", "last"),  # 最後に使用したデバイスタイプ
        )
        .reset_index()
    )

    # Int64Dtype（Nullable 整数型）にキャストして欠損値を適切に扱えるようにする
    df_view_history_features["previous_view_count"] = df_view_history_features["previous_view_count"].astype(pd.Int64Dtype())

    return df_view_history_features


# インプレッション時刻から時間・日・曜日の特徴量を抽出するプライベート関数
# CTR はアクセス時間帯・曜日に依存する傾向があるため、時刻情報を特徴量として使う
def _get_impression_time_feature(
    df_impression_log: pd.DataFrame,
) -> pd.DataFrame:
    df_impression_time_feature = pd.DataFrame(
        {
            "impression_id": df_impression_log["impression_id"],
            "impression_hour": df_impression_log["logged_at"].dt.hour,  # 時（0-23）
            "impression_day": df_impression_log["logged_at"].dt.day,  # 日（1-31）
            "impression_weekday": df_impression_log["logged_at"].dt.weekday,  # 曜日（0=月曜〜6=日曜）
        }
    )
    return df_impression_time_feature


# 時刻文字列カラムから時間・日・曜日特徴量を既存 DataFrame に追加する関数
# 特徴量ストアから取得したデータに対してオンラインで時刻特徴量を付与する際に使用する
def add_impression_time_feature(
    df: pd.DataFrame,
    impression_time_column: str,
) -> pd.DataFrame:
    # 文字列型の時刻カラムを datetime 型に変換する
    df[impression_time_column] = pd.to_datetime(df[impression_time_column])
    df["impression_hour"] = df[impression_time_column].dt.hour  # 時（0-23）
    df["impression_day"] = df[impression_time_column].dt.day  # 日（1-31）
    df["impression_weekday"] = df[impression_time_column].dt.weekday  # 曜日（0=月曜〜6=日曜）
    return df
