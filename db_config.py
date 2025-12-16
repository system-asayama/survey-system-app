#!/usr/bin/env python3
"""
データベース抽象化レイヤー
SQLiteとPostgreSQLの両方に対応
"""
import os
import sqlite3
from urllib.parse import urlparse

# 環境変数からデータベース設定を取得
DATABASE_URL = os.environ.get('DATABASE_URL')

# HerokuのDATABASE_URLは postgres:// で始まるが、psycopg2は postgresql:// を期待する
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# データベースタイプを判定
if DATABASE_URL:
    DB_TYPE = 'postgresql'
    parsed = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:],  # 先頭の / を除去
        'user': parsed.username,
        'password': parsed.password,
    }
else:
    DB_TYPE = 'sqlite'
    DB_PATH = 'database/login_auth.db'

def get_db_connection():
    """データベース接続を取得（SQLiteまたはPostgreSQL）"""
    if DB_TYPE == 'postgresql':
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            # DictCursorを使用してカラム名でアクセス可能にする
            return conn
        except ImportError:
            print("⚠️ psycopg2がインストールされていません。pip install psycopg2-binary を実行してください。")
            raise
        except Exception as e:
            print(f"⚠️ PostgreSQL接続エラー: {e}")
            print("⚠️ SQLiteにフォールバック: database/login_auth.db")
            # フォールバック: SQLiteを使用
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
    else:
        # SQLite
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def get_cursor(conn):
    """カーソルを取得（データベースタイプに応じて適切な設定）"""
    if DB_TYPE == 'postgresql':
        try:
            import psycopg2.extras
            return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        except:
            # psycopg2がない場合（SQLiteフォールバック）
            return conn.cursor()
    else:
        return conn.cursor()

def get_db_type():
    """現在のデータベースタイプを返す"""
    return DB_TYPE

def execute_query(cursor, query, params=None):
    """
    クエリを実行（プレースホルダーを自動変換）
    SQLiteの ? を PostgreSQLの %s に自動変換
    """
    if DB_TYPE == 'postgresql' and '?' in query:
        # ? を %s に置換
        query = query.replace('?', '%s')
    
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

if __name__ == '__main__':
    # テスト
    print(f"データベースタイプ: {DB_TYPE}")
    if DB_TYPE == 'postgresql':
        print(f"接続情報: {DB_CONFIG}")
    else:
        print(f"SQLiteパス: {DB_PATH}")
    
    try:
        conn = get_db_connection()
        print("✓ データベース接続成功")
        conn.close()
    except Exception as e:
        print(f"✗ データベース接続失敗: {e}")
