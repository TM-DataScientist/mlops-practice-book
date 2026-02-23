# Glueカタログデータベース: S3上のデータをSQLで検索できるようにするメタデータ管理データベース
# Athenaのクエリやクローラーがこのデータベースを参照してテーブルスキーマを取得する
resource "aws_glue_catalog_database" "mlops" {
  name         = "mlops_db"
  location_uri = "s3a://${aws_s3_bucket.data.bucket}/train/" # データの実体が格納されているS3パス
}

# Glueクローラー: 学習データ用
# S3の学習データディレクトリを自動スキャンしてGlueカタログのテーブル定義を更新する
resource "aws_glue_crawler" "mlops" {
  database_name = aws_glue_catalog_database.mlops.name
  name          = "mlops_train_data_crawler"
  role          = aws_iam_role.glue_crawler.arn # クローラーがS3とGlueにアクセスするIAMロール

  # クロール対象のS3パスを指定する
  s3_target {
    path = "s3://${aws_s3_bucket.data.bucket}/train"
  }
}

# Glueクローラー: 推論ログ用
# Kinesis Firehoseが書き込んだ推論ログをクロールしてAthenaで分析可能にする
resource "aws_glue_crawler" "mlops_predict_log" {
  database_name = aws_glue_catalog_database.mlops.name
  name          = "mlops_predict_log_crawler"
  role          = aws_iam_role.glue_crawler.arn

  s3_target {
    path = "s3://${aws_s3_bucket.predict_api.bucket}/predict_log"
  }
}

# Glueクローラー: 学習ログ用
# モデルの学習結果ログ（精度・損失値など）をクロールしてAthenaで分析可能にする
resource "aws_glue_crawler" "mlops_train_log" {
  database_name = aws_glue_catalog_database.mlops.name
  name          = "mlops_train_log_crawler"
  role          = aws_iam_role.glue_crawler.arn

  s3_target {
    path = "s3://${aws_s3_bucket.model.bucket}/train_log"
  }
}

# Glueクローラー: フィーチャーストア用
# S3に保存されたオフラインフィーチャーストアのデータをクロールしてAthenaで分析可能にする
resource "aws_glue_crawler" "mlops_feature_store" {
  database_name = aws_glue_catalog_database.mlops.name
  name          = "mlops_feature_store_crawler"
  role          = aws_iam_role.glue_crawler.arn

  s3_target {
    path = "s3://${aws_s3_bucket.feature_store.bucket}/impression_feature"
  }
}
