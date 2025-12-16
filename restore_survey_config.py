#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アンケート設定を11問+2問（自由記述）に復元するスクリプト
"""
import json
import sys
sys.path.insert(0, '/tmp/survey-repo')
from db_config import get_db_connection
from app.utils.db import _sql

# 11問+2問のデフォルト設定
default_survey_config = {
    "title": "お客様満足度アンケート",
    "description": "ご来店ありがとうございます。より良いサービス提供のため、アンケートにご協力ください。",
    "questions": [
        {
            "id": 1,
            "text": "本日のご利用について、総合的にどの程度満足されましたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に満足", "満足", "普通", "やや不満", "非常に不満"]
        },
        {
            "id": 2,
            "text": "料理の味はいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に良い", "良い", "普通", "やや悪い", "非常に悪い"]
        },
        {
            "id": 3,
            "text": "料理の提供スピードはいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に早い", "早い", "普通", "やや遅い", "非常に遅い"]
        },
        {
            "id": 4,
            "text": "メニューの種類・選びやすさはいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に良い", "良い", "普通", "やや悪い", "非常に悪い"]
        },
        {
            "id": 5,
            "text": "スタッフの接客態度はいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に良い", "良い", "普通", "やや悪い", "非常に悪い"]
        },
        {
            "id": 6,
            "text": "注文や説明の分かりやすさはいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に分かりやすい", "分かりやすい", "普通", "やや分かりにくい", "非常に分かりにくい"]
        },
        {
            "id": 7,
            "text": "店内の清潔感はいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に良い", "良い", "普通", "やや悪い", "非常に悪い"]
        },
        {
            "id": 8,
            "text": "店内の雰囲気（照明・音楽・居心地）はいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常に良い", "良い", "普通", "やや悪い", "非常に悪い"]
        },
        {
            "id": 9,
            "text": "価格に対する満足度はいかがでしたか？",
            "type": "radio",
            "required": True,
            "options": ["非常にお得", "ややお得", "適正", "やや高い", "非常に高い（不満）"]
        },
        {
            "id": 10,
            "text": "今後も当店を利用したいと思いますか？",
            "type": "radio",
            "required": True,
            "options": ["強く思う", "思う", "どちらとも言えない", "あまり思わない", "全く思わない"]
        },
        {
            "id": 11,
            "text": "ご家族やご友人に当店をおすすめしたいと思いますか？",
            "type": "radio",
            "required": True,
            "options": ["強く思う", "思う", "どちらとも言えない", "あまり思わない", "全く思わない"]
        },
        {
            "id": 12,
            "text": "１番おいしかったメニューを教えて下さい。",
            "type": "text",
            "required": False
        },
        {
            "id": 13,
            "text": "ご自由にご感想をお書き下さい。",
            "type": "text",
            "required": False
        }
    ]
}

def restore_survey_config():
    """アンケート設定を復元"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 全店舗を取得
    cur.execute(_sql(conn, 'SELECT id, 名称 FROM "T_店舗" WHERE 有効 = 1'), ())
    stores = cur.fetchall()
    
    if not stores:
        print("❌ 店舗が見つかりません")
        conn.close()
        return
    
    config_json = json.dumps(default_survey_config, ensure_ascii=False)
    
    for store in stores:
        store_id = store[0]
        store_name = store[1]
        
        # 既存の設定を確認
        cur.execute(_sql(conn, 'SELECT id FROM "T_店舗_アンケート設定" WHERE store_id = %s'), (store_id,))
        existing = cur.fetchone()
        
        if existing:
            # 更新
            cur.execute(_sql(conn, '''
                UPDATE "T_店舗_アンケート設定"
                SET config_json = %s, updated_at = CURRENT_TIMESTAMP
                WHERE store_id = %s
            '''), (config_json, store_id))
            print(f"✓ 店舗「{store_name}」のアンケート設定を更新しました（11問+2問）")
        else:
            # 新規作成
            cur.execute(_sql(conn, '''
                INSERT INTO "T_店舗_アンケート設定" (store_id, config_json, created_at, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            '''), (store_id, config_json))
            print(f"✓ 店舗「{store_name}」のアンケート設定を作成しました（11問+2問）")
    
    conn.commit()
    conn.close()
    print("\n✅ アンケート設定の復元が完了しました")

if __name__ == '__main__':
    print("=" * 60)
    print("アンケート設定を11問+2問に復元します")
    print("=" * 60)
    restore_survey_config()
