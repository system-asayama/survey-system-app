#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口コミ投稿促進設定テーブルを作成するマイグレーションスクリプト
"""
import os
import sys

# データベース接続を取得
from db_config import get_db_connection, get_cursor
from app.utils.db import _sql

def migrate():
    """口コミ投稿促進設定テーブルを作成"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    print("📋 口コミ投稿促進設定テーブルを作成します...")
    
    try:
        # 1. T_店舗_口コミ投稿促進設定テーブル
        cur.execute(_sql(conn, """
            CREATE TABLE IF NOT EXISTS "T_店舗_口コミ投稿促進設定" (
                id                  SERIAL PRIMARY KEY,
                store_id            INTEGER NOT NULL UNIQUE,
                review_prompt_mode  TEXT DEFAULT 'all',
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES "T_店舗"(id) ON DELETE CASCADE
            )
        """))
        print("✅ T_店舗_口コミ投稿促進設定 テーブル作成完了")
        
        # 2. T_口コミ投稿促進設定ログテーブル
        cur.execute(_sql(conn, """
            CREATE TABLE IF NOT EXISTS "T_口コミ投稿促進設定ログ" (
                id                      SERIAL PRIMARY KEY,
                store_id                INTEGER NOT NULL,
                user_id                 INTEGER,
                review_prompt_mode      TEXT NOT NULL,
                warnings_shown          BOOLEAN DEFAULT FALSE,
                checkboxes_confirmed    BOOLEAN DEFAULT FALSE,
                created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES "T_店舗"(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES "T_管理者"(id) ON DELETE SET NULL
            )
        """))
        print("✅ T_口コミ投稿促進設定ログ テーブル作成完了")
        
        # 3. 既存の店舗にデフォルト設定を挿入
        cur.execute(_sql(conn, 'SELECT id FROM "T_店舗"'))
        stores = cur.fetchall()
        
        for (store_id,) in stores:
            # デフォルト設定を挿入（既に存在する場合はスキップ）
            cur.execute(_sql(conn, '''
                SELECT id FROM "T_店舗_口コミ投稿促進設定" WHERE store_id = %s
            '''), (store_id,))
            
            if not cur.fetchone():
                cur.execute(_sql(conn, '''
                    INSERT INTO "T_店舗_口コミ投稿促進設定" (store_id, review_prompt_mode)
                    VALUES (%s, 'all')
                '''), (store_id,))
                print(f"  ✅ 店舗ID {store_id} にデフォルト設定を追加")
        
        conn.commit()
        print("\n✅ マイグレーション完了")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ マイグレーションエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
