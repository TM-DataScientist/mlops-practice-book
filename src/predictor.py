# FastAPIを使ったオンライン推論サーバーのエントリーポイント
# 起動時にS3からモデルをロードし、/predict エンドポイントで広告クリック率を予測する
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, Request

from mlops.aws import OnlineFeatureStoreDynamoDB, get_latest_model_version, get_model_s3_key
from mlops.const import FEATURE_DYNAMODB_TABLE, MODEL_REGISTRY_DYNAMODB_TABLE
from mlops.middleware import Artifact, set_logger_config
from mlops.model import add_impression_time_feature, get_model_config
from mlops.predictor import AdRequest

logger = logging.getLogger(__name__)


# FastAPIアプリケーションの起動・終了時の処理を管理するライフスパンコンテキストマネージャ
# アプリ起動時にモデルと特徴量ストアを初期化し、各リクエストから参照できるよう yield で渡す
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    current_time = datetime.now()
    version = current_time.strftime("%Y%m%d%H%M%S")
    artifact = Artifact(version=version, job_type="predictor")
    set_logger_config(log_file_path=artifact.file_path("log.txt"))

    # 環境変数からモデル名・バージョン・特徴量バージョンを取得する（デフォルト値付き）
    # Setup for model config
    model_name = os.getenv("MODEL_NAME", "sgd_classifier_ctr")
    model_version = os.getenv("MODEL_VERSION", "latest")
    feature_version = os.getenv("FEATURE_VERSION", "latest")
    logger.info(f"Configure {model_name=}, {model_version=}, {feature_version=}")

    # model_version が "latest" の場合は DynamoDB のモデルレジストリから最新バージョンを取得する
    if model_version == "latest":
        latest_model_version = get_latest_model_version(table=MODEL_REGISTRY_DYNAMODB_TABLE, model=model_name)
        if latest_model_version is None:
            raise ValueError("No latest model found")
        model_version = latest_model_version

    # DynamoDB からモデルの S3 パス（s3_key）を取得する
    model_s3_key = get_model_s3_key(table=MODEL_REGISTRY_DYNAMODB_TABLE, model=model_name, version=model_version)
    if model_s3_key is None:
        raise ValueError("Model S3 key not found")

    model_config = get_model_config(model_name=model_name)
    #  S3 からモデルファイルをダウンロード
    model = model_config.model_class.from_pretrained(s3_key=model_s3_key)

    # DynamoDB のオンライン特徴量ストアへの接続クライアントを初期化する
    online_feature_store = OnlineFeatureStoreDynamoDB(table=FEATURE_DYNAMODB_TABLE, version=feature_version)

    # 論結果をログとして記録するために、DataFrame に列を追加
    # 予測結果・モデル情報・タイムスタンプを JSON として標準出力に書き出す
    def log_prediction(df: pd.DataFrame, prediction: float) -> None:
        df = df.assign(
            prediction=prediction,
            model_name=model_name,
            model_version=model_version,
            feature_version=feature_version,
            logged_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        print(json.dumps(df.iloc[0].to_dict()))

    # yield によって起動時に初期化したオブジェクトを request.state 経由で各エンドポイントに渡す
    yield {
        "model": model,
        "model_config": model_config,
        "online_feature_store": online_feature_store,
        "log_prediction": log_prediction,
    }


app = FastAPI(lifespan=lifespan)


# 広告クリック率を予測するエンドポイント
# リクエストのユーザーID に基づき DynamoDB から特徴量を取得し、モデルで予測確率を返す
@app.post("/predict")
async def predict(ad_request: AdRequest, request: Request) -> dict[str, str | float]:
    # リクエストボディを DataFrame に変換する（1行のみ）
    df = pd.DataFrame([ad_request.model_dump()])

    # DynamoDB からユーザーの過去行動特徴量を取得して DataFrame に結合する
    # Get user feature from DynamoDB
    user_feature = request.state.online_feature_store.get_impression_feature(user_id=ad_request.user_id)
    df = df.assign(**user_feature)

    # インプレッション時刻から時間・日・曜日の特徴量を追加する
    # Add impression time features
    df = add_impression_time_feature(df, "logged_at")

    # モデルスキーマに従い、欠損値補完とデータ型変換を適用する
    # Fill missing values and convert data types
    for schema in request.state.model_config.schemas:
        if schema.name not in df.columns:
            df[schema.name] = np.nan  # スキーマに定義されているが DataFrame に存在しない列は NaN で初期化
        df[schema.name] = df[schema.name].fillna(schema.null_value)  # null_value で欠損補完
        df[schema.name] = df[schema.name].astype(schema.dtype)  # 指定データ型にキャスト
    # スキーマ定義の順序に従ってカラムを並び替える
    df = df[[schema.name for schema in request.state.model_config.schemas]]

    # モデルによる予測確率を計算する（クリック率の予測値）
    # Get prediction
    prediction = request.state.model.predict_proba(df)

    # 予測結果をログに記録する
    request.state.log_prediction(df, float(prediction))

    return dict(
        model=request.state.model_config.name,
        prediction=float(prediction),
    )


# ヘルスチェックエンドポイント（ロードバランサーやコンテナオーケストレーターからの死活監視用）
@app.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"health": "ok"}


# uvicorn でサーバーを起動するエントリーポイント関数
def main() -> None:
    uvicorn.run("predictor:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
