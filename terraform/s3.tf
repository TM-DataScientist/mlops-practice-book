# S3バケット: 学習済みモデルの保管用（モデルバイナリ・学習ログを格納する）
# bucket_prefixを使用してデプロイ環境ごとにユニークなバケット名を自動生成する
resource "aws_s3_bucket" "model" {
  bucket_prefix = "mlops-model-"

  tags = {
    Name = "mlops-model-bucket"
  }
}

# S3バケット: 学習用データの保管用（生データ・前処理済みデータを格納する）
# Glueクローラーがこのバケットをスキャンしてデータカタログを更新する
resource "aws_s3_bucket" "data" {
  bucket_prefix = "mlops-data-"

  tags = {
    Name = "mlops-data-bucket"
  }
}

# S3バケット: オフラインフィーチャーストア用（バッチ処理で生成した特徴量を永続化する）
# GlueクローラーがスキャンしてフィーチャーをAthenaでクエリ可能にする
resource "aws_s3_bucket" "feature_store" {
  bucket_prefix = "mlops-feature-store-"

  tags = {
    Name = "mlops-feature-store-bucket"
  }
}

# S3バケット: 推論APIログ保管用（Kinesis Firehoseが推論リクエスト/レスポンスを書き込む）
# GlueクローラーがスキャンしてログをAthenaで分析可能にする
resource "aws_s3_bucket" "predict_api" {
  bucket_prefix = "mlops-predict-api-"

  tags = {
    Name = "mlops-predict-api-bucket"
  }
}

# S3バケット: Athenaクエリ結果の一時保管用（クエリ実行結果をCSV形式で保存する）
resource "aws_s3_bucket" "athena_output" {
  bucket_prefix = "mlops-athena-output-"

  tags = {
    Name = "mlops-athena-output-bucket"
  }
}
