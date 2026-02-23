# terraform applyの完了後に表示される出力値の定義
# これらの値はCI/CDや他のTerraformモジュールから参照できる

# ALBのDNS名: 推論APIへのリクエスト送信先として使用するエンドポイント
output "alb_dns" {
  description = "The DNS name of the load balancer"
  value       = aws_lb.mlops.dns_name
}

# 学習データ保管用S3バケット名: 学習スクリプトやデータ取り込み処理から参照する
output "data_s3_bucket" {
  description = "s3 bucket name for data"
  value       = aws_s3_bucket.data.bucket
}

# 学習済みモデル保管用S3バケット名: 学習バッチがモデルを保存し推論APIが読み込む際に参照する
output "model_s3_bucket" {
  description = "s3 bucket name for model"
  value       = aws_s3_bucket.model.bucket
}

# オフラインフィーチャーストア用S3バケット名: 特徴量の永続化と分析クエリから参照する
output "feature_s3_bucket" {
  description = "s3 bucket name for feature store"
  value       = aws_s3_bucket.feature_store.bucket
}

# Glueカタログデータベース名: AthenaクエリやGlueクローラーの設定で参照する
output "glue_database" {
  description = "database name in glue catalog"
  value       = aws_glue_catalog_database.mlops.name
}

# オンラインフィーチャーストア用DynamoDBテーブル名: 推論APIがリアルタイム特徴量を取得する際に参照する
output "feature_dynamodb_table" {
  description = "dynamodb table name for online feature store"
  value       = aws_dynamodb_table.impression_feature.name
}

# モデルレジストリ用DynamoDBテーブル名: デプロイ対象モデルのバージョン管理に参照する
output "model_registry_dynamodb_table" {
  description = "dynamodb table name for model registry"
  value       = aws_dynamodb_table.model_registry.name
}

# パブリックサブネット1aのID: ECSタスク起動やCI/CDのStep Functions実行設定で参照する
output "public_subnet_1a" {
  description = "resource id for public subnet 1a"
  value       = aws_subnet.public[0].id
}

# 学習パイプライン用セキュリティグループID: ECSタスク起動設定で参照する
output "train_security_group" {
  description = "security group for train pipeline"
  value       = aws_security_group.train.id
}
