# Athenaワークグループ: クエリの実行環境を定義し、クエリ結果の出力先S3バケットを設定する
resource "aws_athena_workgroup" "mlops" {
  name = "mlops"

  configuration {
    result_configuration {
      # Athenaのクエリ結果を保存するS3パスを指定する
      output_location = "s3://${aws_s3_bucket.athena_output.bucket}/output/"
    }
  }
}
