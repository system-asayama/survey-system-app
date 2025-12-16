#!/usr/bin/env python3
"""
データベーススキーマ完全更新スクリプト
GitHubリポジトリの正しいスキーマに基づいて、不足しているテーブルとカラムを作成します
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
        print("=" * 60)
        print("データベーススキーマ更新を開始します")
        print("=" * 60)
        
        # 1. T_店舗テーブルにopenai_api_keyカラムを追加
        print("\n1. T_店舗テーブルにopenai_api_keyカラムを追加中...")
        try:
            cur.execute('ALTER TABLE T_店舗 ADD COLUMN openai_api_key TEXT DEFAULT NULL')
            conn.commit()
            print("   ✓ openai_api_keyカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ✓ openai_api_keyカラムは既に存在します")
            else:
                raise
        
        # 2. T_テナントテーブルにopenai_api_keyカラムを追加
        print("\n2. T_テナントテーブルにopenai_api_keyカラムを追加中...")
        try:
            cur.execute('ALTER TABLE T_テナント ADD COLUMN openai_api_key TEXT DEFAULT NULL')
            conn.commit()
            print("   ✓ openai_api_keyカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ✓ openai_api_keyカラムは既に存在します")
            else:
                raise
        
        # 2-1. T_テナントテーブルにupdated_atカラムを追加
        print("\n2-1. T_テナントテーブルにupdated_atカラムを追加中...")
        try:
            cur.execute('ALTER TABLE T_テナント ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            conn.commit()
            print("   ✓ updated_atカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ✓ updated_atカラムは既に存在します")
            else:
                raise
        
        # 3. T_管理者テーブルにemailカラムを追加
        print("\n3. T_管理者テーブルにemailカラムを追加中...")
        try:
            cur.execute('ALTER TABLE T_管理者 ADD COLUMN email TEXT')
            conn.commit()
            print("   ✓ emailカラムを追加しました")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ✓ emailカラムは既に存在します")
            else:
                raise
        
        # 4. T_店舗_アンケート設定テーブルを作成
        print("\n4. T_店舗_アンケート設定テーブルを作成中...")
        try:
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
            print("   ✓ T_店舗_アンケート設定テーブルを作成しました")
        except sqlite3.OperationalError as e:
            print(f"   ! テーブル作成エラー: {e}")
        
        # 5. T_店舗_Google設定テーブルを作成
        print("\n5. T_店舗_Google設定テーブルを作成中...")
        try:
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
            print("   ✓ T_店舗_Google設定テーブルを作成しました")
        except sqlite3.OperationalError as e:
            print(f"   ! テーブル作成エラー: {e}")
        
        # 6. T_店舗_スロット設定テーブルを作成
        print("\n6. T_店舗_スロット設定テーブルを作成中...")
        try:
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
            print("   ✓ T_店舗_スロット設定テーブルを作成しました")
        except sqlite3.OperationalError as e:
            print(f"   ! テーブル作成エラー: {e}")
        
        # 7. T_店舗_景品設定テーブルを作成
        print("\n7. T_店舗_景品設定テーブルを作成中...")
        try:
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
            print("   ✓ T_店舗_景品設定テーブルを作成しました")
        except sqlite3.OperationalError as e:
            print(f"   ! テーブル作成エラー: {e}")
        
        # 8. スキーマ確認
        print("\n" + "=" * 60)
        print("8. 更新後のスキーマを確認中...")
        print("=" * 60)
        
        # 全テーブル一覧
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        all_tables = [row[0] for row in cur.fetchall()]
        print(f"\n✓ 全テーブル ({len(all_tables)}個):")
        for table in all_tables:
            print(f"  - {table}")
        
        # 重要なテーブルの詳細確認
        important_tables = [
            'T_テナント',
            'T_店舗',
            'T_管理者',
            'T_店舗_アンケート設定',
            'T_店舗_Google設定',
            'T_店舗_スロット設定',
            'T_店舗_景品設定'
        ]
        
        print("\n重要なテーブルのカラム確認:")
        for table in important_tables:
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cur.fetchone():
                cur.execute(f'PRAGMA table_info("{table}")')
                columns = [row[1] for row in cur.fetchall()]
                print(f"\n  ✓ {table}")
                print(f"    カラム: {', '.join(columns)}")
            else:
                print(f"\n  ✗ {table} が見つかりません")
        
        print("\n" + "=" * 60)
        print("✓ データベーススキーマの更新が完了しました")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_schema()
