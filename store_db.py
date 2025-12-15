#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
店舗ごとの設定を管理するデータベースヘルパー
"""
import sqlite3
import json
from typing import Optional, Dict, Any, List

DB_PATH = "database/login_auth.db"

def get_db_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ===== 店舗情報取得 =====
def get_store_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """slugから店舗情報を取得"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tenant_id, 名称 as name, slug, 有効 as active
        FROM T_店舗
        WHERE slug = ? AND 有効 = 1
    """, (slug,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def get_store_by_id(store_id: int) -> Optional[Dict[str, Any]]:
    """IDから店舗情報を取得"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tenant_id, 名称 as name, slug, 有効 as active
        FROM T_店舗
        WHERE id = ? AND 有効 = 1
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

# ===== アンケート設定 =====
def get_survey_config(store_id: int) -> Dict[str, Any]:
    """店舗のアンケート設定を取得"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT config_json
        FROM T_店舗_アンケート設定
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
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO T_店舗_アンケート設定 (store_id, config_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(store_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = CURRENT_TIMESTAMP
    """, (store_id, json.dumps(config, ensure_ascii=False)))
    conn.commit()
    conn.close()

# ===== スロット設定 =====
def get_slot_config(store_id: int) -> Dict[str, Any]:
    """店舗のスロット設定を取得"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT config_json
        FROM T_店舗_スロット設定
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
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO T_店舗_スロット設定 (store_id, config_json, updated_at)
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
    cur = conn.cursor()
    cur.execute("""
        SELECT prizes_json
        FROM T_店舗_景品設定
        WHERE store_id = ?
    """, (store_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row['prizes_json']:
        return json.loads(row['prizes_json'])
    
    # デフォルト景品
    return [
        {"label": "🎁 特賞", "min": 500, "max": None},
        {"label": "🏆 1等", "min": 250, "max": 499},
        {"label": "🥈 2等", "min": 150, "max": 249},
        {"label": "🥉 3等", "min": 100, "max": 149},
        {"label": "🎊 参加賞", "min": 0, "max": 99}
    ]

def save_prizes_config(store_id: int, prizes: List[Dict[str, Any]]) -> None:
    """店舗の景品設定を保存"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO T_店舗_景品設定 (store_id, prizes_json, updated_at)
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
    cur = conn.cursor()
    cur.execute("""
        SELECT review_url
        FROM T_店舗_Google設定
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
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO T_店舗_Google設定 (store_id, review_url, updated_at)
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
    cur = conn.cursor()
    
    # 動的な質問に対応：response_jsonのみを保存
    cur.execute("""
        INSERT INTO T_アンケート回答 (
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
    cur = conn.cursor()
    
    # 総回答数
    cur.execute("""
        SELECT COUNT(*) as total
        FROM T_アンケート回答
        WHERE store_id = ?
    """, (store_id,))
    total = cur.fetchone()['total']
    
    # 評価分布
    cur.execute("""
        SELECT rating, COUNT(*) as count
        FROM T_アンケート回答
        WHERE store_id = ?
        GROUP BY rating
        ORDER BY rating DESC
    """, (store_id,))
    rating_dist = {row['rating']: row['count'] for row in cur.fetchall()}
    
    # 平均評価
    cur.execute("""
        SELECT AVG(rating) as avg_rating
        FROM T_アンケート回答
        WHERE store_id = ?
    """, (store_id,))
    avg_rating = cur.fetchone()['avg_rating'] or 0.0
    
    conn.close()
    
    return {
        'total': total,
        'rating_distribution': rating_dist,
        'average_rating': round(avg_rating, 2)
    }
