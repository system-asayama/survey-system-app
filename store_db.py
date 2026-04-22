#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
店舗ごとの設定を管理するデータベースヘルパー
SQLiteとPostgreSQLの両方に対応
"""
import json
from typing import Optional, Dict, Any, List
from db_config import get_db_connection, get_cursor, execute_query

# ===== 店舗情報取得 =====
def get_store_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """
 slugから店舗情報を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT id, tenant_id, 名称 as name, slug, 有効 as active
        FROM "T_店舗"
        WHERE slug = ? AND 有効 = 1
    """, (slug,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        # SQLite Rowオブジェクトを辞書に変換
        if hasattr(row, 'keys'):
            return {key: row[key] for key in row.keys()}
        else:
            # タプルの場合（フォールバック）
            return {
                'id': row[0],
                'tenant_id': row[1],
                'name': row[2],
                'slug': row[3],
                'active': row[4]
            }
    return None
def get_store_by_id(store_id: int) -> Optional[Dict[str, Any]]:
    """IDから店舗情報を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT id, tenant_id, 名称 as name, slug, 有効 as active
        FROM "T_店舗"
        WHERE id = ? AND 有効 = 1
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        # SQLite Rowオブジェクトを辞書に変換
        if hasattr(row, 'keys'):
            return {key: row[key] for key in row.keys()}
        else:
            # タプルの場合（フォールバック）
            return {
                'id': row[0],
                'tenant_id': row[1],
                'name': row[2],
                'slug': row[3],
                'active': row[4]
            }
    return None

# ===== アンケート設定 =====
def get_survey_config(store_id: int) -> Dict[str, Any]:
    """店舗のアンケート設定を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT config_json
        FROM "T_店舗_アンケート設定"
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row['config_json']:
        return json.loads(row['config_json'])
    
    # デフォルト設定
    return {
        "title": "お店アンケート",
        "questions": []
    }

def save_survey_config(store_id: int, config: Dict[str, Any]) -> None:
    """店舗のアンケート設定を保存"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    # 既存レコードをチェック
    execute_query(cur, 'SELECT id FROM "T_店舗_アンケート設定" WHERE store_id = ?', (store_id,))
    existing = cur.fetchone()
    
    if existing:
        # 更新
        execute_query(cur, """
            UPDATE "T_店舗_アンケート設定"
            SET config_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE store_id = ?
        """, (json.dumps(config, ensure_ascii=False), store_id))
    else:
        # 新規作成
        execute_query(cur, """
            INSERT INTO "T_店舗_アンケート設定" (store_id, title, config_json)
            VALUES (?, ?, ?)
        """, (store_id, config.get('title', 'お店アンケート'), json.dumps(config, ensure_ascii=False)))
    
    conn.commit()
    conn.close()

# ===== AIレビュー設定（業種・指示文） =====
def get_ai_review_settings(store_id: int) -> Dict[str, Any]:
    """店舗のAIレビュー設定（業種・指示文）を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT business_type, ai_instruction
        FROM "T_店舗_アンケート設定"
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        if hasattr(row, 'keys'):
            return {
                'business_type': row['business_type'] or '',
                'ai_instruction': row['ai_instruction'] or ''
            }
        else:
            return {
                'business_type': row[0] or '',
                'ai_instruction': row[1] or ''
            }
    return {'business_type': '', 'ai_instruction': ''}


def save_ai_review_settings(store_id: int, business_type: str, ai_instruction: str) -> None:
    """店舗のAIレビュー設定（業種・指示文）を保存"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, 'SELECT id FROM "T_店舗_アンケート設定" WHERE store_id = ?', (store_id,))
    existing = cur.fetchone()
    if existing:
        execute_query(cur, """
            UPDATE "T_店舗_アンケート設定"
            SET business_type = ?, ai_instruction = ?, updated_at = CURRENT_TIMESTAMP
            WHERE store_id = ?
        """, (business_type, ai_instruction, store_id))
    else:
        execute_query(cur, """
            INSERT INTO "T_店舗_アンケート設定" (store_id, business_type, ai_instruction)
            VALUES (?, ?, ?)
        """, (store_id, business_type, ai_instruction))
    conn.commit()
    conn.close()


# ===== スロット設定 =====
def get_slot_config(store_id: int) -> Dict[str, Any]:
    """店舗のスロット設定を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT config_json
        FROM "T_店舗_スロット設定"
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row['config_json']:
        return json.loads(row['config_json'])
    
    # デフォルト設定
    return {
        "symbols": [
            {"id": "seven", "label": "7", "payout_3": 100, "color": "#ff0000", "prob": 0.0},
            {"id": "bell", "label": "🔔", "payout_3": 50, "color": "#fbbf24", "prob": 0.0},
            {"id": "bar", "label": "BAR", "payout_3": 25, "color": "#ffffff", "prob": 0.0},
            {"id": "grape", "label": "🍇", "payout_3": 20, "color": "#7c3aed", "prob": 0.0},
            {"id": "cherry", "label": "🍒", "payout_3": 12.5, "color": "#ef4444", "prob": 0.0},
            {"id": "lemon", "label": "🍋", "payout_3": 12.5, "color": "#fde047", "prob": 0.0}
        ],
        "reels": 3,
        "base_bet": 1,
        "expected_total_5": 100.0,
        "miss_probability": 0.0
    }

def save_slot_config(store_id: int, config: Dict[str, Any]) -> None:
    """店舗のスロット設定を保存"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        INSERT INTO "T_店舗_スロット設定" (store_id, config_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(store_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = CURRENT_TIMESTAMP
    """, (store_id, json.dumps(config, ensure_ascii=False)))
    conn.commit()
    conn.close()

# ===== 景品設定 =====
def get_prizes_config(store_id: int) -> List[Dict[str, Any]]:
    """店舗の景品設定を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT prizes_json
        FROM "T_店舗_景品設定"
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row['prizes_json']:
        return json.loads(row['prizes_json'])
    
    # デフォルト景品
    return [
        {"min_score": 500, "rank": "🎁 特賞", "name": "特別景品"},
        {"min_score": 250, "max_score": 499, "rank": "🏆 1等", "name": "1等景品"},
        {"min_score": 150, "max_score": 249, "rank": "🥈 2等", "name": "2等景品"},
        {"min_score": 100, "max_score": 149, "rank": "🥉 3等", "name": "3等景品"},
        {"min_score": 0, "max_score": 99, "rank": "🎊 参加賞", "name": "参加賞"}
    ]

def save_prizes_config(store_id: int, prizes: List[Dict[str, Any]]) -> None:
    """店舗の景品設定を保存"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        INSERT INTO "T_店舗_景品設定" (store_id, prizes_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(store_id) DO UPDATE SET
            prizes_json = excluded.prizes_json,
            updated_at = CURRENT_TIMESTAMP
    """, (store_id, json.dumps(prizes, ensure_ascii=False)))
    conn.commit()
    conn.close()

# ===== Google口コミ設定 =====
def get_google_review_url(store_id: int) -> str:
    """店舗のGoogle口コミURLを取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        SELECT review_url
        FROM "T_店舗_Google設定"
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row['review_url']:
        return row['review_url']
    return '#'

def save_google_review_url(store_id: int, review_url: str) -> None:
    """店舗のGoogle口コミURLを保存"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    execute_query(cur, """
        INSERT INTO "T_店舗_Google設定" (store_id, review_url, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(store_id) DO UPDATE SET
            review_url = excluded.review_url,
            updated_at = CURRENT_TIMESTAMP
    """, (store_id, review_url))
    conn.commit()
    conn.close()

# ===== アンケート回答保存 =====
def save_survey_response(store_id: int, response_data: Dict[str, Any]) -> int:
    """アンケート回答を保存（動的な質問に対応）"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    # 動的な質問に対応：response_jsonのみを保存
    execute_query(cur, """
        INSERT INTO "T_アンケート回答" (
            store_id, rating, visit_purpose, atmosphere, 
            recommend, comment, generated_review, response_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        store_id,
        response_data.get('rating', 3),  # デフォルト値を設定
        response_data.get('visit_purpose', 'その他'),
        json.dumps(response_data.get('atmosphere', []), ensure_ascii=False),
        response_data.get('recommend', '普通'),
        response_data.get('comment', ''),
        response_data.get('generated_review', ''),
        json.dumps(response_data, ensure_ascii=False)
    ))
    
    response_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    return response_id

# ===== 統計データ取得 =====
def get_survey_stats(store_id: int) -> Dict[str, Any]:
    """店舗のアンケート統計を取得"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    # 総回答数
    execute_query(cur, """
        SELECT COUNT(*) as total
        FROM "T_アンケート回答"
        WHERE store_id = ?
    """, (store_id,))
    total = cur.fetchone()['total']
    
    # 評価分布
    execute_query(cur, """
        SELECT rating, COUNT(*) as count
        FROM "T_アンケート回答"
        WHERE store_id = ?
        GROUP BY rating
        ORDER BY rating DESC
    """, (store_id,))
    rating_dist = {row['rating']: row['count'] for row in cur.fetchall()}
    
    # 平均評価
    execute_query(cur, """
        SELECT AVG(rating) as avg_rating
        FROM "T_アンケート回答"
        WHERE store_id = ?
    """, (store_id,))
    avg_rating = cur.fetchone()['avg_rating'] or 0.0
    
    conn.close()
    
    return {
        'total': total,
        'rating_distribution': rating_dist,
        'average_rating': round(avg_rating, 2)
    }
