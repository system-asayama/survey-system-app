#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
予約システム用テーブル追加スクリプト
"""
import os
from db_config import get_db_connection, get_cursor, get_db_type

def add_reservation_tables():
    """予約システム用のテーブルを追加"""
    
    conn = get_db_connection()
    cur = get_cursor(conn)
    db_type = get_db_type()
    
    try:
        print("=" * 60)
        print(f"予約システム用テーブルを追加します ({db_type})")
        print("=" * 60)
        
        # PostgreSQLとSQLiteでAUTO INCREMENTの構文が異なる
        if db_type == 'postgresql':
            serial_type = 'SERIAL PRIMARY KEY'
            timestamp_type = 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        else:
            serial_type = 'INTEGER PRIMARY KEY AUTOINCREMENT'
            timestamp_type = 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        
        # 1. T_店舗_予約設定テーブル
        print("\n1. T_店舗_予約設定 テーブルを作成中...")
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS "T_店舗_予約設定" (
                id              {serial_type},
                store_id        INTEGER NOT NULL,
                営業開始時刻    TEXT DEFAULT '11:00',
                営業終了時刻    TEXT DEFAULT '22:00',
                最終入店時刻    TEXT DEFAULT '21:00',
                予約単位_分     INTEGER DEFAULT 30,
                予約受付日数    INTEGER DEFAULT 60,
                定休日          TEXT DEFAULT NULL,
                予約受付可否    INTEGER DEFAULT 1,
                特記事項        TEXT DEFAULT NULL,
                created_at      {timestamp_type},
                updated_at      TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (store_id) REFERENCES "T_店舗"(id)
            )
        ''')
        conn.commit()
        print("  ✓ T_店舗_予約設定 テーブルを作成しました")
        
        # 2. T_テーブル設定テーブル
        print("\n2. T_テーブル設定 テーブルを作成中...")
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS "T_テーブル設定" (
                id              {serial_type},
                store_id        INTEGER NOT NULL,
                テーブル名      TEXT NOT NULL,
                座席数          INTEGER NOT NULL,
                テーブル数      INTEGER DEFAULT 1,
                表示順序        INTEGER DEFAULT 0,
                有効            INTEGER DEFAULT 1,
                created_at      {timestamp_type},
                updated_at      TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (store_id) REFERENCES "T_店舗"(id)
            )
        ''')
        conn.commit()
        print("  ✓ T_テーブル設定 テーブルを作成しました")
        
        # 3. T_予約テーブル
        print("\n3. T_予約 テーブルを作成中...")
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS "T_予約" (
                id              {serial_type},
                store_id        INTEGER NOT NULL,
                予約番号        TEXT UNIQUE NOT NULL,
                予約日          TEXT NOT NULL,
                予約時刻        TEXT NOT NULL,
                人数            INTEGER NOT NULL,
                顧客名          TEXT NOT NULL,
                顧客電話番号    TEXT NOT NULL,
                顧客メール      TEXT DEFAULT NULL,
                特記事項        TEXT DEFAULT NULL,
                ステータス      TEXT DEFAULT 'confirmed',
                テーブル割当    TEXT DEFAULT NULL,
                created_at      {timestamp_type},
                updated_at      TIMESTAMP DEFAULT NULL,
                cancelled_at    TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (store_id) REFERENCES "T_店舗"(id)
            )
        ''')
        conn.commit()
        print("  ✓ T_予約 テーブルを作成しました")
        
        # 4. インデックスの作成
        print("\n4. インデックスを作成中...")
        
        # 予約設定のstore_idインデックス
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservation_settings_store ON "T_店舗_予約設定"(store_id)')
            print("  ✓ idx_reservation_settings_store を作成しました")
        except Exception as e:
            print(f"  ! インデックス作成エラー: {e}")
        
        # テーブル設定のstore_idインデックス
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_table_settings_store ON "T_テーブル設定"(store_id)')
            print("  ✓ idx_table_settings_store を作成しました")
        except Exception as e:
            print(f"  ! インデックス作成エラー: {e}")
        
        # 予約のstore_idインデックス
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservations_store ON "T_予約"(store_id)')
            print("  ✓ idx_reservations_store を作成しました")
        except Exception as e:
            print(f"  ! インデックス作成エラー: {e}")
        
        # 予約の日付インデックス
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservations_date ON "T_予約"(予約日)')
            print("  ✓ idx_reservations_date を作成しました")
        except Exception as e:
            print(f"  ! インデックス作成エラー: {e}")
        
        # 予約のステータスインデックス
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservations_status ON "T_予約"(ステータス)')
            print("  ✓ idx_reservations_status を作成しました")
        except Exception as e:
            print(f"  ! インデックス作成エラー: {e}")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("予約システム用テーブルの追加が完了しました")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    add_reservation_tables()
