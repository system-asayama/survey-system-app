from app import create_app

# Gunicorn から参照されるアプリケーション本体
app = create_app()

# データベース初期化（テーブルとカラムの自動作成）
try:
    from init_db import init_database
    init_database()
    print("✅ データベース初期化完了")
except Exception as e:
    print(f"⚠️ データベース初期化エラー: {e}")
