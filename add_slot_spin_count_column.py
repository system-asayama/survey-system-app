#!/usr/bin/env python3
"""
T_店舗_Google設定テーブルにslot_spin_countカラムを追加するマイグレーションスクリプト
"""
import psycopg2
from db_config import get_db_connection_string, get_db_type

def add_slot_spin_count_column():
    """slot_spin_countカラムを追加"""
    db_type = get_db_type()
    conn_str = get_db_connection_string()
    
    print(f"データベースタイプ: {db_type}")
    print(f"接続文字列: {conn_str[:50]}...")
    
    if db_type == 'postgresql':
        conn = psycopg2.connect(conn_str)
    else:
        import sqlite3
        conn = sqlite3.connect(conn_str)
    
    cur = conn.cursor()
    
    try:
        # カラムが存在するか確認
        if db_type == 'postgresql':
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'T_店舗_Google設定' AND column_name = 'slot_spin_count'
            """)
        else:
            cur.execute("PRAGMA table_info(\"T_店舗_Google設定\")")
            columns = [row[1] for row in cur.fetchall()]
            if 'slot_spin_count' in columns:
                print("✓ slot_spin_countカラムは既に存在します")
                conn.close()
                return
        
        if db_type == 'postgresql' and not cur.fetchone():
            print("slot_spin_countカラムを追加中...")
            cur.execute('''
                ALTER TABLE "T_店舗_Google設定"
                ADD COLUMN slot_spin_count INTEGER DEFAULT 1
            ''')
            conn.commit()
            print("✓ slot_spin_countカラムを追加しました")
        elif db_type == 'sqlite':
            print("slot_spin_countカラムを追加中...")
            cur.execute('''
                ALTER TABLE "T_店舗_Google設定"
                ADD COLUMN slot_spin_count INTEGER DEFAULT 1
            ''')
            conn.commit()
            print("✓ slot_spin_countカラムを追加しました")
        else:
            print("✓ slot_spin_countカラムは既に存在します")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_slot_spin_count_column()
