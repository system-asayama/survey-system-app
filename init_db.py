#!/usr/bin/env python3
"""
データベース自動初期化モジュール
アプリケーション起動時に必要なテーブルとカラムを自動作成します
"""
import sqlite3
import os

DB_PATH = 'database/login_auth.db'

def init_database():
    """データベースの初期化（テーブルとカラムの作成）"""
    
    # データベースディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        print("=" * 60)
        print("データベース初期化を開始します")
        print("=" * 60)
        
        # 1. T_店舗テーブルにopenai_api_keyカラムを追加
        try:
            cur.execute('ALTER TABLE T_店舗 ADD COLUMN openai_api_key TEXT DEFAULT NULL')
            conn.commit()
            print("✓ T_店舗.openai_api_keyカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e) or "no such table" in str(e):
                pass  # 既に存在するか、テーブルが存在しない
            else:
                raise
        
        # 2. T_テナントテーブルにopenai_api_keyカラムを追加
        try:
            cur.execute('ALTER TABLE T_テナント ADD COLUMN openai_api_key TEXT DEFAULT NULL')
            conn.commit()
            print("✓ T_テナント.openai_api_keyカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e) or "no such table" in str(e):
                pass
            else:
                raise
        
        # 2-1. T_テナントテーブルにupdated_atカラムを追加
        try:
            cur.execute('ALTER TABLE T_テナント ADD COLUMN updated_at TIMESTAMP DEFAULT NULL')
            conn.commit()
            print("✓ T_テナント.updated_atカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e) or "no such table" in str(e):
                pass
            else:
                raise
        
        # 3. T_管理者テーブルにemailカラムを追加
        try:
            cur.execute('ALTER TABLE T_管理者 ADD COLUMN email TEXT')
            conn.commit()
            print("✓ T_管理者.emailカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e) or "no such table" in str(e):
                pass
            else:
                raise
        
        # 4. T_店舗_アンケート設定テーブルを作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "T_店舗_アンケート設定" (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id        INTEGER NOT NULL UNIQUE,
                title           TEXT DEFAULT 'お店アンケート',
                config_json     TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                openai_api_key  TEXT DEFAULT NULL,
                FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("✓ T_店舗_アンケート設定テーブルを作成しました")
        
        # 5. T_店舗_Google設定テーブルを作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "T_店舗_Google設定" (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id        INTEGER NOT NULL UNIQUE,
                review_url      TEXT,
                place_id        TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("✓ T_店舗_Google設定テーブルを作成しました")
        
        # 6. T_店舗_スロット設定テーブルを作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "T_店舗_スロット設定" (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id        INTEGER NOT NULL UNIQUE,
                config_json     TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                openai_api_key  TEXT DEFAULT NULL,
                FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("✓ T_店舗_スロット設定テーブルを作成しました")
        
        # 7. T_店舗_景品設定テーブルを作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "T_店舗_景品設定" (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id        INTEGER NOT NULL UNIQUE,
                prizes_json     TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("✓ T_店舗_景品設定テーブルを作成しました")
        
        # 8. T_アンケート回答テーブルを作成
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "T_アンケート回答" (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id        INTEGER NOT NULL,
                rating          INTEGER NOT NULL,
                visit_purpose   TEXT,
                atmosphere      TEXT,
                recommend       TEXT,
                comment         TEXT,
                generated_review TEXT,
                response_json   TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("✓ T_アンケート回答テーブルを作成しました")
        
        print("=" * 60)
        print("✓ データベース初期化が完了しました")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
