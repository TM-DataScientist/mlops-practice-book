# Terraformの設定ブロック: 使用するバージョンとバックエンドを定義する
terraform {
  required_version = ">= 1.9, < 2.0"
  # tfstateファイルをS3バケットで管理するリモートバックエンドの設定
  backend "s3" {
    bucket = "mlops-terraform-tfstate-tokyo-20260222" # 作成したS3バケット名を設定する
    key    = "terraform.tfstate"
    region = "ap-northeast-1"

  }
  # 使用するプロバイダーのバージョン制約を定義する
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# AWSプロバイダーの設定: リージョンと全リソースに付与するデフォルトタグを定義する
provider "aws" {
  region = "ap-northeast-1"
  default_tags {
    tags = {
      Name = "mlops-practice"
    }
  }
}

# 現在の実行コンテキスト（AWSアカウントIDなど）を取得するデータソース
data "aws_caller_identity" "current" {}
# 現在のリージョン情報を取得するデータソース
data "aws_region" "current" {}

# 他のファイルから参照しやすいようにアカウントIDとリージョンをローカル変数に格納する
locals {
  aws_account_id = data.aws_caller_identity.current.account_id
  aws_region     = data.aws_region.current.region
}
