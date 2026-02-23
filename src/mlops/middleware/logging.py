# ロギング設定を行うミドルウェアモジュール
# 標準出力とファイルへの二重出力、UTC タイムスタンプ付きフォーマットを設定する
import logging
import time
from pathlib import Path


# ルートロガーに標準出力ハンドラとファイルハンドラを設定する関数
# 既存のハンドラをすべてクリアしてから再設定するため、重複ログの出力を防ぐ
def set_logger_config(log_file_path: Path) -> None:
    # ログフォーマット: "タイムスタンプ ロガー名 ログレベル: メッセージ"
    fmt = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    logging_formatter = logging.Formatter(fmt)
    # タイムスタンプを UTC で出力する（本番環境での時刻統一のため）
    logging_formatter.converter = time.gmtime
    level = logging.INFO

    # ルートロガーを取得してレベルを設定する
    logger = logging.getLogger()
    logger.setLevel(level)

    # 既存のハンドラが残っていると重複出力になるためすべてクリアする
    if len(logger.handlers):
        logger.handlers.clear()
        logger.root.handlers.clear()

    # 標準出力ハンドラを追加する（コンソールでリアルタイムに確認するため）
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging_formatter)
    logger.addHandler(stream_handler)

    # ファイルハンドラを追加する（アーティファクトとしてログを永続化するため）
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(level)
    file_handler.setFormatter(logging_formatter)
    logger.addHandler(file_handler)

    # turn off logs for botocore
    # botocore の詳細ログは非常に冗長なため CRITICAL レベル以上のみ出力する
    logging.getLogger("botocore").setLevel(logging.CRITICAL)
