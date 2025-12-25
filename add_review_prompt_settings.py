#!/usr/bin/env python3
"""
口コミ投稿促進設定機能の追加
T_店舗_Google設定テーブルに新しいカラムを追加します
"""
from db_config import get_db_connection, get_cursor, get_db_type

def add_review_prompt_settings():
    """口コミ投稿促進設定のカラムを追加"""
    
    conn = get_db_connection()
    cur = get_cursor(conn)
    db_type = get_db_type()
    
    try:
        print("=" * 60)
        print("口コミ投稿促進設定機能を追加します")
        print("=" * 60)
        
        # 1. review_prompt_mode カラムを追加
        # 'all' = 全ての評価に投稿を促す（デフォルト）
        # 'high_rating_only' = 星4以上のみ投稿を促す
        try:
            if db_type == 'postgresql':
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'T_店舗_Google設定' AND column_name = 'review_prompt_mode'
                """)
                if not cur.fetchone():
                    cur.execute("""
                        ALTER TABLE "T_店舗_Google設定" 
                        ADD COLUMN review_prompt_mode TEXT DEFAULT 'all'
                    """)
                    conn.commit()
                    print("✓ review_prompt_mode カラムを追加しました")
                else:
                    print("- review_prompt_mode カラムは既に存在します")
            else:
                cur.execute('PRAGMA table_info("T_店舗_Google設定")')
                columns = [row[1] for row in cur.fetchall()]
                if 'review_prompt_mode' not in columns:
                    cur.execute("""
                        ALTER TABLE "T_店舗_Google設定" 
                        ADD COLUMN review_prompt_mode TEXT DEFAULT 'all'
                    """)
                    conn.commit()
                    print("✓ review_prompt_mode カラムを追加しました")
                else:
                    print("- review_prompt_mode カラムは既に存在します")
        except Exception as e:
            print(f"! review_prompt_mode カラム追加エラー: {e}")
        
        # 2. T_店舗_Google設定_ログテーブルを作成
        # リスク設定の変更履歴を記録
        try:
            if db_type == 'postgresql':
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS "T_店舗_Google設定_ログ" (
                        id SERIAL PRIMARY KEY,
                        store_id INTEGER NOT NULL,
                        admin_id INTEGER,
                        action TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        warnings_shown BOOLEAN DEFAULT FALSE,
                        checkboxes_confirmed BOOLEAN DEFAULT FALSE,
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS "T_店舗_Google設定_ログ" (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        store_id INTEGER NOT NULL,
                        admin_id INTEGER,
                        action TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        warnings_shown INTEGER DEFAULT 0,
                        checkboxes_confirmed INTEGER DEFAULT 0,
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (store_id) REFERENCES "T_店舗"(id) ON DELETE CASCADE
                    )
                """)
            conn.commit()
            print("✓ T_店舗_Google設定_ログテーブルを作成しました")
        except Exception as e:
            print(f"! T_店舗_Google設定_ログテーブル作成エラー: {e}")
        
        # 3. T_店舗_Google設定_リマインドテーブルを作成
        # 定期リマインドの送信履歴を記録
        try:
            if db_type == 'postgresql':
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS "T_店舗_Google設定_リマインド" (
                        id SERIAL PRIMARY KEY,
                        store_id INTEGER NOT NULL,
                        reminded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        review_prompt_mode TEXT,
                        action_taken TEXT,
                        FOREIGN KEY (store_id) REFERENCES "T_店舗"(id) ON DELETE CASCADE
                    )
                """)
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS "T_店舗_Google設定_リマインド" (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        store_id INTEGER NOT NULL,
                        reminded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        review_prompt_mode TEXT,
                        action_taken TEXT,
                        FOREIGN KEY (store_id) REFERENCES "T_店舗"(id) ON DELETE CASCADE
                    )
                """)
            conn.commit()
            print("✓ T_店舗_Google設定_リマインドテーブルを作成しました")
        except Exception as e:
            print(f"! T_店舗_Google設定_リマインドテーブル作成エラー: {e}")
        
        print("=" * 60)
        print("口コミ投稿促進設定機能の追加が完了しました")
        print("=" * 60)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_review_prompt_settings()
