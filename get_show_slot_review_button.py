#!/usr/bin/env python3
"""
スロット結果ページでGoogle口コミボタンを表示するかどうかの設定を取得する関数
"""
from db_config import get_db_connection, get_cursor, execute_query

def get_show_slot_review_button(store_id: int) -> bool:
    """店舗のスロット結果ページでGoogle口コミボタンを表示するかどうかを取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT show_slot_review_button
        FROM "T_店舗_Google設定"
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row['show_slot_review_button'] is not None:
        return bool(row['show_slot_review_button'])
    return True  # デフォルトは表示する
