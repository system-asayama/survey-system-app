#!/usr/bin/env python3
import json
import sqlite3
import sys

# survey_config.jsonを読み込み
with open('/home/ubuntu/survey-system-app/data/survey_config.json', 'r', encoding='utf-8') as f:
    survey_config = json.load(f)

# データベースに接続
conn = sqlite3.connect('/home/ubuntu/survey-system-app/database/login_auth.db')
cursor = conn.cursor()

# 店舗ID=1に対してアンケート設定を登録
store_id = 1
config_json = json.dumps(survey_config, ensure_ascii=False)

cursor.execute("""
    INSERT INTO T_店舗_アンケート設定 (store_id, config_json, updated_at)
    VALUES (?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(store_id) DO UPDATE SET
        config_json = excluded.config_json,
        updated_at = CURRENT_TIMESTAMP
""", (store_id, config_json))

conn.commit()
conn.close()

print(f"✅ 店舗ID {store_id} にアンケート設定を登録しました")
print(f"質問数: {len(survey_config['questions'])}問")
