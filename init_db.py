#!/usr/bin/env python3
"""
データベース自動初期化モジュール
アプリケーション起動時に必要なテーブルとカラムを自動作成します
SQLiteとPostgreSQLの両方に対応
"""
import os
from db_config import get_db_connection, get_cursor, get_db_type

def init_database():
    """データベースの初期化（テーブルとカラムの作成）"""
    
    conn = get_db_connection()
    cur = get_cursor(conn)
    db_type = get_db_type()
    
    try:
        print("=" * 60)
        print(f"データベース初期化を開始します ({db_type})")
        print("=" * 60)
        
        # PostgreSQLとSQLiteでAUTO INCREMENTの構文が異なる
        if db_type == 'postgresql':
            serial_type = 'SERIAL PRIMARY KEY'
            timestamp_type = 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        else:
            serial_type = 'INTEGER PRIMARY KEY AUTOINCREMENT'
            timestamp_type = 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        
        # ===== 基本テーブル =====
        
        # 1. T_テナントテーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_テナント" (
                    id          {serial_type},
                    名称        TEXT NOT NULL,
                    slug        TEXT UNIQUE NOT NULL,
                    有効        INTEGER DEFAULT 1,
                    created_at  {timestamp_type},
                    openai_api_key TEXT DEFAULT NULL,
                    updated_at  TIMESTAMP DEFAULT NULL
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_テナント" (
                    id          {serial_type},
                    名称        TEXT NOT NULL,
                    slug        TEXT UNIQUE NOT NULL,
                    有効        INTEGER DEFAULT 1,
                    created_at  {timestamp_type},
                    openai_api_key TEXT DEFAULT NULL,
                    updated_at  TIMESTAMP DEFAULT NULL
                )
            ''')
        conn.commit()
        print("✓ T_テナントテーブルを作成しました")
        
        # 2. T_店舗テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗" (
                    id          {serial_type},
                    tenant_id   INTEGER NOT NULL,
                    名称        TEXT NOT NULL,
                    slug        TEXT NOT NULL,
                    有効        INTEGER DEFAULT 1,
                    created_at  {timestamp_type},
                    updated_at  {timestamp_type},
                    openai_api_key TEXT DEFAULT NULL,
                    UNIQUE(tenant_id, slug)
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗" (
                    id          {serial_type},
                    tenant_id   INTEGER NOT NULL,
                    名称        TEXT NOT NULL,
                    slug        TEXT NOT NULL,
                    有効        INTEGER DEFAULT 1,
                    created_at  {timestamp_type},
                    updated_at  {timestamp_type},
                    openai_api_key TEXT DEFAULT NULL,
                    UNIQUE(tenant_id, slug)
                )
            ''')
        conn.commit()
        print("✓ T_店舗テーブルを作成しました")
        
        # 3. T_管理者テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_管理者" (
                    id               {serial_type},
                    login_id         TEXT UNIQUE NOT NULL,
                    name             TEXT NOT NULL,
                    password_hash    TEXT NOT NULL,
                    role             TEXT DEFAULT 'admin',
                    tenant_id        INTEGER,
                    active           INTEGER DEFAULT 1,
                    is_owner         INTEGER DEFAULT 0,
                    can_manage_admins INTEGER DEFAULT 0,
                    created_at       {timestamp_type},
                    updated_at       {timestamp_type},
                    email            TEXT
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_管理者" (
                    id               {serial_type},
                    login_id         TEXT UNIQUE NOT NULL,
                    name             TEXT NOT NULL,
                    password_hash    TEXT NOT NULL,
                    role             TEXT DEFAULT 'admin',
                    tenant_id        INTEGER,
                    active           INTEGER DEFAULT 1,
                    is_owner         INTEGER DEFAULT 0,
                    can_manage_admins INTEGER DEFAULT 0,
                    created_at       {timestamp_type},
                    updated_at       {timestamp_type},
                    email            TEXT
                )
            ''')
        conn.commit()
        print("✓ T_管理者テーブルを作成しました")
        
        # 4. T_管理者_店舗テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_管理者_店舗" (
                    id          {serial_type},
                    admin_id    INTEGER NOT NULL,
                    store_id    INTEGER NOT NULL,
                    created_at  {timestamp_type},
                    UNIQUE(admin_id, store_id)
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_管理者_店舗" (
                    id          {serial_type},
                    admin_id    INTEGER NOT NULL,
                    store_id    INTEGER NOT NULL,
                    created_at  {timestamp_type},
                    UNIQUE(admin_id, store_id)
                )
            ''')
        conn.commit()
        print("✓ T_管理者_店舗テーブルを作成しました")
        
        # 5. T_従業員テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_従業員" (
                    id            {serial_type},
                    email         TEXT UNIQUE NOT NULL,
                    login_id      TEXT UNIQUE NOT NULL,
                    name          TEXT NOT NULL,
                    password_hash TEXT,
                    tenant_id     INTEGER,
                    role          TEXT DEFAULT 'employee',
                    created_at    {timestamp_type},
                    updated_at    {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_従業員" (
                    id            {serial_type},
                    email         TEXT UNIQUE NOT NULL,
                    login_id      TEXT UNIQUE NOT NULL,
                    name          TEXT NOT NULL,
                    password_hash TEXT,
                    tenant_id     INTEGER,
                    role          TEXT DEFAULT 'employee',
                    created_at    {timestamp_type},
                    updated_at    {timestamp_type}
                )
            ''')
        conn.commit()
        print("✓ T_従業員テーブルを作成しました")
        
        # 6. T_従業員_店舗テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_従業員_店舗" (
                    id              {serial_type},
                    employee_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    created_at      {timestamp_type},
                    UNIQUE(employee_id, store_id)
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_従業員_店舗" (
                    id              {serial_type},
                    employee_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    created_at      {timestamp_type},
                    UNIQUE(employee_id, store_id)
                )
            ''')
        conn.commit()
        print("✓ T_従業員_店舗テーブルを作成しました")
        
        # 7. T_テナント管理者_テナントテーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_テナント管理者_テナント" (
                    id                  {serial_type},
                    tenant_admin_id     INTEGER NOT NULL,
                    tenant_id           INTEGER NOT NULL,
                    created_at          {timestamp_type},
                    UNIQUE(tenant_admin_id, tenant_id)
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_テナント管理者_テナント" (
                    id                  {serial_type},
                    tenant_admin_id     INTEGER NOT NULL,
                    tenant_id           INTEGER NOT NULL,
                    created_at          {timestamp_type},
                    UNIQUE(tenant_admin_id, tenant_id)
                )
            ''')
        conn.commit()
        print("✓ T_テナント管理者_テナントテーブルを作成しました")
        
        # ===== アプリケーション固有テーブル =====
        
        # 8. T_店舗_アンケート設定テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_アンケート設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    title           TEXT DEFAULT 'お店アンケート',
                    config_json     TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    openai_api_key  TEXT DEFAULT NULL
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_アンケート設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    title           TEXT DEFAULT 'お店アンケート',
                    config_json     TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    openai_api_key  TEXT DEFAULT NULL,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_店舗_アンケート設定テーブルを作成しました")
        
        # 9. T_店舗_Google設定テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_Google設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    review_url      TEXT,
                    place_id        TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_Google設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    review_url      TEXT,
                    place_id        TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_店舗_Google設定テーブルを作成しました")
        
        # 10. T_店舗_スロット設定テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_スロット設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    config_json     TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    openai_api_key  TEXT DEFAULT NULL
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_スロット設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    config_json     TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    openai_api_key  TEXT DEFAULT NULL,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_店舗_スロット設定テーブルを作成しました")
        
        # 11. T_店舗_景品設定テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_景品設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    prizes_json     TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_景品設定" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL UNIQUE,
                    prizes_json     TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_店舗_景品設定テーブルを作成しました")
        
        # 12. T_アンケート回答テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_アンケート回答" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL,
                    rating          INTEGER NOT NULL,
                    visit_purpose   TEXT,
                    atmosphere      TEXT,
                    recommend       TEXT,
                    comment         TEXT,
                    generated_review TEXT,
                    response_json   TEXT,
                    created_at      {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_アンケート回答" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL,
                    rating          INTEGER NOT NULL,
                    visit_purpose   TEXT,
                    atmosphere      TEXT,
                    recommend       TEXT,
                    comment         TEXT,
                    generated_review TEXT,
                    response_json   TEXT,
                    created_at      {timestamp_type},
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_アンケート回答テーブルを作成しました")
        
        print("=" * 60)
        print(f"✓ データベース初期化が完了しました ({db_type})")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
