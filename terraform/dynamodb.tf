# DynamoDBテーブル: オンラインフィーチャーストア用テーブル
# 推論時にリアルタイムで参照するユーザーの行動特徴量を保存する
resource "aws_dynamodb_table" "impression_feature" {
  name           = "mlops-impression-feature"
  billing_mode   = "PAY_PER_REQUEST" # リクエスト課金モード（オートスケール不要でコスト最適）
  hash_key       = "user_id"         # パーティションキー: ユーザーIDで検索する
  stream_enabled = false

  # パーティションキーの型定義（N=数値型）
  attribute {
    name = "user_id"
    type = "N"
  }

  # TTL設定: expired_at属性の値（エポック秒）を過ぎたレコードを自動削除する
  ttl {
    attribute_name = "expired_at"
    enabled        = true
  }

  tags = {
    Name = "mlops-impression-feature-table"
  }
}

# DynamoDBテーブル: モデルレジストリ用テーブル
# 学習済みモデルのメタデータ（モデル名・バージョン・S3パスなど）を管理する
resource "aws_dynamodb_table" "model_registry" {
  name           = "mlops-model-registry"
  billing_mode   = "PAY_PER_REQUEST" # リクエスト課金モード
  hash_key       = "model"           # パーティションキー: モデル名
  range_key      = "version"         # ソートキー: バージョン文字列（"latest"や日時など）
  stream_enabled = false

  # パーティションキーの型定義（S=文字列型）
  attribute {
    name = "model"
    type = "S"
  }

  # ソートキーの型定義（S=文字列型）
  attribute {
    name = "version"
    type = "S"
  }

  tags = {
    Name = "mlops-model-registry-table"
  }
}
