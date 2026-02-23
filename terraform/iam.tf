# ECS Task Execution Role
# ECSタスク実行ロールのポリシー定義: コンテナ起動に必要なEC2/CloudWatch/ECRへのアクセス権限
data "aws_iam_policy_document" "ecs_task_execution" {
  # ECSがVPC内でコンテナを起動するためのEC2ネットワーク操作権限
  statement {
    effect = "Allow"
    actions = [
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:CreateSecurityGroup",
      "ec2:CreateTags",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeSubnets",
      "ec2:DescribeVpcs",
      "ec2:DeleteSecurityGroup",
    ]
    resources = ["*"]
  }
  # コンテナのログをCloudWatch Logsへ送信するための権限
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }
  # ECRからコンテナイメージをプルするための権限
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability"
    ]
    resources = ["*"]
  }
}

# ECSタスク実行ロール用IAMポリシーを作成する
resource "aws_iam_policy" "ecs_task_execution" {
  name   = "mlops-ecs-task-exection-policy"
  policy = data.aws_iam_policy_document.ecs_task_execution.json

  tags = {
    Name = "mlops-ecs-task-execution-policy"
  }
}

# ECSタスク実行ロールの信頼ポリシー: ECSタスクサービスにこのロールの引き受けを許可する
data "aws_iam_policy_document" "ecs_task_execution_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# ECSタスク実行ロール: コンテナエージェントがECRやCloudWatchにアクセスする際に使用するロール
resource "aws_iam_role" "ecs_task_execution" {
  name               = "mlops-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json

  tags = {
    Name = "mlops-ecs-task-execution-role"
  }
}

# ECSタスク実行ロールにポリシーをアタッチする
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.ecs_task_execution.arn
}


# ECS Task Role
# ECSタスクロールのポリシー定義: コンテナ内のアプリが使用するAWSサービスへのアクセス権限
data "aws_iam_policy_document" "ecs_task" {
  # CloudWatch Logsへのログ書き込み権限
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup",
      "logs:DescribeLogGroups",
      "logs:GetLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["*"]
  }

  # S3バケットへのデータ読み書き権限（モデル/データ/フィーチャーストアのアクセスに使用）
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts",
      "s3:AbortMultipartUpload",
      "s3:CreateBucket",
      "s3:PutObject",
      "s3:PutBucketPublicAccessBlock"
    ]
    resources = ["*"]
  }

  # Athenaクエリ実行権限（推論ログの分析に使用）
  statement {
    effect = "Allow"
    actions = [
      "athena:*",
    ]
    resources = ["*"]
  }

  # Glueデータカタログの読み書き権限（Athenaがテーブル定義を参照するために必要）
  statement {
    effect = "Allow"
    actions = [
      "glue:CreateDatabase",
      "glue:DeleteDatabase",
      "glue:GetCatalog",
      "glue:GetCatalogs",
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:UpdateDatabase",
      "glue:CreateTable",
      "glue:DeleteTable",
      "glue:BatchDeleteTable",
      "glue:UpdateTable",
      "glue:GetTable",
      "glue:GetTables",
      "glue:BatchCreatePartition",
      "glue:CreatePartition",
      "glue:DeletePartition",
      "glue:BatchDeletePartition",
      "glue:UpdatePartition",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:BatchGetPartition",
      "glue:StartColumnStatisticsTaskRun",
      "glue:GetColumnStatisticsTaskRun",
      "glue:GetColumnStatisticsTaskRuns",
      "glue:GetCatalogImportStatus"
    ]
    resources = ["*"]
  }

  # DynamoDBアクセス権限（オンラインフィーチャーストアとモデルレジストリの読み書きに使用）
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:Query"
    ]
    resources = ["*"]
  }
  # Kinesis Firehoseへの書き込み権限（推論ログをS3へストリーミング転送するために使用）
  statement {
    effect = "Allow"
    actions = [
      "firehose:PutRecord",
      "firehose:PutRecordBatch",
    ]
    resources = [
      "*"
    ]
  }
}



# ECSタスクロール用IAMポリシーを作成する
resource "aws_iam_policy" "ecs_task" {
  name   = "mlops-ecs-task-policy"
  policy = data.aws_iam_policy_document.ecs_task.json

  tags = {
    Name = "mlops-ecs-task-policy"
  }
}

# ECSタスクロールの信頼ポリシー: EC2/SSM/ECSタスクサービスにロールの引き受けを許可する
data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com", "ssm.amazonaws.com", "ecs-tasks.amazonaws.com"]
    }
  }
}

# ECSタスクロール: コンテナ内のアプリケーションがAWSリソースにアクセスする際に使用するロール
resource "aws_iam_role" "ecs_task" {
  name               = "mlops-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "mlops-ecs-task-role"
  }
}

# ECSタスクロールにポリシーをアタッチする
resource "aws_iam_role_policy_attachment" "ecs_task" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task.arn
}

# Step Functions Role
# Step Functionsロールのポリシー定義: ステートマシンがAWSサービスを操作するための権限
data "aws_iam_policy_document" "step_functions" {
  # CloudWatch Logsへのログ配信設定権限（ステートマシンの実行ログ記録に使用）
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
  # ECSタスクの起動権限（学習バッチをFargateで実行するために使用）
  statement {
    effect = "Allow"
    actions = [
      "ecs:RunTask",
    ]
    resources = ["*"]
  }
  # Glueクローラーの起動・状態確認権限（学習後にデータカタログを更新するために使用）
  statement {
    effect = "Allow"
    actions = [
      "glue:StartCrawler",
      "glue:GetCrawler"
    ]
    resources = ["*"]
  }
  # X-Rayトレース送信権限（ステートマシンの分散トレーシングに使用）
  statement {
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
    ]
    resources = ["*"]
  }
  # IAMロール委譲権限（ECSタスク起動時にタスクロールを渡すために必要）
  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = ["*"]
  }
  # EventBridgeルール操作権限（ステートマシンからEventBridgeを制御するために使用）
  statement {
    effect = "Allow"
    actions = [
      "events:PutTargets",
      "events:PutRule",
      "events:DescribeRule",
    ]
    resources = [
      "arn:aws:events:${local.aws_region}:${local.aws_account_id}:rule/*",
    ]
  }
  # ECSサービス更新権限（新モデルデプロイ後にサービスのタスク定義を更新するために使用）
  statement {
    effect = "Allow"
    actions = [
      "ecs:UpdateService"
    ]
    resources = [
      "*"
    ]
  }
}

# Step Functionsロール用IAMポリシーを作成する
resource "aws_iam_policy" "step_functions" {
  name   = "mlops-step-functions-policy"
  policy = data.aws_iam_policy_document.step_functions.json

  tags = {
    Name = "mlops-step-functions-policy"
  }
}


# Step Functionsロールの信頼ポリシー: Step FunctionsサービスにAssumeRoleを許可する
data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

# Step Functionsロール: ステートマシン（学習パイプライン）が使用するIAMロール
resource "aws_iam_role" "step_functions" {
  name               = "mlops-step-functions-role"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json

  tags = {
    Name = "mlops-step-functions-role"
  }
}

# Step FunctionsロールにポリシーをアタッチするM
resource "aws_iam_role_policy_attachment" "step_functions" {
  role       = aws_iam_role.step_functions.name
  policy_arn = aws_iam_policy.step_functions.arn
}

# Event Bridge Role
# EventBridgeロールのポリシー定義: スケジューラーがStep FunctionsやELBを操作するための権限
data "aws_iam_policy_document" "event_bridge" {
  # Step Functionsのステートマシン実行権限（学習パイプラインをスケジュール起動するために使用）
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = ["*"]
  }
  # ELB操作権限とCloudWatch Logsへのログ書き込み権限（コスト削減のためELBを定期削除するために使用）
  statement {
    effect = "Allow"
    actions = [
      "elasticloadbalancing:DeleteLoadBalancer",
      "elasticloadbalancing:DeleteTargetGroup",
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeListeners",
      "elasticloadbalancing:DescribeRules",
      "elasticloadbalancing:DescribeTargetHealth",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

# EventBridgeロール用IAMポリシーを作成する
resource "aws_iam_policy" "event_bridge" {
  name   = "mlops-event-bridge-policy"
  policy = data.aws_iam_policy_document.event_bridge.json

  tags = {
    Name = "mlops-event-bridge-policy"
  }
}

# EventBridgeスケジューラーの信頼ポリシー: EventBridgeスケジューラーにAssumeRoleを許可する
data "aws_iam_policy_document" "event_bridge_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

# EventBridgeロール: スケジューラーがStep FunctionsやELBを操作する際に使用するIAMロール
resource "aws_iam_role" "event_bridge" {
  name               = "mlops-event-bridge-role"
  assume_role_policy = data.aws_iam_policy_document.event_bridge_assume_role.json

  tags = {
    Name = "mlops-event-bridge-role"
  }
}

# EventBridgeロールにポリシーをアタッチする
resource "aws_iam_role_policy_attachment" "event_bridge" {
  role       = aws_iam_role.event_bridge.name
  policy_arn = aws_iam_policy.event_bridge.arn
}

# Glue Crawler Role
# Glueクローラーロールのポリシー定義: クローラーがS3を読み取りGlueカタログを更新するための権限
data "aws_iam_policy_document" "glue_crawler" {
  # S3バケットのオブジェクト一覧取得・読み取り権限（クロール対象データの参照に使用）
  statement {
    effect = "Allow"
    actions = [
      "s3:List*",
      "s3:Get*",
    ]
    resources = ["*"]
  }
  # Glueカタログのテーブル・パーティション管理権限（クロール結果をカタログに書き込むために使用）
  statement {
    effect = "Allow"
    actions = [
      "glue:GetCrawler",
      "glue:GetTable",
      "glue:GetDatabase",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:BatchCreatePartition",
      "glue:BatchGetPartition",
    ]
    resources = ["*"]
  }
  # CloudWatch Logsへのログ書き込み権限（クローラーの実行ログ記録に使用）
  statement {
    effect = "Allow"
    actions = [
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }
}

# Glueクローラーロール用IAMポリシーを作成する
resource "aws_iam_policy" "glue_crawler" {
  name   = "mlops-glue-cralwer-policy"
  policy = data.aws_iam_policy_document.glue_crawler.json

  tags = {
    Name = "mlops-glue-crawler-policy"
  }
}

# Glueクローラーの信頼ポリシー: GlueサービスにAssumeRoleを許可する
data "aws_iam_policy_document" "glue_crawler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

# Glueクローラーロール: Glueクローラーが使用するIAMロール
resource "aws_iam_role" "glue_crawler" {
  name               = "mlops-glue-crawler-role"
  assume_role_policy = data.aws_iam_policy_document.glue_crawler_assume_role.json

  tags = {
    Name = "mlops-glue-crawler-role"
  }
}

# GlueクローラーロールにポリシーをアタッチするM
resource "aws_iam_role_policy_attachment" "glue_crawler" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = aws_iam_policy.glue_crawler.arn
}


# Kinesis Firehose Role
# Kinesis Firehoseロールのポリシー定義: FirehoseがS3へデータを書き込むための権限
data "aws_iam_policy_document" "kinesis" {
  statement {
    sid = "S3Access"

    effect = "Allow"
    # FirehoseがS3バケットにデータを書き込むために必要な最小限のS3権限
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject"
    ]
    # 推論ログ保管用S3バケットのみにアクセスを制限する（最小権限の原則）
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.predict_api.bucket}",
      "arn:aws:s3:::${aws_s3_bucket.predict_api.bucket}/*",
    ]
  }
}

# Kinesis Firehoseロール用IAMポリシーを作成する
resource "aws_iam_policy" "kinesis" {
  name   = "mlops-kinesis-policy"
  policy = data.aws_iam_policy_document.kinesis.json

  tags = {
    Name = "mlops-kinesis-policy"
  }
}

# Kinesis Firehoseの信頼ポリシー: FirehoseサービスにAssumeRoleを許可する
data "aws_iam_policy_document" "kinesis_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}

# Kinesis Firehoseロール: FirehoseがS3へデータを転送する際に使用するIAMロール
resource "aws_iam_role" "kinesis" {
  name               = "mlops-kinesis-role"
  assume_role_policy = data.aws_iam_policy_document.kinesis_assume_role.json

  tags = {
    Name = "mlops-kinesis-role"
  }
}

# Kinesis FirehoseロールにポリシーをアタッチするM
resource "aws_iam_role_policy_attachment" "kinesis" {
  role       = aws_iam_role.kinesis.name
  policy_arn = aws_iam_policy.kinesis.arn
}
