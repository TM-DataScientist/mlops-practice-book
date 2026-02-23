# CloudWatchロググループ: Kinesis Firehoseの配信エラーやメトリクスを記録するロググループ（365日保持）
resource "aws_cloudwatch_log_group" "predict_api_kinesis" {
  name              = "/aws/kinesis/predict-api"
  retention_in_days = 365 # 監査・分析目的で長期保持する
}

# CloudWatchログストリーム: Kinesis Firehoseのログ出力先ストリーム
resource "aws_cloudwatch_log_stream" "predict_api_kinesis" {
  name           = "mlops-predict-api-kinesis-log-stream"
  log_group_name = aws_cloudwatch_log_group.predict_api_kinesis.name
}


# Kinesis Firehose配信ストリーム: 推論APIのリクエスト/レスポンスログをS3へリアルタイム転送する
# Fluent Bitサイドカーから受け取ったログデータをバッファリングしてS3に書き込む
resource "aws_kinesis_firehose_delivery_stream" "firelens" {
  name        = "mlops-predict-api-kinesis-firehose"
  destination = "extended_s3" # S3への拡張配信モード（データ変換・圧縮などの追加機能を使用可能）

  extended_s3_configuration {
    role_arn           = aws_iam_role.kinesis.arn         # S3書き込みに使用するIAMロール
    bucket_arn         = aws_s3_bucket.predict_api.arn    # ログ保管先のS3バケット
    buffering_size     = 64                               # バッファサイズ（MB）: 64MBに達したらS3に書き込む
    buffering_interval = 10                               # バッファ時間（秒）: 10秒経過したらS3に書き込む
    prefix             = "predict_log/"                   # S3保存先のプレフィックス（Glueクローラーの対象パスと一致させる）

    # CloudWatch Logsへのエラーログ出力設定
    cloudwatch_logging_options {
      enabled         = "true"
      log_group_name  = aws_cloudwatch_log_group.predict_api_kinesis.name
      log_stream_name = aws_cloudwatch_log_stream.predict_api_kinesis.name
    }
  }
}
