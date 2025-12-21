#!/usr/bin/env python3
"""
データベース自動初期化モジュール
アプリケーション起動時に必要なテーブルとカラムを自動作成します
SQLiteとPostgreSQLの両方に対応
"""
import os
from db_config import get_db_connection, get_cursor, get_db_type

def add_column_if_not_exists(cur, conn, table_name, column_name, column_def, db_type):
    """既存テーブルにカラムが存在しない場合のみ追加"""
    try:
        if db_type == 'postgresql':
            # PostgreSQLの場合
            cur.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = '{column_name}'
            """)
            if not cur.fetchone():
                cur.execute(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {column_def}')
                conn.commit()
                print(f"  ✓ {table_name}.{column_name} カラムを追加しました")
            else:
                print(f"  - {table_name}.{column_name} カラムは既に存在します")
        else:
            # SQLiteの場合
            cur.execute(f'PRAGMA table_info("{table_name}")')
            columns = [row[1] for row in cur.fetchall()]
            if column_name not in columns:
                cur.execute(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {column_def}')
                conn.commit()
                print(f"  ✓ {table_name}.{column_name} カラムを追加しました")
            else:
                print(f"  - {table_name}.{column_name} カラムは既に存在します")
    except Exception as e:
        print(f"  ! {table_name}.{column_name} カラム追加エラー: {e}")

def table_exists(cur, table_name, db_type):
    """テーブルが存在するか確認"""
    try:
        if db_type == 'postgresql':
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """)
            return cur.fetchone()[0]
        else:
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            return cur.fetchone() is not None
    except:
        return False

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
        print("✓ T_テナントテーブルを確認しました")
        
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
        print("✓ T_店舗テーブルを確認しました")
        
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
        print("✓ T_管理者テーブルを確認しました")
        
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
        print("✓ T_管理者_店舗テーブルを確認しました")
        
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
                    active        INTEGER DEFAULT 1,
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
                    active        INTEGER DEFAULT 1,
                    created_at    {timestamp_type},
                    updated_at    {timestamp_type}
                )
            ''')
        conn.commit()
        print("✓ T_従業員テーブルを確認しました")
        
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
        print("✓ T_従業員_店舗テーブルを確認しました")
        
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
        print("✓ T_テナント管理者_テナントテーブルを確認しました")
        
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
        print("✓ T_店舗_アンケート設定テーブルを確認しました")
        
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
        print("✓ T_店舗_Google設定テーブルを確認しました")
        
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
        print("✓ T_店舗_スロット設定テーブルを確認しました")
        
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
        print("✓ T_店舗_景品設定テーブルを確認しました")
        
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
        print("✓ T_アンケート回答テーブルを確認しました")
        
        # 13. T_顧客テーブル（スタンプカード用）
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_顧客" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL,
                    phone           TEXT,
                    email           TEXT,
                    name            TEXT NOT NULL,
                    password_hash   TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    last_login      TIMESTAMP,
                    UNIQUE(store_id, phone),
                    UNIQUE(store_id, email)
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_顧客" (
                    id              {serial_type},
                    store_id        INTEGER NOT NULL,
                    phone           TEXT,
                    email           TEXT,
                    name            TEXT NOT NULL,
                    password_hash   TEXT,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    last_login      TIMESTAMP,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE,
                    UNIQUE(store_id, phone),
                    UNIQUE(store_id, email)
                )
            ''')
        conn.commit()
        print("✓ T_顧客テーブルを確認しました")
        
        # 14. T_店舗_スタンプカード設定テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_スタンプカード設定" (
                    id                  {serial_type},
                    store_id            INTEGER NOT NULL UNIQUE,
                    required_stamps     INTEGER DEFAULT 10,
                    reward_description  TEXT,
                    card_title          TEXT DEFAULT 'スタンプカード',
                    enabled             INTEGER DEFAULT 1,
                    created_at          {timestamp_type},
                    updated_at          {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_店舗_スタンプカード設定" (
                    id                  {serial_type},
                    store_id            INTEGER NOT NULL UNIQUE,
                    required_stamps     INTEGER DEFAULT 10,
                    reward_description  TEXT,
                    card_title          TEXT DEFAULT 'スタンプカード',
                    enabled             INTEGER DEFAULT 1,
                    created_at          {timestamp_type},
                    updated_at          {timestamp_type},
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_店舗_スタンプカード設定テーブルを確認しました")
        
        # 15. T_スタンプカードテーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_スタンプカード" (
                    id              {serial_type},
                    customer_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    current_stamps  INTEGER DEFAULT 0,
                    total_stamps    INTEGER DEFAULT 0,
                    rewards_used    INTEGER DEFAULT 0,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    UNIQUE(customer_id, store_id)
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_スタンプカード" (
                    id              {serial_type},
                    customer_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    current_stamps  INTEGER DEFAULT 0,
                    total_stamps    INTEGER DEFAULT 0,
                    rewards_used    INTEGER DEFAULT 0,
                    created_at      {timestamp_type},
                    updated_at      {timestamp_type},
                    FOREIGN KEY (customer_id) REFERENCES T_顧客(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE,
                    UNIQUE(customer_id, store_id)
                )
            ''')
        conn.commit()
        print("✓ T_スタンプカードテーブルを確認しました")
        
        # 16. T_スタンプ履歴テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_スタンプ履歴" (
                    id              {serial_type},
                    card_id         INTEGER NOT NULL,
                    customer_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    stamps_added    INTEGER DEFAULT 1,
                    action_type     TEXT DEFAULT 'add',
                    note            TEXT,
                    created_by      TEXT,
                    created_at      {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_スタンプ履歴" (
                    id              {serial_type},
                    card_id         INTEGER NOT NULL,
                    customer_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    stamps_added    INTEGER DEFAULT 1,
                    action_type     TEXT DEFAULT 'add',
                    note            TEXT,
                    created_by      TEXT,
                    created_at      {timestamp_type},
                    FOREIGN KEY (card_id) REFERENCES T_スタンプカード(id) ON DELETE CASCADE,
                    FOREIGN KEY (customer_id) REFERENCES T_顧客(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_スタンプ履歴テーブルを確認しました")
        
        # 17. T_特典利用履歴テーブル
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_特典利用履歴" (
                    id              {serial_type},
                    card_id         INTEGER NOT NULL,
                    customer_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    stamps_used     INTEGER NOT NULL,
                    reward_description TEXT,
                    used_by         TEXT,
                    created_at      {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_特典利用履歴" (
                    id              {serial_type},
                    card_id         INTEGER NOT NULL,
                    customer_id     INTEGER NOT NULL,
                    store_id        INTEGER NOT NULL,
                    stamps_used     INTEGER NOT NULL,
                    reward_description TEXT,
                    used_by         TEXT,
                    created_at      {timestamp_type},
                    FOREIGN KEY (card_id) REFERENCES T_スタンプカード(id) ON DELETE CASCADE,
                    FOREIGN KEY (customer_id) REFERENCES T_顧客(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_特典利用履歴テーブルを確認しました")
        
        # 18. T_特典設定テーブル（複数特典機能）
        if db_type == 'postgresql':
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_特典設定" (
                    id                  {serial_type},
                    store_id            INTEGER NOT NULL,
                    required_stamps     INTEGER NOT NULL,
                    reward_description  TEXT NOT NULL,
                    is_repeatable       INTEGER DEFAULT 0,
                    display_order       INTEGER DEFAULT 0,
                    enabled             INTEGER DEFAULT 1,
                    created_at          {timestamp_type},
                    updated_at          {timestamp_type}
                )
            ''')
        else:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "T_特典設定" (
                    id                  {serial_type},
                    store_id            INTEGER NOT NULL,
                    required_stamps     INTEGER NOT NULL,
                    reward_description  TEXT NOT NULL,
                    is_repeatable       INTEGER DEFAULT 0,
                    display_order       INTEGER DEFAULT 0,
                    enabled             INTEGER DEFAULT 1,
                    created_at          {timestamp_type},
                    updated_at          {timestamp_type},
                    FOREIGN KEY (store_id) REFERENCES T_店舗(id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("✓ T_特典設定テーブルを確認しました")
        
        # 既存テーブルにカラムを追加
        # T_店舗_スタンプカード設定にuse_multi_rewardsカラムを追加
        add_column_if_not_exists(cur, conn, 'T_店舗_スタンプカード設定', 'use_multi_rewards', 'INTEGER DEFAULT 0', db_type)
        
        # T_特典利用履歴にreward_idカラムを追加
        add_column_if_not_exists(cur, conn, 'T_特典利用履歴', 'reward_id', 'INTEGER DEFAULT NULL', db_type)
        
        # ===== 既存テーブルへのカラム追加（アップデート対応） =====
        print("\n" + "-" * 60)
        print("既存テーブルのカラム確認・追加を開始します")
        print("-" * 60)
        
        # T_テナントテーブルのカラム追加
        if table_exists(cur, 'T_テナント', db_type):
            add_column_if_not_exists(cur, conn, 'T_テナント', 'openai_api_key', 'TEXT DEFAULT NULL', db_type)
            add_column_if_not_exists(cur, conn, 'T_テナント', 'updated_at', 'TIMESTAMP DEFAULT NULL', db_type)
        
        # T_店舗テーブルのカラム追加
        if table_exists(cur, 'T_店舗', db_type):
            add_column_if_not_exists(cur, conn, 'T_店舗', 'openai_api_key', 'TEXT DEFAULT NULL', db_type)
            add_column_if_not_exists(cur, conn, 'T_店舗', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP', db_type)
        
        # T_管理者テーブルのカラム追加
        if table_exists(cur, 'T_管理者', db_type):
            add_column_if_not_exists(cur, conn, 'T_管理者', 'email', 'TEXT', db_type)
            add_column_if_not_exists(cur, conn, 'T_管理者', 'is_owner', 'INTEGER DEFAULT 0', db_type)
            add_column_if_not_exists(cur, conn, 'T_管理者', 'can_manage_admins', 'INTEGER DEFAULT 0', db_type)
            add_column_if_not_exists(cur, conn, 'T_管理者', 'active', 'INTEGER DEFAULT 1', db_type)
            add_column_if_not_exists(cur, conn, 'T_管理者', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP', db_type)
        
        # T_従業員テーブルのカラム追加
        if table_exists(cur, 'T_従業員', db_type):
            add_column_if_not_exists(cur, conn, 'T_従業員', 'active', 'INTEGER DEFAULT 1', db_type)
        
        # T_店舗_アンケート設定テーブルのカラム追加
        if table_exists(cur, 'T_店舗_アンケート設定', db_type):
            add_column_if_not_exists(cur, conn, 'T_店舗_アンケート設定', 'openai_api_key', 'TEXT DEFAULT NULL', db_type)
            add_column_if_not_exists(cur, conn, 'T_店舗_アンケート設定', 'title', "TEXT DEFAULT 'お店アンケート'", db_type)
        
        # T_店舗_スロット設定テーブルのカラム追加
        if table_exists(cur, 'T_店舗_スロット設定', db_type):
            add_column_if_not_exists(cur, conn, 'T_店舗_スロット設定', 'openai_api_key', 'TEXT DEFAULT NULL', db_type)
        
        # T_アンケート回答テーブルのカラム追加
        if table_exists(cur, 'T_アンケート回答', db_type):
            add_column_if_not_exists(cur, conn, 'T_アンケート回答', 'generated_review', 'TEXT', db_type)
            add_column_if_not_exists(cur, conn, 'T_アンケート回答', 'response_json', 'TEXT', db_type)
            add_column_if_not_exists(cur, conn, 'T_アンケート回答', 'visit_purpose', 'TEXT', db_type)
            add_column_if_not_exists(cur, conn, 'T_アンケート回答', 'atmosphere', 'TEXT', db_type)
            add_column_if_not_exists(cur, conn, 'T_アンケート回答', 'recommend', 'TEXT', db_type)
            add_column_if_not_exists(cur, conn, 'T_アンケート回答', 'comment', 'TEXT', db_type)
        
        # 予約システムのテーブルを作成
        print("\n" + "-" * 60)
        print("予約システム用テーブルの作成を開始します")
        print("-" * 60)
        
        # 1. T_店舗_予約設定テーブル
        print("\n✓ T_店舗_予約設定テーブルを確認しました")
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
        
        # 2. T_テーブル設定テーブル
        print("✓ T_テーブル設定テーブルを確認しました")
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
        
        # 3. T_予約テーブル
        print("✓ T_予約テーブルを確認しました")
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
        
        # 4. インデックスの作成
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservation_settings_store ON "T_店舗_予約設定"(store_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_table_settings_store ON "T_テーブル設定"(store_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservations_store ON "T_予約"(store_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservations_date ON "T_予約"(予約日)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_reservations_status ON "T_予約"(ステータス)')
            conn.commit()
        except Exception as e:
            print(f"  ! インデックス作成エラー（無視します）: {e}")
        
        print("\n" + "=" * 60)
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
