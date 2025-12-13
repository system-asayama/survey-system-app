"""
既存データの店舗紐付けマイグレーション
"""

import sqlite3
import json

def migrate_existing_data():
    """既存データを店舗に紐付ける"""
    conn = sqlite3.connect('database/login_auth.db')
    cur = conn.cursor()
    
    print("=== 既存データのマイグレーション開始 ===\n")
    
    # 1. デフォルト店舗を取得（最初の店舗を使用）
    cur.execute('SELECT id, 名称 FROM "T_店舗" ORDER BY id LIMIT 1')
    default_store = cur.fetchone()
    
    if not default_store:
        print("⚠️ 店舗が見つかりません。マイグレーションをスキップします。")
        conn.close()
        return
    
    default_store_id = default_store[0]
    default_store_name = default_store[1]
    print(f"デフォルト店舗: ID={default_store_id}, 名称={default_store_name}\n")
    
    # 2. アンケート回答に店舗IDを設定（NULL の場合のみ）
    cur.execute('''
        UPDATE "T_アンケート回答" 
        SET 店舗ID = ? 
        WHERE 店舗ID IS NULL
    ''', (default_store_id,))
    
    updated_surveys = cur.rowcount
    print(f"✅ アンケート回答: {updated_surveys}件を店舗ID={default_store_id}に紐付けました")
    
    # 3. デフォルトのスロット設定を作成（存在しない場合）
    cur.execute('SELECT COUNT(*) FROM "T_店舗スロット設定" WHERE 店舗ID = ?', (default_store_id,))
    if cur.fetchone()[0] == 0:
        default_slot_config = {
            "symbols": [
                {"id": "seven", "label": "7", "prob": 0.05, "payout_3": 100},
                {"id": "bell", "label": "🔔", "prob": 0.1, "payout_3": 50},
                {"id": "bar", "label": "BAR", "prob": 0.15, "payout_3": 25},
                {"id": "grape", "label": "🍇", "prob": 0.2, "payout_3": 20},
                {"id": "cherry", "label": "🍒", "prob": 0.25, "payout_3": 12.5},
                {"id": "lemon", "label": "🍋", "prob": 0.25, "payout_3": 12.5}
            ],
            "reels": 3,
            "expected_value": 30
        }
        
        cur.execute('''
            INSERT INTO "T_店舗スロット設定" (店舗ID, 設定JSON)
            VALUES (?, ?)
        ''', (default_store_id, json.dumps(default_slot_config, ensure_ascii=False)))
        
        print(f"✅ スロット設定: デフォルト設定を店舗ID={default_store_id}に作成しました")
    else:
        print(f"ℹ️ スロット設定: 店舗ID={default_store_id}の設定は既に存在します")
    
    # 4. デフォルトの景品設定を作成（存在しない場合）
    cur.execute('SELECT COUNT(*) FROM "T_店舗景品設定" WHERE 店舗ID = ?', (default_store_id,))
    if cur.fetchone()[0] == 0:
        default_prizes = [
            ("特賞: 商品券3000円分", 200, 999999, 10, True),
            ("1等: 商品券1000円分", 100, 199.9, 20, True),
            ("2等: ドリンク無料券", 50, 99.9, 50, True),
            ("3等: 次回10%割引券", 25, 49.9, 100, True),
            ("参加賞: ありがとうございました", 0, 24.9, 999999, True)
        ]
        
        for prize in default_prizes:
            cur.execute('''
                INSERT INTO "T_店舗景品設定" (店舗ID, 景品名, 最小得点, 最大得点, 在庫数, 有効フラグ)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (default_store_id,) + prize)
        
        print(f"✅ 景品設定: {len(default_prizes)}件のデフォルト景品を店舗ID={default_store_id}に作成しました")
    else:
        print(f"ℹ️ 景品設定: 店舗ID={default_store_id}の設定は既に存在します")
    
    # 5. Google口コミURL設定を作成（存在しない場合）
    cur.execute('SELECT COUNT(*) FROM "T_店舗Google口コミ設定" WHERE 店舗ID = ?', (default_store_id,))
    if cur.fetchone()[0] == 0:
        cur.execute('''
            INSERT INTO "T_店舗Google口コミ設定" (店舗ID, Google口コミURL)
            VALUES (?, ?)
        ''', (default_store_id, ''))
        
        print(f"✅ Google口コミURL設定: 空の設定を店舗ID={default_store_id}に作成しました")
    else:
        print(f"ℹ️ Google口コミURL設定: 店舗ID={default_store_id}の設定は既に存在します")
    
    conn.commit()
    conn.close()
    
    print("\n=== マイグレーション完了 ===")


if __name__ == "__main__":
    migrate_existing_data()
