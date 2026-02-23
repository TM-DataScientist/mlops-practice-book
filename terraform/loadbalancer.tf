# Application Load Balancer: 推論APIへのHTTPトラフィックを振り分けるALB
# メインとサブのECSサービスへのウェイトベースルーティングに使用する
resource "aws_lb" "mlops" {
  load_balancer_type = "application" # ALB（レイヤー7ロードバランサー）を使用する
  name               = "mlops-alb"

  security_groups = [aws_security_group.alb.id]
  subnets         = aws_subnet.public[*].id # 全パブリックサブネットに配置して高可用性を確保する
}


# ELB Target Group
# ターゲットグループ（メイン）: predict-api-mainサービスへトラフィックを転送するターゲットグループ
resource "aws_lb_target_group" "predict_api_main" {
  name = "predict-api-main-target-group"

  port                 = 8080
  protocol             = "HTTP"
  target_type          = "ip"           # Fargateのコンテナに直接ルーティングするためIPターゲットを使用する
  vpc_id               = aws_vpc.mlops.id
  deregistration_delay = 0              # ドレイン時間0秒（コスト節約のため即時デタッチ）
  # ヘルスチェック設定: /healthcheckエンドポイントを短い間隔で確認する
  health_check {
    interval            = 5  # チェック間隔（秒）
    timeout             = 2  # タイムアウト（秒）
    healthy_threshold   = 2  # 正常判定に必要な連続成功回数
    unhealthy_threshold = 2  # 異常判定に必要な連続失敗回数
    port                = 8080
    path                = "/healthcheck"
  }
}

# ELB Target Group
# ターゲットグループ（サブ）: predict-api-subサービスへトラフィックを転送するターゲットグループ
resource "aws_lb_target_group" "predict_api_sub" {
  name = "predict-api-sub-target-group"

  port                 = 8080
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.mlops.id
  deregistration_delay = 0
  health_check {
    interval            = 5
    timeout             = 2
    healthy_threshold   = 2
    unhealthy_threshold = 2
    port                = 8080
    path                = "/healthcheck"
  }
}

# Listener
# ALBリスナー: ポート8080でHTTPリクエストを受け付けてデフォルトでメインターゲットグループへ転送する
resource "aws_lb_listener" "predict_api" {
  load_balancer_arn = aws_lb.mlops.arn
  port              = "8080"
  protocol          = "HTTP"

  # デフォルトアクション: /predict以外のパスはメインターゲットグループへ転送する
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.predict_api_main.arn
  }

  depends_on = [
    aws_lb_target_group.predict_api_main,
    aws_lb_target_group.predict_api_sub
  ]
}

# ALBリスナールール: /predictへのリクエストをメイン100%・サブ0%の比率でルーティングする
# weightを変更することでA/Bテストや段階的リリース（カナリアリリース）を実現できる
resource "aws_lb_listener_rule" "predict_api" {
  listener_arn = aws_lb_listener.predict_api.arn
  priority     = 100 # ルールの優先度（数値が小さいほど優先される）

  action {
    type = "forward"
    forward {
      # メインサービスに100%のトラフィックを送る（サブに流す場合はweightを変更する）
      target_group {
        arn    = aws_lb_target_group.predict_api_main.arn
        weight = 100
      }
      target_group {
        arn    = aws_lb_target_group.predict_api_sub.arn
        weight = 0
      }
    }
  }

  # このルールは /predict パスへのリクエストにのみ適用する
  condition {
    path_pattern {
      values = ["/predict"]
    }
  }
}

# To reduce ELB costs, create the event bridge to delete the ELB and target groups.
# ELBコスト削減設定: EventBridgeスケジューラーでALBとターゲットグループを定期的に削除する
locals {
  delete_elb_state = "ENABLED" # Change to "DISABLED" to disable the schedule
  target_group_arns = [
    aws_lb_target_group.predict_api_main.arn,
    aws_lb_target_group.predict_api_sub.arn
  ]
}

# EventBridgeスケジュール: 2時間ごとにALBを削除してELBの時間課金を停止する
resource "aws_scheduler_schedule" "elb_delete" {
  name                = "mlops-elb-delete-schedule"
  schedule_expression = "cron(0 */2 * * ? *)" # 2時間ごとの毎時0分に実行する
  group_name          = "default"
  state               = local.delete_elb_state

  flexible_time_window {
    mode = "OFF" # フレキシブル時間ウィンドウを使用しない（指定時刻に厳密に実行する）
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:elasticloadbalancingv2:deleteLoadBalancer"
    role_arn = aws_iam_role.event_bridge.arn
    input = jsonencode({
      LoadBalancerArn = aws_lb.mlops.arn # 削除対象のALB ARN
    })
  }
}


# EventBridgeスケジュール: 2時間ごとにターゲットグループを削除する（メイン/サブ各1つ）
# count.indexを使って複数ターゲットグループに対して同一設定を適用する
resource "aws_scheduler_schedule" "elb_target_delete" {
  count               = length(local.target_group_arns)
  name                = "mlops-elb-target-delete-${count.index}-schedule"
  schedule_expression = "cron(0 */2 * * ? *)"
  group_name          = "default"
  state               = local.delete_elb_state

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:elasticloadbalancingv2:deleteTargetGroup"
    role_arn = aws_iam_role.event_bridge.arn
    input = jsonencode({
      TargetGroupArn = local.target_group_arns[count.index] # インデックスでターゲットグループを選択する
    })
  }
}
