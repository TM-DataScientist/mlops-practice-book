# AWS リソース（S3・DynamoDB・ECS）を操作するコントローラー関数群
# モデルファイルのアップロード/ダウンロード、モデルレジストリの読み書き、ECS タスクの起動を担う
import logging
from pathlib import Path
from typing import Any

import boto3
import numpy as np
import pandas as pd
from boto3.dynamodb.types import TypeSerializer
from tqdm import tqdm

from mlops.const import PUBLIC_SUBNET_1A, TRAIN_SECURITY_GROUP

logger = logging.getLogger(__name__)


# S3 から指定されたキーのファイルをローカルにダウンロードする関数
def download_file_from_s3(s3_bucket: str, s3_key: str, file_path: str) -> None:
    logger.info(f"Start download model file: {s3_key}, file_path: {file_path}")
    s3_client = boto3.client("s3")
    s3_client.download_file(s3_bucket, s3_key, file_path)
    logger.info(f"Finished download model file: {s3_key}, file_path: {file_path}")


# 指定されたローカルディレクトリ内のすべてのファイルを、サブディレクトリの構造を保った状態でS3バケットへアップロードする関数
def upload_dir_to_s3(dir_path: Path, s3_bucket: str, key_prefix: str) -> None:
    s3_client = boto3.client("s3")
    # 指定したディレクトリ内にあるすべてのファイルやフォルダを、サブディレクトリまで含めて再帰的に探し出す処理
    for file_path in dir_path.rglob("*"):
        if file_path.is_file():
            # ディレクトリからの相対パスを S3 キーの末尾に付加してパス構造を再現する
            s3_key = key_prefix + "/" + str(file_path.relative_to(dir_path))
            try:
                s3_client.upload_file(str(file_path), s3_bucket, s3_key)
                logger.info(f"Uploaded {file_path} to s3://{s3_bucket}/{s3_key}")
            except Exception as e:
                logger.info(f"Failed to upload {file_path}. Error: {e}")


# 単一ファイルを指定した S3 キーにアップロードする関数
def upload_file_to_s3(
    s3_bucket: str,
    file_path: Path,
    s3_key: str,
) -> None:
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(str(file_path), s3_bucket, s3_key)
        logger.info(f"Succeed to upload {file_path} to s3://{s3_bucket}/{s3_key}")
    except Exception as e:
        logger.info(f"Failed to upload {file_path}. Error: {e}")


# DynamoDB のモデルレジストリにモデルのバージョン情報とメタデータを登録する関数
def register_model_registry(table_name: str, model_name: str, version: str, metadata: dict[str, Any]) -> None:
    logger.info(f"Start register model registry: {table_name=} {model_name=}, {version=}, {metadata=}")
    client = boto3.client("dynamodb")

    # Python の辞書を DynamoDB のデータ型フォーマット（AttributeValue）にシリアライズする
    serializer = TypeSerializer()
    metadata_dynamodb_type = {k: serializer.serialize(str(v)) for k, v in metadata.items()}
    logger.info(f"{metadata_dynamodb_type=}")

    try:
        # モデル名とバージョンをキーとして DynamoDB にアイテムを書き込む
        client.put_item(
            TableName=table_name,
            Item={
                "model": {"S": model_name},
                "version": {"S": version},
                **metadata_dynamodb_type,  # メタデータを展開してマージ
            },
        )
        logger.info("Finished register model registry.")
    except Exception as e:
        logger.info(f"Failed to register model registry. Error: {e}")


# DynamoDB のモデルレジストリから指定モデルの最新バージョンを取得する関数
# バージョンは文字列の降順（最新が先頭）で取得し、最初の1件を返す
def get_latest_model_version(table: str, model: str) -> str | None:
    logger.info(f"Start getting latest version for model: {table=}, {model=}")
    client = boto3.client("dynamodb")

    try:
        response = client.query(
            TableName=table,
            KeyConditionExpression="model = :model",
            ExpressionAttributeValues={":model": {"S": model}},
            ProjectionExpression="version",  # version カラムのみ取得してデータ転送量を削減
            ScanIndexForward=False,  # 降順ソート（最新バージョンが先頭）
            Limit=1,  # 最新の1件だけ取得
        )
        latest_version = response["Items"][0]["version"]["S"]
        logger.info(f"Found latest version for model {model}: {latest_version}")
        return latest_version

    except Exception as err:
        # バージョンが存在しない場合や DynamoDB エラーの場合は None を返す
        logger.info(f"Failed to get latest version for model {model}. Error: {err}")
        return None


# DynamoDB のモデルレジストリから指定モデル・バージョンの S3 パスを取得する関数
def get_model_s3_key(table: str, model: str, version: str) -> str | None:
    logger.info(f"Start get model s3 key from dynamodb: {table=}, {model=}, {version=}")
    client = boto3.client("dynamodb")

    try:
        response = client.query(
            TableName=table,
            KeyConditionExpression="model = :model AND version = :version",
            ExpressionAttributeValues={":model": {"S": model}, ":version": {"S": version}},
            ProjectionExpression="model_s3_path",  # S3 パスのみ取得
        )
        if len(response["Items"]) == 0:
            # 指定したモデル・バージョンが存在しない場合
            logger.info(f"Model {model} version {version} not found in DynamoDB.")
            return None
        model_s3_path = response["Items"][0]["model_s3_path"]["S"]
        logger.info(f"Finished get model s3 key from dynamodb: {model_s3_path=}")
        return model_s3_path

    except Exception as err:
        logger.info(f"Failed to get model s3 key from dynamodb. {err}")
        return None


# DataFrame のデータを DynamoDB に一括書き込みする関数（バッチライターで効率的に書き込む）
def put_csv_to_dynamodb(df: pd.DataFrame, table_name: str) -> None:
    logger.info(f"Start put csv to dynamodb {table_name=}, {df.shape=}")
    dynamo = boto3.resource("dynamodb")
    dynamo_table = dynamo.Table(table_name)
    # batch_writer はバッファリングして一括書き込みするため、put_item を個別に呼ぶより効率的
    with dynamo_table.batch_writer() as batch:
        # DataFrame を行の辞書の iterable に変換してループ処理（tqdm で進捗表示）
        for item in tqdm(df.T.to_dict().values()):
            batch.put_item(Item=item)


# DynamoDB のオンライン特徴量ストアへの読み取りアクセスを管理するクラス
# 推論時にユーザーの最新特徴量をリアルタイムで取得するために使用する
class OnlineFeatureStoreDynamoDB:
    def __init__(self, table: str, version: str):
        # DynamoDB テーブル名と使用する特徴量バージョン（"latest" または具体的なバージョン文字列）
        self.table = table
        self.version = version
        self.client = boto3.client("dynamodb")

    # 指定ユーザーIDに対応する最新のインプレッション特徴量を DynamoDB から取得するメソッド
    def get_impression_feature(self, user_id: int) -> dict[str, str | int]:
        if self.version == "latest":
            # "latest" の場合は降順ソートの1件目（最新）を取得するクエリオプション
            options = {
                "TableName": self.table,
                "KeyConditionExpression": "user_id = :user_id",
                "ExpressionAttributeValues": {":user_id": {"N": str(user_id)}},
                "ScanIndexForward": False,  # 降順ソート
                "Limit": 1,
            }
        else:
            # 特定バージョンを指定する場合はバージョン条件を追加する
            options = {
                "TableName": self.table,
                "KeyConditionExpression": "user_id = :user_id AND version = :version",
                "ExpressionAttributeValues": {":user_id": {"N": str(user_id)}, ":version": {"N": str(self.version)}},
            }

        record = {}
        try:
            response = self.client.query(**options)
            if response["Items"]:
                logger.info(f"{response=}")
                item = response["Items"][0]
                logger.info(f"{item=}")
                # DynamoDB の AttributeValue フォーマット（{"N": "123"} や {"S": "android"}）を Python の値に変換する
                for key, value_type in item.items():
                    if "N" in value_type:
                        value = value_type["N"]  # 数値型
                    elif "S" in value_type:
                        value = value_type["S"]  # 文字列型
                    else:
                        value = np.nan  # 未対応の型は欠損値として扱う
                    record[key] = value
            logger.info(f"{record=}")
            return record

        except Exception as e:
            # エラー時は空の辞書を返して推論を継続できるようにする
            logger.info(f"Error: {e}")
            return record


# 現在実行中のスクリプトを AWS ECS Fargate タスクとして起動する関数
# ローカルから ECS にオフロードして大規模なリソースで訓練したい場合に使用する
def run_task(command: list[str], cpu: int = 1024, memory: int = 2048) -> None:
    # コマンドに "python" を先頭に追加し "--ecs" フラグを除去する（無限ループ防止）
    command = ["python"] + command
    command.remove("--ecs")

    ecs_client = boto3.client("ecs")
    response = ecs_client.run_task(
        cluster="mlops-ecs",
        taskDefinition="train-experiment",
        launchType="FARGATE",
        platformVersion="LATEST",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [PUBLIC_SUBNET_1A],  # タスクを起動するサブネット
                "securityGroups": [TRAIN_SECURITY_GROUP],  # タスクに適用するセキュリティグループ
                "assignPublicIp": "ENABLED",  # パブリック IP を付与して外部リソースにアクセス可能にする
            }
        },
        overrides={
            "cpu": str(cpu),
            "memory": str(memory),
            "containerOverrides": [
                {
                    "name": "train",
                    "cpu": cpu,
                    "memory": memory,
                    "command": command,  # 実行するコマンドを上書き
                }
            ],
        },
    )

    # 起動したタスクの ARN からクラスター名とタスク ID を抽出して AWS コンソールの URL を表示する
    cluster_name = response["tasks"][0]["clusterArn"].split("/")[-1]
    task_id = response["tasks"][0]["taskArn"].split("/")[-1]
    print(f"https://ap-northeast-1.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}/tasks/{task_id}")
