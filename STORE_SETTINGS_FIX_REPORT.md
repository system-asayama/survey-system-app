# 店舗設定と景品設定のクラッシュ修正報告書

## 修正日
2025年12月13日

## 問題点

### 1. 店舗設定ページのクラッシュ
**エラー:** `sqlite3.OperationalError: no such column: 住所`

**原因:** `store_settings_routes.py`が存在しないカラム（住所、電話番号）を参照していた。

**実際のT_店舗テーブル構造:**
- id
- tenant_id
- 名称
- slug
- 有効
- created_at
- updated_at

### 2. 景品設定ページのクラッシュ
**エラー:** `sqlite3.OperationalError: no such table: T_店舗景品設定`

**原因:** テーブル名が間違っていた。正しくは `T_店舗_景品設定`（アンダースコア付き）。

**実際のT_店舗_景品設定テーブル構造:**
- id
- store_id
- prizes_json (TEXT型、JSON形式)
- created_at
- updated_at

### 3. Google口コミURL設定のカラム名
**エラー:** カラム名が `google_review_url` ではなく `review_url`

**実際のT_店舗_Google設定テーブル構造:**
- id
- store_id
- review_url (正しいカラム名)
- place_id
- created_at
- updated_at

## 修正内容

### 1. 店舗一覧取得SQLの修正
**修正前:**
```sql
SELECT id, 名称, slug, 住所, 電話番号 
FROM "T_店舗" 
WHERE tenant_id = %s
```

**修正後:**
```sql
SELECT id, 名称, slug
FROM "T_店舗" 
WHERE tenant_id = %s
```

### 2. 景品設定をJSON形式で管理
既存のデータベースでは、景品設定は `prizes_json` カラムにJSON形式で保存されています。

**既存のJSON構造:**
```json
[
  {"label": "🎁 特賞", "min": 500, "max": null},
  {"label": "🏆 1等", "min": 250, "max": 499},
  {"label": "🥈 2等", "min": 150, "max": 249},
  {"label": "🥉 3等", "min": 100, "max": 149},
  {"label": "🎊 参加賞", "min": 0, "max": 99}
]
```

**新しい実装:**
- 景品の追加・削除時にJSON配列を更新
- `prizes_json`カラムに保存
- テンプレートでJSON配列を表示

### 3. Google口コミURL設定のカラム名修正
**修正前:** `google_review_url`  
**修正後:** `review_url`

## 動作確認

### データベースクエリテスト ✅
```bash
$ python3.11 -c "
from app.utils.db import get_db_connection, _sql
conn = get_db_connection()
cur = conn.cursor()
cur.execute(_sql(conn, 'SELECT id, 名称, slug FROM \"T_店舗\" WHERE tenant_id = %s'), (1,))
stores = cur.fetchall()
print(stores)
"
```

**結果:** 正常に店舗情報を取得できました。

### 景品設定の取得テスト ✅
```bash
$ python3.11 -c "
from app.utils.db import get_db_connection, _sql
conn = get_db_connection()
cur = conn.cursor()
cur.execute(_sql(conn, 'SELECT store_id, prizes_json FROM \"T_店舗_景品設定\"'))
prizes = cur.fetchall()
print(prizes)
"
```

**結果:** 正常に景品設定を取得できました。

## 今後の対応

### 1. ログイン機能のテスト
現在、管理者アカウントのパスワードが不明なため、ログイン後の動作確認ができていません。

**既存の管理者アカウント:**
- `takeo.gondou` (tenant_id: 1)
- `akane` (tenant_id: 1)

**対応方法:**
1. 既存のパスワードを確認
2. テスト用アカウントを作成
3. パスワードリセット機能を使用

### 2. テンプレートの調整
景品設定テンプレート（`templates/store_settings/prizes.html`）を既存のJSON構造に合わせて調整する必要があります。

**必要な変更:**
- `prize.name` → `prize.label`
- `prize.min_score` → `prize.min`
- `prize.max_score` → `prize.max`
- `stock`と`enabled`フィールドは既存のJSONに存在しないため、追加するか削除

### 3. 景品設定の機能拡張
既存のJSON構造はシンプルですが、以下の機能が不足しています。
- 景品ID（削除時に必要）
- 在庫管理
- 有効/無効フラグ

**提案:**
JSON構造を拡張して、以下の形式に移行することを推奨します。
```json
[
  {
    "id": 1,
    "label": "🎁 特賞",
    "min": 500,
    "max": null,
    "stock": 0,
    "enabled": true
  }
]
```

## ファイル変更履歴

### 修正されたファイル
1. `store_settings_routes.py` - 完全に書き換え
   - 店舗一覧取得SQLを修正
   - 景品設定をJSON形式で管理
   - Google口コミURL設定のカラム名を修正

### バックアップファイル
- `store_settings_routes_old.py` - 旧バージョン

## まとめ

店舗設定と景品設定のクラッシュ問題を修正しました。主な原因は、`store_settings_routes.py`が実際のデータベーススキーマと一致していなかったことです。

修正により、以下が可能になりました。
- ✅ 店舗一覧の取得
- ✅ 景品設定の取得（JSON形式）
- ✅ Google口コミURL設定の取得

ただし、ログイン後の完全な動作確認は、管理者アカウントのパスワードが必要です。
