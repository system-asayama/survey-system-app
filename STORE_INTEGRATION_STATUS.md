# 店舗紐付け機能実装状況

## 完了した作業

### 1. データベーススキーマ拡張 ✅
- `T_店舗_アンケート設定` テーブル作成
- `T_店舗_スロット設定` テーブル作成
- `T_店舗_景品設定` テーブル作成
- `T_アンケート回答` テーブル作成
- `T_店舗_Google設定` テーブル作成
- デフォルト設定を既存店舗に挿入

### 2. データベースヘルパー作成 ✅
- `store_db.py` 作成
  - 店舗情報取得関数
  - アンケート設定の保存/取得
  - スロット設定の保存/取得
  - 景品設定の保存/取得
  - Google口コミURL管理
  - アンケート回答保存
  - 統計データ取得

### 3. URLルーティング実装 ✅
- URLベースの店舗識別: `/store/<store_slug>/`
- `url_value_preprocessor` でstore_slugを自動処理
- `require_store` デコレータで店舗存在チェック
- 全ルートを店舗対応に変更:
  - `/store/<store_slug>/survey` - アンケート
  - `/store/<store_slug>/submit_survey` - アンケート送信
  - `/store/<store_slug>/review_confirm` - 口コミ確認
  - `/store/<store_slug>/slot` - スロット
  - `/store/<store_slug>/demo` - デモ
  - `/store/<store_slug>/config` - 設定取得/保存
  - `/store/<store_slug>/spin` - スロット回転

### 4. テンプレート対応 ✅
- `store_select.html` - 店舗選択ページ作成
- `survey.html` - コピー完了
- `review_confirm.html` - コピー完了
- `demo.html` - コピー完了
- `slot.html` - コピー完了

### 5. JavaScript修正 ✅
- `survey.js` - API URLを店舗対応に修正

## 現在の状況
- アプリケーション起動: ✅
- 店舗選択ページ表示: ✅
- アンケートページ表示: ✅
- URL: https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/

## 残りの作業

### 1. slot.htmlのJavaScript修正 🔄
- スロットページ内のAPI呼び出しを店舗対応に修正
- `/config` → `/store/${storeSlug}/config`
- `/spin` → `/store/${storeSlug}/spin`
- `/calc_prob` → `/store/${storeSlug}/calc_prob` (必要に応じて)

### 2. 管理画面統合 🔄
- 店舗管理者が自店舗の設定を編集できる画面
- アンケート設定編集
- スロット設定編集
- 景品設定編集
- Google口コミURL設定
- 統計データ表示

### 3. 動作確認 🔄
- アンケート送信テスト
- スロット動作テスト
- 店舗ごとの設定分離確認
- セッション管理確認

### 4. 複数店舗対応テスト 🔄
- 2つ目の店舗データ追加
- 店舗間のデータ分離確認

## テスト用URL
- 店舗選択: https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/
- ホルモンダイニングGON: https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/

## データベース
- パス: `/home/ubuntu/survey-system-app/database/login_auth.db`
- 既存店舗: ホルモンダイニングGON (slug: horumon-gon, id: 1)
