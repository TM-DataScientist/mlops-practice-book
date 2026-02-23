# ECSクラスター: MLOpsシステム全体のコンテナを管理するクラスター
# Container Insightsを有効化してCPU/メモリ/タスク数などのメトリクスをCloudWatchに送信する
resource "aws_ecs_cluster" "mlops" {
  name = "mlops-ecs"
  setting {
    name  = "containerInsights"
    value = "enabled" # CloudWatch Container Insightsを有効化する
  }
}

# CloudWatchロググループ: 学習バッチタスクのログ保管先（保持期間14日）
resource "aws_cloudwatch_log_group" "train" {
  name              = "/mlops/ecs/train"
  retention_in_days = 14
}

# CloudWatchロググループ: Fluent Bitサイドカーのログ保管先（保持期間14日）
resource "aws_cloudwatch_log_group" "fluentbit" {
  name              = "/mlops/ecs/fluentbit"
  retention_in_days = 14
}

# CloudWatchロググループ: 推論APIコンテナのアプリケーションログ保管先（保持期間14日）
resource "aws_cloudwatch_log_group" "predict_api" {
  name              = "/mlops/ecs/predict-api"
  retention_in_days = 14
}

# ECSタスク定義: 本番学習バッチ用（SGD分類器、latestイメージを使用）
# Fargate起動タイプ、1vCPU/2GBメモリで実行する
resource "aws_ecs_task_definition" "train" {
  family                   = "train"
  network_mode             = "awsvpc"
  cpu                      = 1024  # 1 vCPU
  memory                   = 2048  # 2 GB
  requires_compatibilities = ["FARGATE"]
  # コンテナ定義をテンプレートファイルから生成する（モデル名・学習期間上限を注入）
  container_definitions = templatefile("./container_definitions/train.json", {
    ecr_uri           = aws_ecr_repository.mlops.repository_url,
    image_tag         = "latest",
    model_name        = "sgd_classifier_ctr",
    train_datetime_ub = "2018-12-10 00:00:00" # 学習データの日時上限
  })
  task_role_arn      = aws_iam_role.ecs_task.arn           # タスク実行中のAWSリソースアクセス権限
  execution_role_arn = aws_iam_role.ecs_task_execution.arn # コンテナ起動（ECR/CloudWatchアクセス）に必要な権限
}

# ECSタスク定義: 実験用学習バッチ（localタグのイメージを使用してローカルビルドを試験できる）
resource "aws_ecs_task_definition" "train_experiment" {
  family                   = "train-experiment"
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  requires_compatibilities = ["FARGATE"]
  container_definitions = templatefile("./container_definitions/train.json", {
    ecr_uri           = aws_ecr_repository.mlops.repository_url,
    image_tag         = "local", # ローカルビルドイメージを使用する（実験・デバッグ用）
    model_name        = "sgd_classifier_ctr",
    train_datetime_ub = "2018-12-10 00:00:00",
  })
  task_role_arn      = aws_iam_role.ecs_task.arn
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
}

# ECSタスク定義: 推論APIメイン（SGD分類器モデル、Fluent Bitサイドカー付き）
# Fluent Bitでリクエスト/レスポンスログをKinesis Firehose経由でS3へ転送する
resource "aws_ecs_task_definition" "predict_api_main" {
  family                   = "predict-api-main"
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  requires_compatibilities = ["FARGATE"]
  container_definitions = templatefile("./container_definitions/predict_api.json", {
    ecr_uri         = aws_ecr_repository.mlops.repository_url,
    model_name      = "sgd_classifier_ctr", # 使用モデル: SGD分類器（CTR予測）
    model_version   = "latest",
    feature_version = "latest",
    fluent_bid_uri  = aws_ecr_repository.fluentbit.repository_url, # ログ転送用サイドカーのECR URI
  })
  task_role_arn      = aws_iam_role.ecs_task.arn
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
}

# ECSキャパシティプロバイダー設定: コストを抑えるためFARGATE_SPOTをデフォルトとして使用する
resource "aws_ecs_cluster_capacity_providers" "mlops" {
  cluster_name = aws_ecs_cluster.mlops.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  # デフォルトはFARGATE_SPOT（スポットインスタンスで最大70%コスト削減）
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
    base              = 0
  }
}

# ECSサービス: 推論APIメイン（本番トラフィックを受け付けるメインサービス）
# ローリングアップデートとサーキットブレーカーを設定してデプロイの安全性を担保する
resource "aws_ecs_service" "predict_api_main" {
  name                              = "predict-api-main"
  cluster                           = aws_ecs_cluster.mlops.name
  task_definition                   = aws_ecs_task_definition.predict_api_main.arn
  desired_count                     = 0 # 初期タスク数0（スケジュールアクションで起動する）
  health_check_grace_period_seconds = 2 # ヘルスチェック開始までの猶予時間（秒）

  # Rolling Update
  deployment_minimum_healthy_percent = 0   # デプロイ中に最低限維持するタスク数の割合（0=全停止→起動を許可）
  deployment_maximum_percent         = 100 # デプロイ中の最大タスク数の割合

  # Circuit breaker
  deployment_circuit_breaker {
    enable   = true # デプロイ失敗時に自動停止する
    rollback = true # デプロイ失敗時に直前の正常バージョンへ自動ロールバックする
  }
  # FARGATE_SPOTを使用してコストを削減する
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }
  network_configuration {
    security_groups  = [aws_security_group.predict_api.id]
    subnets          = [for subnet in aws_subnet.public : subnet.id]
    assign_public_ip = true # パブリックサブネットで動作するためパブリックIPを付与する
  }
  # ALBターゲットグループへ登録してロードバランシングを受ける
  load_balancer {
    target_group_arn = aws_lb_target_group.predict_api_main.arn
    container_name   = "predict-api"
    container_port   = 8080
  }

  depends_on = [
    aws_ecs_task_definition.predict_api_main,
    aws_lb_target_group.predict_api_main
  ]
}



# ECSタスク定義: 推論APIサブ（LightGBMモデル、A/Bテスト・シャドウテスト用）
resource "aws_ecs_task_definition" "predict_api_sub" {
  family                   = "predict-api-sub"
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  requires_compatibilities = ["FARGATE"]
  container_definitions = templatefile("./container_definitions/predict_api.json", {
    ecr_uri         = aws_ecr_repository.mlops.repository_url,
    model_name      = "lightgbm_ctr", # 使用モデル: LightGBM（CTR予測）
    model_version   = "latest",
    feature_version = "latest",
    fluent_bid_uri  = aws_ecr_repository.fluentbit.repository_url,
  })
  task_role_arn      = aws_iam_role.ecs_task.arn
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
}

# ECSサービス: 推論APIサブ（新モデルのA/Bテストや段階的リリースに使用するサービス）
resource "aws_ecs_service" "predict_api_sub" {
  name                              = "predict-api-sub"
  cluster                           = aws_ecs_cluster.mlops.name
  task_definition                   = aws_ecs_task_definition.predict_api_sub.arn
  desired_count                     = 0 # 初期タスク数0（必要時にスケールアウトする）
  health_check_grace_period_seconds = 2

  # Rolling Update
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  # Circuit breaker
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }
  network_configuration {
    security_groups  = [aws_security_group.predict_api.id]
    subnets          = [for subnet in aws_subnet.public : subnet.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.predict_api_sub.arn
    container_name   = "predict-api"
    container_port   = 8080
  }

  depends_on = [
    aws_ecs_task_definition.predict_api_sub,
    aws_lb_target_group.predict_api_sub
  ]
}

# Application Auto Scalingターゲット: 推論APIメインのスケール対象を定義する（最小1〜最大5タスク）
resource "aws_appautoscaling_target" "predict_api_main" {
  min_capacity       = 1 # 最小タスク数
  max_capacity       = 5 # 最大タスク数
  resource_id        = "service/${aws_ecs_cluster.mlops.name}/${aws_ecs_service.predict_api_main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scalingポリシー: 推論APIメインのCPU使用率50%を目標にタスク数を自動調整する
resource "aws_appautoscaling_policy" "predict_api_main" {
  name               = "predict-api-main-request-count-policy"
  policy_type        = "TargetTrackingScaling" # ターゲット追跡スケーリング（目標値に追跡）
  resource_id        = aws_appautoscaling_target.predict_api_main.resource_id
  scalable_dimension = aws_appautoscaling_target.predict_api_main.scalable_dimension
  service_namespace  = aws_appautoscaling_target.predict_api_main.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization" # 平均CPU使用率でスケールする
    }
    scale_in_cooldown  = 10 # スケールイン後の待機時間（秒）
    scale_out_cooldown = 10 # スケールアウト後の待機時間（秒）
    target_value       = 50 # CPU使用率50%を目標値とする
  }
}

# Application Auto Scalingターゲット: 推論APIサブのスケール対象を定義する（最小1〜最大5タスク）
resource "aws_appautoscaling_target" "predict_api_sub" {
  min_capacity       = 1
  max_capacity       = 5
  resource_id        = "service/${aws_ecs_cluster.mlops.name}/${aws_ecs_service.predict_api_sub.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scalingポリシー: 推論APIサブのCPU使用率50%を目標にタスク数を自動調整する
resource "aws_appautoscaling_policy" "predict_api_sub" {
  name               = "predict-api-sub-app-autoscaling-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.predict_api_sub.resource_id
  scalable_dimension = aws_appautoscaling_target.predict_api_sub.scalable_dimension
  service_namespace  = aws_appautoscaling_target.predict_api_sub.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 10
    scale_out_cooldown = 10
    target_value       = 50
  }
}

# To reduce ECS costs, create scheduled action to change the ECS Task count to 0
# スケジュールアクション: 推論APIメインを毎時0分にタスク数0へリセットしてコストを削減する（UTC 00:00 = JST 09:00）
resource "aws_appautoscaling_scheduled_action" "predict_api_main" {
  name               = "predict-api-main-scheduled-action"
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.mlops.name}/${aws_ecs_service.predict_api_main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  schedule           = "cron(0 0 * * * ?)" # 毎時0分に実行する（6フィールド形式）

  scalable_target_action {
    min_capacity = 0 # タスク数を0にしてFargate課金を停止する
    max_capacity = 0
  }
}

# スケジュールアクション: 推論APIサブを毎時0分にタスク数0へリセットしてコストを削減する
resource "aws_appautoscaling_scheduled_action" "predict_api_sub" {
  name               = "predict-api-sub-scheduled-action"
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.mlops.name}/${aws_ecs_service.predict_api_sub.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  schedule           = "cron(0 0 * * * ?)"

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}
