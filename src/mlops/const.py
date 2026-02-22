from typing import Final

# Terraform Applyで作成したAWSリソースの値を設定する
MODEL_S3_BUCKET: Final = "mlops-model-20260222094957204900000005"
FEATURE_S3_BUCKET: Final = "mlops-feature-store-20260222094954545300000001"
GLUE_DATABASE: Final = "mlops_db"
FEATURE_DYNAMODB_TABLE: Final = "mlops-impression-feature"
MODEL_REGISTRY_DYNAMODB_TABLE: Final = "mlops-model-registry"
PUBLIC_SUBNET_1A: Final = "subnet-004930bedde98cb44"
TRAIN_SECURITY_GROUP: Final = "sg-09ab5c096ffec4659"
