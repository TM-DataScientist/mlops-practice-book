# CloudWatchダッシュボード: MLOpsシステムの主要メトリクスを一覧表示するダッシュボードを定義する
resource "aws_cloudwatch_dashboard" "mlops" {
  dashboard_name = "mlops"
  # ダッシュボードのウィジェット構成をJSON形式で定義する
  dashboard_body = jsonencode({
    widgets = [
      # ウィジェット1: ECSサービス（main/sub）のCPU使用率を時系列グラフで表示する（左上 6x6）
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 6
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${aws_ecs_service.predict_api_main.name}", "ClusterName", "${aws_ecs_cluster.mlops.name}"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${aws_ecs_service.predict_api_sub.name}", "ClusterName", "${aws_ecs_cluster.mlops.name}"],
          ]
          region = local.aws_region
        }
      },
      # ウィジェット2: ECSサービス（main/sub）のメモリ使用率を時系列グラフで表示する（右上 6x6）
      {
        type   = "metric"
        x      = 6
        y      = 0
        width  = 6
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "${aws_ecs_service.predict_api_main.name}", "ClusterName", "${aws_ecs_cluster.mlops.name}"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "${aws_ecs_service.predict_api_sub.name}", "ClusterName", "${aws_ecs_cluster.mlops.name}"],

          ]
          region = local.aws_region
        }
      },
      # ウィジェット3: ALBのターゲットグループ別レスポンスタイムを時系列グラフで表示する（中央 6x6）
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 6
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ApplicationELB",
              "TargetResponseTime",
              "TargetGroup",
              "${aws_lb_target_group.predict_api_sub.arn_suffix}",
              "LoadBalancer",
              "${aws_lb.mlops.arn_suffix}"
            ],
            [
              "AWS/ApplicationELB",
              "TargetResponseTime",
              "TargetGroup",
              "${aws_lb_target_group.predict_api_main.arn_suffix}",
              "LoadBalancer",
              "${aws_lb.mlops.arn_suffix}"
            ],
          ]
          region = "${local.aws_region}"
        }
      },
      # ウィジェット4: ALBのターゲットグループ別リクエスト数の合計を時系列グラフで表示する（右端 6x6）
      {
        type   = "metric"
        x      = 18
        y      = 0
        width  = 6
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "TargetGroup", "${aws_lb_target_group.predict_api_main.arn_suffix}", "LoadBalancer", "${aws_lb.mlops.arn_suffix}"],
            ["AWS/ApplicationELB", "RequestCount", "TargetGroup", "${aws_lb_target_group.predict_api_sub.arn_suffix}", "LoadBalancer", "${aws_lb.mlops.arn_suffix}"],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          stat    = "Sum"
        }
      },
      # ウィジェット5: ECSサービス別の稼働中タスク数をスパークライン付き単一値で表示する（左下 6x6）
      {
        type   = "metric",
        x      = 0,
        y      = 6,
        width  = 6,
        height = 6,
        properties = {
          sparkline = true,
          view      = "singleValue",
          metrics = [
            ["ECS/ContainerInsights", "RunningTaskCount", "ServiceName", "${aws_ecs_service.predict_api_main.name}", "ClusterName", "${aws_ecs_cluster.mlops.name}"],
            ["ECS/ContainerInsights", "RunningTaskCount", "ServiceName", "${aws_ecs_service.predict_api_sub.name}", "ClusterName", "${aws_ecs_cluster.mlops.name}"],
          ],
          region = local.aws_region
        }
      },
      # ウィジェット6: ALBの5xxエラー数をスパークライン付き単一値で表示する（中央下 6x6）
      {
        "type" : "metric",
        "x" : 6,
        "y" : 6,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "sparkline" : true,
          "view" : "singleValue",
          "metrics" : [
            ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", "${aws_lb.mlops.arn_suffix}"]
          ],
          "region" : local.aws_region,
        }
      },
      # ウィジェット7: predict-apiのログをテーブル形式で表示する（全幅 24x6）
      # ヘルスチェックログを除外し、コンテナIDが存在するログのみをJSON解析して表示する
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          query   = <<EOT
          SOURCE '${aws_cloudwatch_log_group.predict_api.name}'
          | fields @timestamp, @message, @logStream, @log, jsonParse(@message) as json_message
          | filter ispresent(json_message.container_id)
          | sort @timestamp desc
          | unnest json_message.log into event
          | filter ispresent(event) and event != ""
          | filter event not like 'healthcheck'
          EOT
          region  = local.aws_region
          stacked = false
          title   = aws_cloudwatch_log_group.predict_api.name
          view    = "table"
        }
      }
    ]
  })
}
