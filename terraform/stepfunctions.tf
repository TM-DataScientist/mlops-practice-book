# Step Functionsステートマシン: MLOpsの学習パイプラインを定義する
# 学習バッチの実行 → Glueクローラーの起動 → ECSサービスの更新 の一連のワークフローを管理する
resource "aws_sfn_state_machine" "train" {
  name     = "mlops-train-pipeline"
  role_arn = aws_iam_role.step_functions.arn
  # ステートマシンの定義をJSONテンプレートから生成する（ECSクラスター・タスク定義・サービス名などを注入）
  definition = templatefile("./statemachine_definitions/train_pipeline.json", {
    cluster_arn         = aws_ecs_cluster.mlops.arn
    task_definition_arn = aws_ecs_task_definition.train.arn   # 学習バッチのタスク定義
    security_group      = aws_security_group.train.id         # 学習タスクが使用するセキュリティグループ
    subnet_ids          = jsonencode([for subnet in aws_subnet.public : subnet.id]) # 起動先サブネット（全パブリックサブネット）
    cluster             = aws_ecs_cluster.mlops.name
    main_service        = aws_ecs_service.predict_api_main.name # 学習後にデプロイするメインサービス名
    sub_service         = aws_ecs_service.predict_api_sub.name  # 学習後にデプロイするサブサービス名
  })

  tags = {
    Name = "mlops-train-batch-state-machine"
  }

  # Step Functionsロールが作成された後にステートマシンを作成する
  depends_on = [
    aws_iam_role.step_functions
  ]
}

# EventBridgeスケジュール: 学習パイプラインを毎日0時（UTC）に定期実行するスケジュール設定
# stateをDISABLEDにしているため、デフォルトでは自動実行されない（手動で有効化が必要）
resource "aws_scheduler_schedule" "train" {
  name                = "mlops-train-pipeline-schedule"
  schedule_expression = "cron(0 0 * * ? *)" # 毎日UTC 00:00（JST 09:00）に実行する
  group_name          = "default"
  flexible_time_window {
    mode = "OFF" # フレキシブル時間ウィンドウを使用しない（指定時刻に厳密に実行する）
  }
  target {
    arn      = aws_sfn_state_machine.train.arn   # 実行対象: 学習パイプラインのステートマシン
    role_arn = aws_iam_role.event_bridge.arn      # 実行に使用するIAMロール
  }
  state = "DISABLED" # スケジュールを無効化してコストを削減する（必要時にENABLEDへ変更する）
}
