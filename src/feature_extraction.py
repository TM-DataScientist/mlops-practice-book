# 特徴量抽出パイプラインのエントリーポイント
# Athenaからデータを取得し、特徴量を生成してS3（オフライン）とDynamoDB（オンライン）に保存する
import argparse
import logging
from datetime import datetime, timedelta

from mlops.aws import put_csv_to_dynamodb, upload_file_to_s3
from mlops.const import FEATURE_DYNAMODB_TABLE, FEATURE_S3_BUCKET
from mlops.data_loader import compose_sql, extract_dataframe_from_athena
from mlops.data_validator import IMPRESSION_LOG_SCHEMA, MST_ITEM_SCHEMA, VIEW_LOG_SCHEMA
from mlops.middleware import Artifact, set_logger_config
from mlops.model import get_impression_feature, get_model_config

logger = logging.getLogger(__name__)

# オフライン特徴量ストアに保存するカラムの一覧（訓練データ用）
OFFLINE_FEATURES = [
    "user_id",
    "app_code",
    "os_version",
    "is_4g",
    "is_click",
    "previous_impression_count",
    "previous_view_count",
    "item_id",
    "device_type",
    "item_price",
    "category_1",
    "category_2",
    "category_3",
    "product_type",
    "logged_at",
]
# オンライン特徴量ストア（DynamoDB）に保存するカラムの一覧（推論時にリアルタイムで使用する特徴量）
ONLINE_FEATURES = [
    "user_id",
    "previous_impression_count",
    "previous_view_count",
    "device_type",
    "item_id",
    "item_price",
    "category_1",
    "category_2",
    "category_3",
    "product_type",
]


# コマンドライン引数を解析して返す関数
def load_options() -> argparse.Namespace:
    description = """
    Feature extraction arguments
    """
    parser = argparse.ArgumentParser(description=description)
    # データ取得の上限日時（デフォルト: 2018-12-10 00:00:00）
    parser.add_argument("-t", "--datetime_ub", type=str, default="2018-12-10 00:00:00")

    return parser.parse_args()


# 特徴量抽出パイプライン全体を実行するメイン関数
def main() -> None:
    args = load_options()

    # -----------------------------
    # Setup
    # -----------------------------
    current_time = datetime.now()
    # バージョン文字列はタイムスタンプから生成し、アーティファクトの識別子として使う
    version = current_time.strftime("%Y%m%d%H%M%S")
    artifact = Artifact(version=version, job_type="feature_extraction")
    set_logger_config(log_file_path=artifact.file_path("log.txt"))
    # モデル設定からルックバック日数や訓練期間を取得する
    model_config = get_model_config(model_name="sgd_classifier_ctr")
    logger.info(f"{artifact=}, {args=}, {vars(model_config)=}")

    # -----------------------------
    # Extract Data
    # -----------------------------
    # 上限日時の引数が指定されていればパース、なければ現在時刻を使用する
    if args.datetime_ub is not None:
        to_datetime = datetime.strptime(args.datetime_ub, "%Y-%m-%d %H:%M:%S")
    else:
        to_datetime = current_time

    # インプレッションログ: 訓練期間分（train_interval_days）のデータを取得
    sql = compose_sql(
        table="impression_log",
        from_datetime=to_datetime - timedelta(days=model_config.train_interval_days),
        to_datetime=to_datetime,
    )
    df_impression_log = extract_dataframe_from_athena(sql=sql)

    # ビューログ: 訓練期間 + ルックバック日数分のデータを取得（履歴特徴量に必要）
    sql = compose_sql(
        table="view_log",
        from_datetime=to_datetime - timedelta(days=model_config.train_interval_days + model_config.lookback_days),
        to_datetime=to_datetime,
    )
    df_view_log = extract_dataframe_from_athena(sql=sql)

    # 商品マスタ: 全件取得（期間フィルタなし）
    sql = compose_sql(
        table="mst_item",
    )
    df_item = extract_dataframe_from_athena(sql=sql)

    # -----------------------------
    # Validate Data
    # -----------------------------
    # panderaスキーマを使ってデータ型・値域・カラム構成を検証する
    df_impression_log = IMPRESSION_LOG_SCHEMA.validate(df_impression_log)
    df_view_log = VIEW_LOG_SCHEMA.validate(df_view_log)
    df_item = MST_ITEM_SCHEMA.validate(df_item)

    # -----------------------------
    # Preprocess Data
    # -----------------------------
    # インプレッション・ビュー・商品の3テーブルを結合して特徴量DataFrameを生成する
    df_feature = get_impression_feature(
        df_impression_log=df_impression_log,
        df_view_log=df_view_log,
        df_item=df_item,
        lookback_days=model_config.lookback_days,
    )

    # -----------------------------
    # Save Offline Feature Store
    # -----------------------------
    # 訓練用のカラムだけを抽出してCSV保存し、S3のオフライン特徴量ストアへアップロード
    df_feature_transaction = df_feature[OFFLINE_FEATURES]
    df_feature_transaction.to_csv(artifact.file_path("df_feature.csv"), index=False)
    upload_file_to_s3(
        s3_bucket=FEATURE_S3_BUCKET,
        file_path=artifact.file_path("df_feature.csv"),
        s3_key=f"impression_feature/version={version}/df_feature.csv",  # バージョンでパーティション分割
    )

    # -----------------------------
    # Save Online Feature Store
    # -----------------------------
    # ユーザーごとに最新のログを1件だけ残す（重複除去）
    df_feature_latest = df_feature.sort_values("logged_at", ascending=False).drop_duplicates("user_id", keep="first")
    df_feature_latest = df_feature_latest[ONLINE_FEATURES]
    # バージョンと有効期限（7日後のUNIXタイムスタンプ）を付与してDynamoDBへ書き込む
    df_feature_latest["version"] = version
    df_feature_latest["expired_at"] = int((current_time + timedelta(days=7)).timestamp())
    put_csv_to_dynamodb(df=df_feature_latest, table_name=FEATURE_DYNAMODB_TABLE)

    logger.info("Finished Feature Extraction.")


if __name__ == "__main__":
    main()
