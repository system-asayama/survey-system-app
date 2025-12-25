# 口コミ投稿促進設定機能 実装ガイド

## 概要

本ドキュメントは、警告付き「星4以上のみ投稿を促す」設定機能の実装内容を説明します。

## 実装された機能

### 1. データベーススキーマ

#### 追加されたテーブル・カラム

##### T_店舗_Google設定テーブル

新規カラム：
- `review_prompt_mode` (TEXT): 投稿促進モード
  - `'all'`: 全ての評価に投稿を促す（デフォルト）
  - `'high_rating_only'`: 星4以上のみ投稿を促す

##### T_店舗_Google設定_ログテーブル（新規）

設定変更の履歴を記録：

| カラム名 | 型 | 説明 |
|---------|---|------|
| id | SERIAL/INTEGER | 主キー |
| store_id | INTEGER | 店舗ID |
| admin_id | INTEGER | 管理者ID |
| action | TEXT | アクション（'review_prompt_mode_changed'） |
| old_value | TEXT | 変更前の値 |
| new_value | TEXT | 変更後の値 |
| warnings_shown | BOOLEAN/INTEGER | 警告を表示したか |
| checkboxes_confirmed | BOOLEAN/INTEGER | チェックボックスで確認したか |
| ip_address | TEXT | IPアドレス |
| user_agent | TEXT | ユーザーエージェント |
| created_at | TIMESTAMP | 作成日時 |

##### T_店舗_Google設定_リマインドテーブル（新規）

リマインド送信履歴を記録：

| カラム名 | 型 | 説明 |
|---------|---|------|
| id | SERIAL/INTEGER | 主キー |
| store_id | INTEGER | 店舗ID |
| reminded_at | TIMESTAMP | リマインド送信日時 |
| review_prompt_mode | TEXT | 送信時の設定モード |
| action_taken | TEXT | 実行されたアクション |

### 2. バックエンドロジック

#### review_prompt_settings.py

主要な関数：

##### ReviewPromptMode (Enum)
```python
class ReviewPromptMode(Enum):
    ALL = 'all'
    HIGH_RATING_ONLY = 'high_rating_only'
```

##### get_review_prompt_mode(store_id)
店舗の現在の設定を取得

##### should_show_review_button(store_id, rating)
設定に基づいてレビューボタンを表示すべきか判定

##### save_review_prompt_mode(...)
設定を保存し、ログを記録

##### get_stores_needing_reminder()
リマインドが必要な店舗のリストを取得

##### record_reminder_sent(store_id, action_taken)
リマインド送信を記録

### 3. 管理画面

#### 設定ページ

URL: `/admin/store_settings/<store_id>/review_prompt`

機能：
- 2つの設定モードから選択
- 各モードの説明とリスク表示
- 視覚的に分かりやすいUI

#### 警告モーダル

「星4以上のみ投稿を促す」を選択した場合に表示：

内容：
1. Googleポリシー違反の警告
2. 具体的なペナルティの説明
3. 法的リスクの説明
4. 実際の摘発事例
5. 3つの確認チェックボックス
6. 「安全な設定に戻る」ボタン
7. 「それでも使用する」ボタン（チェック後に有効化）

### 4. レビュー確認ページの修正

#### 条件分岐

設定に基づいて表示内容を変更：

- `show_review_button = True`: Google口コミ投稿ボタンを表示
- `show_review_button = False`: 投稿ボタンを非表示

#### 自動遷移の削除

問題点：
- 旧実装：Google口コミページを開いた1秒後に自動でスロットページへ遷移
- お客様が投稿中に勝手に移動してしまう

改善：
- 自動遷移を削除
- お客様が「スロットへ進む」ボタンを押すまで待つ

### 5. 定期リマインド機能

#### send_review_prompt_reminders.py

機能：
- high_rating_only設定の店舗を検索
- 30日以上リマインドされていない店舗を抽出
- 管理者にリマインドメール送信
- 送信履歴を記録

実行方法：
```bash
python3 send_review_prompt_reminders.py
```

cron設定（毎月1日午前9時）：
```
0 9 1 * * cd /home/ubuntu/survey-system-app && /usr/bin/python3 send_review_prompt_reminders.py >> /var/log/review_prompt_reminders.log 2>&1
```

### 6. 利用規約

ファイル: `TERMS_OF_SERVICE_REVIEW_PROMPT.md`

内容：
- 本機能の概要
- リスクの明示
- 免責事項
- 警告と確認
- 定期リマインド
- 推奨事項

## ファイル一覧

### 新規作成されたファイル

| ファイル名 | 説明 |
|-----------|------|
| `add_review_prompt_settings.py` | データベーススキーマ拡張スクリプト |
| `review_prompt_settings.py` | バックエンドロジック |
| `app/templates/store_settings/review_prompt.html` | 設定ページテンプレート |
| `send_review_prompt_reminders.py` | リマインド送信スクリプト |
| `CRON_SETUP.md` | cron設定手順書 |
| `TERMS_OF_SERVICE_REVIEW_PROMPT.md` | 利用規約 |
| `REVIEW_PROMPT_IMPLEMENTATION_GUIDE.md` | 本ドキュメント |

### 修正されたファイル

| ファイル名 | 変更内容 |
|-----------|---------|
| `store_settings_routes.py` | 設定ページのルート追加 |
| `app/templates/store_settings/index.html` | 設定ボタン追加 |
| `app/blueprints/survey.py` | レビュー確認ページのロジック修正 |
| `app/templates/review_confirm.html` | 条件分岐と自動遷移削除 |

## 使用方法

### 管理者向け

#### 1. 設定の変更

1. 管理画面にログイン
2. 「店舗設定」をクリック
3. 対象店舗の「口コミ投稿促進設定」をクリック
4. 設定モードを選択
5. 「設定を保存」をクリック

#### 2. リスクある設定を選択する場合

1. 「星4以上のみ投稿を促す」を選択
2. 「設定を保存」をクリック
3. 警告モーダルが表示される
4. 警告内容を読む
5. 3つのチェックボックスにチェック
6. 「それでも使用する」をクリック

#### 3. 定期リマインドの設定

`CRON_SETUP.md`を参照してcronジョブを設定してください。

### 開発者向け

#### データベーススキーマの初期化

```bash
cd /home/ubuntu/survey-system-app
python3 add_review_prompt_settings.py
```

#### 設定の取得

```python
from review_prompt_settings import get_review_prompt_mode

mode = get_review_prompt_mode(store_id)
# 'all' または 'high_rating_only'
```

#### レビューボタン表示判定

```python
from review_prompt_settings import should_show_review_button

show_button = should_show_review_button(store_id, rating)
# True または False
```

#### 設定の保存

```python
from review_prompt_settings import save_review_prompt_mode, ReviewPromptMode

save_review_prompt_mode(
    store_id=1,
    mode=ReviewPromptMode.ALL.value,
    admin_id=1,
    ip_address='192.168.1.1',
    user_agent='Mozilla/5.0...',
    warnings_shown=False,
    checkboxes_confirmed=False
)
```

## セキュリティ考慮事項

### 1. ログの保存

全ての設定変更は以下の情報とともにログに記録されます：

- 変更日時
- 管理者ID
- IPアドレス
- ユーザーエージェント
- 警告表示の有無
- チェックボックス確認の有無

### 2. 免責の証拠

ログは、利用者が警告を確認したことの証拠として使用できます。

### 3. データの保護

ログに含まれる個人情報は適切に管理してください。

## トラブルシューティング

### 設定が保存されない

1. データベース接続を確認
2. `add_review_prompt_settings.py`が実行されているか確認
3. エラーログを確認

### レビューボタンが表示されない

1. 設定が正しく保存されているか確認
2. `should_show_review_button()`の戻り値を確認
3. テンプレートの条件分岐を確認

### リマインドが送信されない

1. cronジョブが設定されているか確認
2. Pythonのパスが正しいか確認
3. メール送信設定を確認
4. ログファイルを確認

## 今後の拡張案

### 1. メール送信の実装

現在はデモ実装です。実際のSMTP/SendGrid実装を追加してください。

### 2. 管理画面でのリマインド履歴表示

リマインド送信履歴を管理画面で確認できるようにする。

### 3. 設定変更履歴の表示

設定変更ログを管理画面で確認できるようにする。

### 4. A/Bテスト機能

2つの設定モードの効果を比較する機能。

### 5. 多言語対応

警告メッセージの多言語対応。

## まとめ

本実装は、以下の5つの条件を満たしています：

1. ✅ 極めて強力な警告
2. ✅ デフォルトは安全設定
3. ✅ 定期的なリマインド
4. ✅ ログの保存
5. ✅ 利用規約の作成

利用者の選択権を尊重しつつ、安全な方向に誘導する設計になっています。
