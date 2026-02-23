# 推論エンドポイントへのリクエストボディのスキーマ定義
# FastAPI の /predict エンドポイントが受け取る広告リクエストの型を Pydantic で定義する
from pydantic import BaseModel


# 広告インプレッション発生時に推論サーバーへ送信されるリクエストのデータモデル
# Pydantic による型バリデーションにより、不正なリクエストは自動的に 422 エラーを返す
class AdRequest(BaseModel):
    impression_id: str  # インプレッションの一意識別子（ログ追跡用）
    logged_at: str  # インプレッション発生日時（"YYYY-MM-DD HH:MM:SS" 形式の文字列）
    user_id: int  # 広告を閲覧したユーザーのID（DynamoDB 特徴量取得のキーとして使用）
    app_code: int  # 使用しているアプリの識別コード
    os_version: str  # OS バージョンカテゴリ（"old" / "latest" / "intermediate"）
    is_4g: int  # 4G 接続かどうかのフラグ（0: 非4G, 1: 4G）
