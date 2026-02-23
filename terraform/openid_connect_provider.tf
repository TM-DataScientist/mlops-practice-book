# GitHub ActionsのOIDC連携に必要なリポジトリ名のローカル変数
locals {
  # 自分のGitHubリポジトリ名を設定する
  github_repository = "TM-DataScientist/mlops-practice-book"
}

# OIDCプロバイダー: GitHub ActionsがAWSリソースにアクセスできるようにIDフェデレーションを設定する
# IAMユーザーのアクセスキーを発行せずに、GitHub ActionsのJWTトークンでAWSを操作できる
resource "aws_iam_openid_connect_provider" "github_actions" {
  url            = "https://token.actions.githubusercontent.com" # GitHub ActionsのOIDCエンドポイント
  client_id_list = ["sts.amazonaws.com"]                        # STSサービスへのアクセスを許可するクライアントID
}


# GitHub ActionsロールのAssumeRoleポリシー: 特定リポジトリからのOIDCトークンのみロール引き受けを許可する
data "aws_iam_policy_document" "github_actions" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRoleWithWebIdentity", # WebアイデンティティトークンによるAssumeRoleを許可する
    ]
    # OIDCプロバイダーをフェデレーションプリンシパルとして指定する
    principals {
      type = "Federated"
      identifiers = [
        aws_iam_openid_connect_provider.github_actions.arn
      ]
    }

    # セキュリティ条件1: audクレームがSTSであることを確認する
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # セキュリティ条件2: 指定したGitHubリポジトリからのリクエストのみを許可する（不正リポジトリからの利用を防ぐ）
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${local.github_repository}:*"] # 指定リポジトリの全ブランチ・タグからのアクセスを許可する
    }

  }
}

# GitHub ActionsワークフローのIAMポリシー: CI/CDで必要なAWSサービスへのフルアクセス権限を定義する
data "aws_iam_policy_document" "github_actions_workflow" {
  # S3への完全アクセス（モデルや学習データのアップロード/ダウンロードに使用）
  statement {
    effect = "Allow"
    actions = [
      "s3:*"
    ]
    resources = ["*"]
  }
  # IAMへの完全アクセス（Terraformによるロール管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "iam:*"
    ]
    resources = ["*"]
  }
  # ECRへの完全アクセス（コンテナイメージのビルド・プッシュに使用）
  statement {
    effect = "Allow"
    actions = [
      "ecr:*"
    ]
    resources = ["*"]
  }
  # ECSへの完全アクセス（サービスのデプロイとタスク管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "ecs:*"
    ]
    resources = ["*"]
  }
  # DynamoDBへの完全アクセス（モデルレジストリとフィーチャーストアの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:*"
    ]
    resources = ["*"]
  }
  # CloudWatch Logsへの完全アクセス（ログ確認とリソース管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "logs:*"
    ]
    resources = ["*"]
  }
  # Glueへの完全アクセス（データカタログとクローラーの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "glue:*"
    ]
    resources = ["*"]
  }
  # EC2への完全アクセス（VPC・セキュリティグループ等のネットワーク管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "ec2:*"
    ]
    resources = ["*"]
  }
  # Kinesis Firehoseへの完全アクセス（ログストリームの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "firehose:*"
    ]
    resources = ["*"]
  }
  # ELBへの完全アクセス（ロードバランサーの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "elasticloadbalancing:*"
    ]
    resources = ["*"]
  }
  # Step Functionsへの完全アクセス（学習パイプラインの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "states:*"
    ]
    resources = ["*"]
  }
  # CloudWatchへの完全アクセス（ダッシュボードとアラームの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "cloudwatch:*"
    ]
    resources = ["*"]
  }
  # Application Auto Scalingへの完全アクセス（ECSのオートスケール設定管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "application-autoscaling:*"
    ]
    resources = ["*"]
  }
  # EventBridgeスケジューラーへの完全アクセス（定期スケジュールの管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "scheduler:*"
    ]
    resources = ["*"]
  }
  # Athenaへの完全アクセス（クエリ実行とワークグループ管理に使用）
  statement {
    effect = "Allow"
    actions = [
      "athena:*"
    ]
    resources = ["*"]
  }

  # ECRの認証トークン取得権限（DockerログインのためにCI/CDで使用）
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }
}

# GitHub Actions Role
# GitHub ActionsロールのIAMロール: OIDCトークンを使ってCI/CDがAWSを操作する際に引き受けるロール
resource "aws_iam_role" "github_actions" {
  name               = "mlops-github-actions-role"
  assume_role_policy = data.aws_iam_policy_document.github_actions.json

  tags = {
    Name = "mlops-github-actions-role"
  }
}

# GitHub ActionsワークフローのIAMポリシーを作成する
resource "aws_iam_policy" "github_actions_workflow" {
  name   = "github-actions-policy"
  policy = data.aws_iam_policy_document.github_actions_workflow.json
}

# GitHub Actionsロールにワークフローポリシーをアタッチする
resource "aws_iam_role_policy_attachment" "github_actions_workflow" {
  policy_arn = aws_iam_policy.github_actions_workflow.arn
  role       = aws_iam_role.github_actions.name
}
