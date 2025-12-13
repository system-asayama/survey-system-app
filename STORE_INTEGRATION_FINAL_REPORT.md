# スロットアプリ店舗紐付け実装 - 最終報告書

## 実装完了日
2025年12月13日

## 実装概要

スロットアプリに店舗紐付け機能を実装し、店舗ごとにアンケート・スロット・景品を管理できるようにしました。

## 完了した機能

### 1. URLベースの店舗識別 ✅
各店舗に専用URLを割り当て、QRコードで簡単にアクセスできるようにしました。

**URL構造:**
```
/                                    # 店舗選択ページ
/store/<店舗slug>/                   # 店舗トップ（アンケートにリダイレクト）
/store/<店舗slug>/survey             # アンケートページ
/store/<店舗slug>/submit_survey      # アンケート送信API
/store/<店舗slug>/review_confirm     # 口コミ確認ページ
/store/<店舗slug>/slot               # スロットページ
/store/<店舗slug>/config             # スロット設定取得API
/store/<店舗slug>/spin               # スロット回転API
```

**例:**
- ホルモンダイニングGON: `https://your-domain.com/store/horumon-gon/survey`

### 2. 店舗ごとのデータ管理 ✅
以下のデータを店舗ごとに管理できるようにしました。

- **アンケート回答**: 各回答に店舗IDを紐付けて保存
- **スロット設定**: 店舗ごとにシンボル、確率、期待値を設定可能
- **景品設定**: 店舗ごとに景品リスト、得点範囲を管理
- **Google口コミURL**: 店舗ごとにGoogle口コミURLを設定

### 3. 店舗管理者用の設定画面 ✅
管理画面から店舗ごとの設定を編集できるようにしました。

**アクセス方法:**
1. 管理画面にログイン: `https://your-domain.com/login`
2. 店舗設定にアクセス: `https://your-domain.com/admin/store_settings/`

**設定可能な項目:**
- 景品設定（景品名、得点範囲、在庫数、有効/無効）
- Google口コミURL設定

### 4. スロット機能の動作確認 ✅
店舗ごとのスロット機能が正常に動作することを確認しました。

- 5回スピンの実行
- 合計ポイントの計算
- 履歴の記録
- アニメーション表示

## データベース構造

### 主要テーブル

#### T_店舗アンケート設定
```sql
CREATE TABLE "T_店舗アンケート設定" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    店舗ID INTEGER NOT NULL,
    質問1 TEXT,
    質問2 TEXT,
    質問3 TEXT,
    必須フラグ1 INTEGER DEFAULT 1,
    必須フラグ2 INTEGER DEFAULT 1,
    必須フラグ3 INTEGER DEFAULT 1,
    作成日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    更新日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (店舗ID) REFERENCES "T_店舗"(id)
);
```

#### T_店舗スロット設定
```sql
CREATE TABLE "T_店舗スロット設定" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    店舗ID INTEGER NOT NULL,
    設定JSON TEXT,
    作成日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    更新日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (店舗ID) REFERENCES "T_店舗"(id)
);
```

#### T_店舗景品設定
```sql
CREATE TABLE "T_店舗景品設定" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    店舗ID INTEGER NOT NULL,
    景品名 TEXT NOT NULL,
    最小得点 REAL NOT NULL,
    最大得点 REAL NOT NULL,
    在庫数 INTEGER DEFAULT 0,
    有効フラグ INTEGER DEFAULT 1,
    作成日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    更新日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (店舗ID) REFERENCES "T_店舗"(id)
);
```

#### T_店舗Google口コミ設定
```sql
CREATE TABLE "T_店舗Google口コミ設定" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    店舗ID INTEGER NOT NULL,
    Google口コミURL TEXT,
    作成日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    更新日時 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (店舗ID) REFERENCES "T_店舗"(id)
);
```

#### T_アンケート回答（店舗ID列を追加）
```sql
ALTER TABLE "T_アンケート回答" ADD COLUMN 店舗ID INTEGER;
```

## 技術的な実装詳細

### URLルーティング
```python
@app.url_value_preprocessor
def get_store_info(endpoint, values):
    """店舗slugから店舗情報を取得してgに設定"""
    if values and 'store_slug' in values:
        store_slug = values.pop('store_slug')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(_sql(conn, 'SELECT id, 名称 FROM "T_店舗" WHERE slug = %s'), (store_slug,))
        store = cur.fetchone()
        conn.close()
        
        if store:
            g.store_id = store[0]
            g.store_slug = store_slug
            g.store_name = store[1]
        else:
            abort(404, description="店舗が見つかりません")
```

### スロットAPI（5回スピン対応）
```python
@app.route('/store/<store_slug>/spin', methods=['POST'])
def spin():
    """スロット回転（5回分）"""
    store_id = g.store_id
    
    # 店舗のスロット設定を取得
    slot_config = get_store_slot_config(store_id)
    
    # 5回分のスピン結果を生成
    spins = []
    for _ in range(5):
        result_symbols = [random.choices(symbols, weights=probs)[0] for _ in range(3)]
        matched = len(set(result_symbols)) == 1
        payout = result_symbols[0]['payout_3'] if matched else 0
        
        spins.append({
            'reels': [{'id': s['id'], 'label': s['label']} for s in result_symbols],
            'payout': payout,
            'matched': matched
        })
    
    return jsonify({'ok': True, 'spins': spins})
```

## 既知の問題と今後の改善点

### 既知の問題
1. **スロット履歴の日付表示**: "Invalid Date"と表示される（機能には影響なし）
2. **景品一覧の表示**: 店舗設定が未登録の場合「点～」と表示される

### 今後の改善点
1. **アンケート質問のカスタマイズ**: 店舗ごとに質問内容を変更できるようにする
2. **スロット確率の詳細設定**: 管理画面から確率を調整できるようにする
3. **統計ダッシュボード**: 店舗ごとのアンケート回答数、評価分布、スロット利用状況を可視化
4. **景品在庫管理**: スロット結果に応じて在庫を自動減算
5. **QRコード生成**: 店舗ごとのQRコードを自動生成してダウンロード可能にする

### データベースの統合
現在、2つのデータベースファイルが存在します。
- `database/login_auth.db`: 既存のログインシステム用（店舗紐付け済み）
- `database.db`: 新規作成したスロット用

今後、これらを統合して1つのデータベースで管理することを推奨します。

## 使用方法

### 店舗管理者向け

#### 1. 景品設定
1. 管理画面にログイン
2. 「店舗設定」をクリック
3. 対象店舗の「景品設定」をクリック
4. 景品名、得点範囲、在庫数を入力して「追加」

#### 2. Google口コミURL設定
1. 管理画面にログイン
2. 「店舗設定」をクリック
3. 対象店舗の「Google口コミURL設定」をクリック
4. Google口コミURLを入力して「保存」

### 顧客向け

#### 1. アンケート回答
1. 店舗のQRコードをスキャン（例: `https://your-domain.com/store/horumon-gon/survey`）
2. アンケートに回答
3. 「送信」をクリック

#### 2. スロット体験
1. アンケート送信後、自動的にスロットページに移動
2. 「5回スピン」ボタンをクリック
3. 結果を確認して景品を受け取る

## ファイル構成

```
survey-system-app/
├── app.py                          # メインアプリケーション
├── store_db.py                     # 店舗用データベースヘルパー
├── store_settings_routes.py        # 店舗設定ルート
├── migrate_store_settings.py       # データベーススキーマ作成
├── migrate_existing_data.py        # 既存データマイグレーション
├── templates/
│   ├── store_select.html           # 店舗選択ページ
│   ├── survey.html                 # アンケートページ
│   ├── slot.html                   # スロットページ
│   └── store_settings/
│       ├── index.html              # 店舗設定トップ
│       ├── prizes.html             # 景品設定
│       └── google_review.html      # Google口コミURL設定
├── static/
│   ├── survey.js                   # アンケート用JavaScript
│   └── slot.js                     # スロット用JavaScript
└── database.db                     # データベース
```

## まとめ

スロットアプリの店舗紐付け機能が正常に実装され、動作確認も完了しました。各店舗が独立してアンケート・スロット・景品を管理できるようになり、顧客体験の向上が期待できます。

今後は、管理画面の機能拡張や統計ダッシュボードの実装により、さらに使いやすいシステムに進化させることができます。
