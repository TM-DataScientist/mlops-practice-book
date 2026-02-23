# プロジェクト全体で共通利用する AWS リソース名・IDの定数定義
# Terraform で作成したリソースの値をここで一元管理する
from typing import Final

# Terraform Applyで作成したAWSリソースの値を設定する

# 訓練済みモデルのアーティファクトを保存する S3 バケット名
MODEL_S3_BUCKET: Final = "mlops-model-20260222094957204900000005"

# 特徴量ストア（オフライン）のデータを保存する S3 バケット名
FEATURE_S3_BUCKET: Final = "mlops-feature-store-20260222094954545300000001"

# Athena でクエリ対象となる Glue データカタログのデータベース名
GLUE_DATABASE: Final = "mlops_db"

# ユーザーごとの最新インプレッション特徴量を保存する DynamoDB テーブル名（オンライン特徴量ストア）
FEATURE_DYNAMODB_TABLE: Final = "mlops-impression-feature"

# 訓練済みモデルのバージョン管理を行う DynamoDB テーブル名（モデルレジストリ）
MODEL_REGISTRY_DYNAMODB_TABLE: Final = "mlops-model-registry"

# ECS タスクを起動するパブリックサブネットの ID（ap-northeast-1a）
PUBLIC_SUBNET_1A: Final = "subnet-004930bedde98cb44"

# ECS タスクに割り当てるセキュリティグループの ID
TRAIN_SECURITY_GROUP: Final = "sg-09ab5c096ffec4659"
