# ECRリポジトリ: MLOpsメインアプリケーション（学習・推論APIコンテナ）のイメージ保管先
resource "aws_ecr_repository" "mlops" {
  name                 = "mlops-practice"
  image_tag_mutability = "MUTABLE" # 同一タグへの上書きプッシュを許可する（latestタグ運用のため）

  tags = {
    Name = "mlops-ecr-repository"
  }
}

# ECRライフサイクルポリシー: mlopsリポジトリの古いイメージを自動削除してストレージコストを削減する
resource "aws_ecr_lifecycle_policy" "mlops" {
  repository = aws_ecr_repository.mlops.name

  policy = jsonencode(
    {
      "rules" : [
        {
          "rulePriority" : 1,
          "description" : "Delete any image older than 3 days",
          # プッシュから3日以上経過したイメージ（タグ有無問わず）を削除する
          "selection" : {
            "tagStatus" : "any"
            "countType" : "sinceImagePushed",
            "countUnit" : "days",
            "countNumber" : 3
          },
          "action" : {
            "type" : "expire"
          }
        }
      ]
    }
  )
}

# ECRリポジトリ: Fluent Bitサイドカーコンテナ（ログ転送）のイメージ保管先
resource "aws_ecr_repository" "fluentbit" {
  name                 = "fluentbit"
  image_tag_mutability = "MUTABLE" # latestタグ運用のため上書きを許可する

  tags = {
    Name = "mlops-fluentbit-ecr-repository"
  }
}

# ECRライフサイクルポリシー: fluentbitリポジトリの古いイメージを自動削除する
resource "aws_ecr_lifecycle_policy" "fluentbit" {
  repository = aws_ecr_repository.fluentbit.name
  policy = jsonencode(
    {
      "rules" : [
        {
          "rulePriority" : 1,
          "description" : "Delete any image older than 3 days",
          # プッシュから3日以上経過したイメージ（タグ有無問わず）を削除する
          "selection" : {
            "tagStatus" : "any"
            "countType" : "sinceImagePushed",
            "countUnit" : "days",
            "countNumber" : 3
          },
          "action" : {
            "type" : "expire"
          }
        }
      ]
    }
  )

}

# ローカルビルド＆プッシュリソース: Fluent BitのDockerイメージをビルドしてECRへプッシュする
# fluentbitディレクトリ配下のファイル変更を検知して再実行するトリガーを持つ
resource "null_resource" "fluentbit" {
  # Trigger when any file in the fluentbit directory changes
  triggers = {
    fluentbit_hash = sha256(join("", [
      for f in fileset("fluentbit", "**/*") :
      filesha256("fluentbit/${f}")
    ]))
  }

  # Authenticate to ECR
  provisioner "local-exec" {
    command = "aws ecr get-login-password --region ${local.aws_region} | docker login --username AWS --password-stdin ${local.aws_account_id}.dkr.ecr.ap-northeast-1.amazonaws.com"
  }

  # Build the image for Fluent Bit
  provisioner "local-exec" {
    command = "docker build --platform linux/x86_64 -f fluentbit/Dockerfile -t predict-api-fluentbit ."
  }

  # Tag the image
  provisioner "local-exec" {
    command = "docker tag predict-api-fluentbit:latest ${aws_ecr_repository.fluentbit.repository_url}:latest"
  }

  # Push the image to ECR
  provisioner "local-exec" {
    command = "docker push ${aws_ecr_repository.fluentbit.repository_url}:latest"
  }

  # ECRリポジトリとライフサイクルポリシーの作成後に実行する
  depends_on = [
    aws_ecr_repository.fluentbit,
    aws_ecr_lifecycle_policy.fluentbit
  ]
}
