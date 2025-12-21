# 予約システム - 実装ドキュメント

## 概要

飲食店向けのオンライン予約システムを既存のサーベイシステムに統合しました。テーブル管理機能と空席状況のリアルタイム確認機能を備えています。

## 実装日

2024年12月21日

## データベース構造

### T_店舗_予約設定

店舗ごとの予約設定を管理するテーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| store_id | INTEGER | 店舗ID（外部キー） |
| 営業開始時刻 | TEXT | 営業開始時刻（例: "11:00"） |
| 営業終了時刻 | TEXT | 営業終了時刻（例: "22:00"） |
| 最終入店時刻 | TEXT | 最終入店可能時刻（例: "21:00"） |
| 予約単位_分 | INTEGER | 予約時間の単位（15/30/60分） |
| 予約受付日数 | INTEGER | 何日先まで予約を受け付けるか |
| 定休日 | TEXT | 定休日（カンマ区切り、例: "月,火"） |
| 予約受付可否 | INTEGER | 予約受付のON/OFF（1=有効, 0=無効） |
| 特記事項 | TEXT | 特記事項 |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### T_テーブル設定

テーブルタイプと座席数を管理するテーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| store_id | INTEGER | 店舗ID（外部キー） |
| テーブル名 | TEXT | テーブル名（例: "2人席", "4人席"） |
| 座席数 | INTEGER | 座席数 |
| テーブル数 | INTEGER | このタイプのテーブルの数 |
| 表示順序 | INTEGER | 表示順序 |
| 有効 | INTEGER | 有効フラグ（1=有効, 0=無効） |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### T_予約

予約データを管理するテーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| store_id | INTEGER | 店舗ID（外部キー） |
| 予約番号 | TEXT | 予約番号（例: "RES20241221-ABC123"） |
| 予約日 | TEXT | 予約日（YYYY-MM-DD形式） |
| 予約時刻 | TEXT | 予約時刻（HH:MM形式） |
| 人数 | INTEGER | 予約人数 |
| 顧客名 | TEXT | 顧客名 |
| 顧客電話番号 | TEXT | 顧客電話番号 |
| 顧客メール | TEXT | 顧客メールアドレス |
| 特記事項 | TEXT | 特記事項（アレルギー、記念日など） |
| ステータス | TEXT | ステータス（confirmed/cancelled） |
| テーブル割当 | TEXT | 割り当てられたテーブル名 |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |
| cancelled_at | TIMESTAMP | キャンセル日時 |

## API エンドポイント

### 顧客向けエンドポイント

#### GET /store/{store_slug}/reservation/
予約フォームを表示

#### POST /store/{store_slug}/reservation/api/time_slots
指定日の予約可能時間枠を取得

**リクエスト:**
```json
{
  "date": "2024-12-25",
  "party_size": 4
}
```

**レスポンス:**
```json
{
  "time_slots": [
    {
      "time": "11:00",
      "available": true,
      "display": "11:00"
    },
    {
      "time": "11:30",
      "available": false,
      "display": "11:30"
    }
  ]
}
```

#### POST /store/{store_slug}/reservation/api/availability
指定日時の空席状況を確認

**リクエスト:**
```json
{
  "date": "2024-12-25",
  "time": "18:00",
  "party_size": 4
}
```

**レスポンス:**
```json
{
  "available": true,
  "table_type": "4人席",
  "seats": 4,
  "available_count": 2
}
```

#### POST /store/{store_slug}/reservation/api/submit
予約を登録

**リクエスト:**
```json
{
  "date": "2024-12-25",
  "time": "18:00",
  "party_size": 4,
  "name": "山田太郎",
  "phone": "090-1234-5678",
  "email": "yamada@example.com",
  "notes": "窓際の席を希望"
}
```

**レスポンス:**
```json
{
  "success": true,
  "reservation_number": "RES20241221-ABC123",
  "reservation_id": 1
}
```

#### GET /store/{store_slug}/reservation/confirmation/{reservation_number}
予約確認画面を表示

### 管理画面エンドポイント

#### GET /admin/store/{store_id}/reservation/settings
予約設定画面（要ログイン）

#### POST /admin/store/{store_id}/reservation/settings/save
予約設定を保存（要ログイン）

#### POST /admin/store/{store_id}/reservation/tables/add
テーブル設定を追加（要ログイン）

#### POST /admin/store/{store_id}/reservation/tables/{table_id}/delete
テーブル設定を削除（要ログイン）

#### GET /admin/store/{store_id}/reservation/list
予約一覧画面（要ログイン）

#### POST /admin/store/{store_id}/reservation/{reservation_id}/cancel
予約をキャンセル（要ログイン）

#### GET /admin/store/{store_id}/reservation/{reservation_id}/edit
予約編集画面（要ログイン）

#### POST /admin/store/{store_id}/reservation/{reservation_id}/edit
予約を更新（要ログイン）

#### GET /admin/store/{store_id}/reservation/calendar
予約カレンダー表示（要ログイン）

## 機能説明

### テーブル管理機能

1. **テーブル設定の追加**
   - 管理画面でテーブル名、座席数、テーブル数を設定
   - 例: 2人席×5台、4人席×3台、6人席×2台

2. **自動テーブル割当**
   - 予約時に人数に応じて適切なテーブルを自動割当
   - 小さいテーブルから優先的に割当（効率的な席配置）

3. **空席状況の確認**
   - リアルタイムで各時間帯の空席状況を確認
   - 予約済みのテーブル数を差し引いて空席を計算

### 予約フロー

1. **日時選択**
   - カレンダーから予約日を選択
   - 人数を選択
   - 空いている時間枠から予約時間を選択

2. **お客様情報入力**
   - お名前（必須）
   - 電話番号（必須）
   - メールアドレス（任意）
   - 特記事項（任意）

3. **確認**
   - 入力内容を確認
   - 予約を確定

4. **完了**
   - 予約番号を発行
   - 予約確認画面を表示

## デフォルト設定

- **営業時間**: 11:00～22:00
- **最終入店時刻**: 21:00
- **予約時間単位**: 30分
- **予約受付日数**: 60日先まで
- **定休日**: なし

これらの設定は管理画面から変更可能です。

## セットアップ手順

### 1. データベースの初期化

```bash
cd /home/ubuntu/survey-system-app
python3.11 add_reservation_tables.py
```

### 2. アプリケーションの起動

```bash
python3.11 run.py
```

### 3. 管理画面でテーブル設定

1. `/admin/login` にアクセス
2. ログイン（店舗コード: default, ID: admin, パスワード: admin123）
3. 店舗アプリ一覧から「予約システム」→「設定」
4. テーブル設定を追加（例: 2人席×5台、4人席×3台）
5. 営業時間や予約受付日数を設定

### 4. 予約フォームのテスト

1. 「プレビュー」ボタンをクリック
2. 予約フォームで日時を選択
3. お客様情報を入力
4. 予約を確定

## POSレジ連携の準備

予約データは `T_予約` テーブルに保存されており、以下の情報でPOSレジと連携可能です。

- 予約番号
- 予約日時
- 顧客情報（名前、電話番号）
- 人数
- テーブル割当

APIエンドポイントを追加することで、POSレジから予約情報を取得・更新することができます。

## 今後の拡張案

1. **メール通知機能**
   - 予約確定時の自動メール送信
   - 予約前日のリマインダーメール

2. **SMS通知機能**
   - 予約確定時のSMS送信
   - 予約当日のリマインダーSMS

3. **予約変更機能**
   - 顧客自身が予約を変更できる機能
   - 予約番号と電話番号で認証

4. **ウェイティングリスト**
   - 満席時のキャンセル待ち機能

5. **コース予約**
   - 特定のメニューやコースの予約

6. **複数店舗対応**
   - 店舗ごとに異なる設定を管理

7. **予約統計**
   - 予約数の推移グラフ
   - 人気時間帯の分析
   - 来店率の計算

## トラブルシューティング

### 予約が表示されない

- データベースが正しく初期化されているか確認
- `T_予約` テーブルが存在するか確認

### 時間枠が表示されない

- 予約設定が保存されているか確認
- 営業時間と最終入店時刻が正しく設定されているか確認

### テーブルが割り当てられない

- テーブル設定が追加されているか確認
- 座席数が予約人数に対して適切か確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHubのIssuesページで報告してください。
