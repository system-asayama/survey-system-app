#!/usr/bin/env python3
"""
データベーススキーマ更新スクリプト
T_店舗テーブルにopenai_api_keyカラムを追加
T_店舗_アンケート設定テーブルを作成
"""
import sqlite3
import os

DB_PATH = 'database/login_auth.db'

def update_schema():
    if not os.path.exists(DB_PATH):
        print(f"エラー: {DB_PATH} が見つかりません")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # 1. T_店舗テーブルにopenai_api_keyカラムを追加
        print("1. T_店舗テーブルにopenai_api_keyカラムを追加中...")
        try:
            cur.execute('ALTER TABLE T_店舗 ADD COLUMN openai_api_key TEXT DEFAULT NULL')
            conn.commit()
            print("   ✓ openai_api_keyカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ✓ openai_api_keyカラムは既に存在します")
            else:
                raise
        
        # 2. T_店舗_アンケート設定テーブルを作成
        print("\n2. T_店舗_アンケート設定テーブルを作成中...")
        try:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "T_店舗_アンケート設定" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id INTEGER NOT NULL,
                    openai_api_key TEXT,
                    google_review_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()
            print("   ✓ T_店舗_アンケート設定テーブルを作成しました")
        except sqlite3.OperationalError as e:
            print(f"   ! エラー: {e}")
        
        # 3. スキーマ確認
        print("\n3. 更新後のスキーマを確認中...")
        cur.execute('PRAGMA table_info(T_店舗)')
        store_columns = [row[1] for row in cur.fetchall()]
        print(f"   T_店舗のカラム: {', '.join(store_columns)}")
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='T_店舗_アンケート設定'")
        if cur.fetchone():
            print("   ✓ T_店舗_アンケート設定テーブルが存在します")
        else:
            print("   ✗ T_店舗_アンケート設定テーブルが見つかりません")
        
        print("\n✓ データベーススキーマの更新が完了しました")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_schema()
