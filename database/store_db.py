# -*- coding: utf-8 -*-
"""
店舗関連のデータベース操作
"""
import sqlite3
import json
from typing import Optional, Dict, Any

DATABASE_PATH = "/home/ubuntu/survey-system-app/database/login_auth.db"


def get_db_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_survey_config(store_id: int) -> Optional[Dict[str, Any]]:
    """
    店舗IDからアンケート設定を取得
    
    Args:
        store_id: 店舗ID
        
    Returns:
        アンケート設定の辞書、存在しない場合はNone
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'SELECT config_json FROM "T_店舗_アンケート設定" WHERE store_id = ?',
            (store_id,)
        )
        row = cursor.fetchone()
        
        if row and row['config_json']:
            return json.loads(row['config_json'])
        return None
    finally:
        conn.close()


def get_store_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """
    店舗slugから店舗情報を取得
    
    Args:
        slug: 店舗slug
        
    Returns:
        店舗情報の辞書、存在しない場合はNone
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'SELECT id, 名称, slug, tenant_id FROM "T_店舗" WHERE slug = ?',
            (slug,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'name': row['名称'],
                'slug': row['slug'],
                'tenant_id': row['tenant_id']
            }
        return None
    finally:
        conn.close()


def save_survey_response(store_id: int, response_data: Dict[str, Any]) -> int:
    """
    アンケート回答を保存
    
    Args:
        store_id: 店舗ID
        response_data: 回答データ
        
    Returns:
        保存された回答のID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            '''INSERT INTO "T_アンケート回答" 
               (store_id, response_json, created_at)
               VALUES (?, ?, datetime('now'))''',
            (store_id, json.dumps(response_data, ensure_ascii=False))
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
