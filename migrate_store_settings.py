#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
店舗ごとの設定テーブルを作成するマイグレーションスクリプト
"""
import sqlite3
import json
import os

DB_PATH = "database/login_auth.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("📋 店舗ごとの設定テーブルを作成します...")
    
    # 1. アンケート設定テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS T_店舗_アンケート設定 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id        INTEGER NOT NULL UNIQUE,
            title           TEXT DEFAULT 'お店アンケート',
            config_json     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
        )
    """)
    print("✅ T_店舗_アンケート設定 テーブル作成完了")
    
    # 2. スロット設定テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS T_店舗_スロット設定 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id        INTEGER NOT NULL UNIQUE,
            config_json     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
        )
    """)
    print("✅ T_店舗_スロット設定 テーブル作成完了")
    
    # 3. 景品設定テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS T_店舗_景品設定 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id        INTEGER NOT NULL UNIQUE,
            prizes_json     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
        )
    """)
    print("✅ T_店舗_景品設定 テーブル作成完了")
    
    # 4. アンケート回答履歴テーブル（店舗IDカラム追加）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS T_アンケート回答 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id        INTEGER NOT NULL,
            rating          INTEGER NOT NULL,
            visit_purpose   TEXT,
            atmosphere      TEXT,
            recommend       TEXT,
            comment         TEXT,
            generated_review TEXT,
            response_json   TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
        )
    """)
    print("✅ T_アンケート回答 テーブル作成完了")
    
    # 5. Google口コミURL設定テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS T_店舗_Google設定 (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id        INTEGER NOT NULL UNIQUE,
            review_url      TEXT,
            place_id        TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
        )
    """)
    print("✅ T_店舗_Google設定 テーブル作成完了")
    
    # 6. 既存の店舗にデフォルト設定を挿入
    cur.execute("SELECT id FROM T_店舗")
    stores = cur.fetchall()
    
    for (store_id,) in stores:
        # デフォルトアンケート設定
        default_survey_config = {
            "title": "お店アンケート",
            "questions": [
                {
                    "id": "rating",
                    "type": "rating",
                    "label": "総合評価",
                    "required": True,
                    "max": 5
                },
                {
                    "id": "visit_purpose",
                    "type": "select",
                    "label": "ご来店の目的は？",
                    "required": True,
                    "options": ["食事", "飲み会", "デート", "家族との食事", "その他"]
                },
                {
                    "id": "atmosphere",
                    "type": "checkbox",
                    "label": "お店の雰囲気はいかがでしたか？",
                    "required": True,
                    "options": ["落ち着いた", "活気がある", "清潔", "おしゃれ", "アットホーム"]
                },
                {
                    "id": "recommend",
                    "type": "select",
                    "label": "友人におすすめしたいですか？",
                    "required": True,
                    "options": ["ぜひおすすめしたい", "おすすめしたい", "どちらともいえない", "あまりおすすめしない", "おすすめしない"]
                },
                {
                    "id": "comment",
                    "type": "textarea",
                    "label": "ご意見・ご感想",
                    "required": False,
                    "placeholder": "お気づきの点があればお聞かせください"
                }
            ]
        }
        
        cur.execute("""
            INSERT OR IGNORE INTO T_店舗_アンケート設定 (store_id, config_json)
            VALUES (?, ?)
        """, (store_id, json.dumps(default_survey_config, ensure_ascii=False)))
        
        # デフォルトスロット設定
        default_slot_config = {
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
        
        cur.execute("""
            INSERT OR IGNORE INTO T_店舗_スロット設定 (store_id, config_json)
            VALUES (?, ?)
        """, (store_id, json.dumps(default_slot_config, ensure_ascii=False)))
        
        # デフォルト景品設定
        default_prizes = [
            {"label": "🎁 特賞", "min": 500, "max": None},
            {"label": "🏆 1等", "min": 250, "max": 499},
            {"label": "🥈 2等", "min": 150, "max": 249},
            {"label": "🥉 3等", "min": 100, "max": 149},
            {"label": "🎊 参加賞", "min": 0, "max": 99}
        ]
        
        cur.execute("""
            INSERT OR IGNORE INTO T_店舗_景品設定 (store_id, prizes_json)
            VALUES (?, ?)
        """, (store_id, json.dumps(default_prizes, ensure_ascii=False)))
        
        print(f"✅ 店舗ID {store_id} にデフォルト設定を挿入")
    
    conn.commit()
    conn.close()
    
    print("\n✅ マイグレーション完了!")

if __name__ == "__main__":
    migrate()
