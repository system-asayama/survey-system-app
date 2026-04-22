#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T_店舗_アンケート設定テーブルに業種・AI指示文カラムを追加するマイグレーション
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_config import get_db_connection, get_cursor
from app.utils.db import _sql

def migrate():
    conn = get_db_connection()
    cur = get_cursor(conn)

    # SQLite か PostgreSQL かを判定
    is_sqlite = 'sqlite' in type(conn).__module__.lower()

    try:
        if is_sqlite:
            # SQLite: PRAGMA で既存カラムを確認
            cur.execute("PRAGMA table_info('T_店舗_アンケート設定')")
            columns = [row['name'] if hasattr(row, 'keys') else row[1] for row in cur.fetchall()]

            if 'business_type' not in columns:
                cur.execute("ALTER TABLE \"T_店舗_アンケート設定\" ADD COLUMN business_type TEXT DEFAULT ''")
                print("✓ business_type カラムを追加しました")
            else:
                print("- business_type カラムは既に存在します")

            if 'ai_instruction' not in columns:
                cur.execute("ALTER TABLE \"T_店舗_アンケート設定\" ADD COLUMN ai_instruction TEXT DEFAULT ''")
                print("✓ ai_instruction カラムを追加しました")
            else:
                print("- ai_instruction カラムは既に存在します")

        else:
            # PostgreSQL: information_schema で確認
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'T_店舗_アンケート設定'
            """)
            columns = [row[0] for row in cur.fetchall()]

            if 'business_type' not in columns:
                cur.execute("ALTER TABLE \"T_店舗_アンケート設定\" ADD COLUMN business_type TEXT DEFAULT ''")
                print("✓ business_type カラムを追加しました")
            else:
                print("- business_type カラムは既に存在します")

            if 'ai_instruction' not in columns:
                cur.execute("ALTER TABLE \"T_店舗_アンケート設定\" ADD COLUMN ai_instruction TEXT DEFAULT ''")
                print("✓ ai_instruction カラムを追加しました")
            else:
                print("- ai_instruction カラムは既に存在します")

        conn.commit()
        print("✓ マイグレーション完了")

    except Exception as e:
        conn.rollback()
        print(f"! マイグレーションエラー: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
