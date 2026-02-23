# 利用可能なアベイラビリティゾーンの一覧を取得するデータソース
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
# MLOpsシステム用VPC: 10.0.0.0/16のCIDRブロックでプライベートネットワークを構築する
resource "aws_vpc" "mlops" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true  # VPC内のDNS解決を有効化する
  enable_dns_hostnames = true  # VPC内のインスタンスにDNSホスト名を付与する

  tags = {
    Name = "mlops-vpc"
  }
}

# SecurityGroup for ML Pipeline
# セキュリティグループ: 学習バッチ用（アウトバウンドのHTTPS通信のみ許可）
# ECRからのイメージプルやS3/DynamoDBへのアクセスに必要なHTTPS通信を許可する
resource "aws_security_group" "train" {
  name        = "mlops-train-sg"
  description = "security group for train"
  vpc_id      = aws_vpc.mlops.id

  # アウトバウンド: HTTPS（443）のみ許可してセキュアな通信に制限する
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mlops-train-sg"
  }
}

# SecurityGroup for application load balancer
# セキュリティグループ: ALB用（インターネットからポート8080のHTTPを受け付ける）
resource "aws_security_group" "alb" {
  name        = "mlops-alb-sg"
  description = "security group for alb of prediction server"
  vpc_id      = aws_vpc.mlops.id
  # インバウンド: ポート8080のHTTPを全IPから受け付ける
  ingress {
    from_port = 8080
    to_port   = 8080
    protocol  = "tcp"
    # Warning: In production, restrict the source of requests
    cidr_blocks = ["0.0.0.0/0"]
  }

  # アウトバウンド: 全ポート・全プロトコルを許可する（ECSコンテナへの転送のため）
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # -1は全プロトコルを意味する
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mlops-predictor-alb-sg"
  }
}

# SecurityGroup for predict api
# セキュリティグループ: 推論APIコンテナ用（ALBからのポート8080のHTTPのみ受け付ける）
# ALBのセキュリティグループからのアクセスのみ許可してセキュリティを強化する
resource "aws_security_group" "predict_api" {
  name        = "mlops-predict-api-sg"
  description = "security group for predict api"
  vpc_id      = aws_vpc.mlops.id
  # インバウンド: ALBのセキュリティグループからのポート8080のみ許可する（直接アクセスを遮断）
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  # アウトバウンド: 全ポート・全プロトコルを許可する（S3/DynamoDB/Kinesis等への通信のため）
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mlops-predictor-api-sg"
  }
}

# Subnet
# パブリックサブネット: 利用可能なAZ数に応じて自動的に複数サブネットを作成する（マルチAZ構成）
resource "aws_subnet" "public" {
  count             = length(data.aws_availability_zones.available.names) # AZ数分のサブネットを作成する
  vpc_id            = aws_vpc.mlops.id
  cidr_block        = "10.0.${count.index + 1}.0/24" # AZごとに異なるCIDRブロックを割り当てる（例: 10.0.1.0/24, 10.0.2.0/24）
  availability_zone = element(data.aws_availability_zones.available.names, count.index)

  tags = {
    Name = "public-subnet-${element(data.aws_availability_zones.available.names, count.index)}"
  }
}

# Internet Gateway
# インターネットゲートウェイ: VPCとインターネット間の通信を可能にするゲートウェイ
resource "aws_internet_gateway" "mlops" {
  vpc_id = aws_vpc.mlops.id

  tags = {
    Name = "mlops-igw"
  }
}

# Route Table (Public)
# ルートテーブル（パブリック）: インターネット宛て（0.0.0.0/0）のトラフィックをIGWへ転送する
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.mlops.id
  route {
    cidr_block = "0.0.0.0/0"                      # デフォルトルート（全インターネット宛て）
    gateway_id = aws_internet_gateway.mlops.id     # インターネットゲートウェイへ転送する
  }

  tags = {
    Name = "mlops-public-route-table"
  }
}

# Association (Public ${var.aws_region}a)
# ルートテーブルとサブネットの関連付け: 全パブリックサブネットにパブリックルートテーブルを適用する
resource "aws_route_table_association" "public" {
  count          = length(data.aws_availability_zones.available.names)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
