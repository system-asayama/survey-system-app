#!/usr/bin/env python3
"""
review_prompt_modeを'all'に変更するスクリプト
"""
import os
import sys

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.db import get_db_connection, _sql

def update_review_prompt_mode_to_all():
    """全店舗のreview_prompt_modeを'all'に更新"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 現在の設定を確認
        cur.execute(_sql(conn, '''
            SELECT id, store_id, review_prompt_mode 
            FROM "T_店舗_口コミ投稿促進設定"
        '''))
        
        settings = cur.fetchall()
        print("=" * 60)
        print("現在の設定:")
        print("=" * 60)
        for setting in settings:
            print(f"ID: {setting[0]}, Store ID: {setting[1]}, Mode: {setting[2]}")
        
        # 全てを'all'に更新
        cur.execute(_sql(conn, '''
            UPDATE "T_店舗_口コミ投稿促進設定"
            SET review_prompt_mode = %s, updated_at = CURRENT_TIMESTAMP
        '''), ('all',))
        
        conn.commit()
        
        # 更新後の設定を確認
        cur.execute(_sql(conn, '''
            SELECT id, store_id, review_prompt_mode 
            FROM "T_店舗_口コミ投稿促進設定"
        '''))
        
        settings = cur.fetchall()
        print("\n" + "=" * 60)
        print("更新後の設定:")
        print("=" * 60)
        for setting in settings:
            print(f"ID: {setting[0]}, Store ID: {setting[1]}, Mode: {setting[2]}")
        
        print("\n✅ review_prompt_modeを'all'に更新しました")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_review_prompt_mode_to_all()
