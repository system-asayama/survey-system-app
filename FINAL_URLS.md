# スロットアプリ - 全ページURL一覧（最終版）

## ベースURL
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer
```

---

## 顧客向けページ（ログイン不要）

### 1. 店舗選択ページ ✅
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/
```
**説明:** 利用可能な店舗一覧を表示。QRコードのランディングページとして使用可能。

---

### 2. アンケートページ ✅
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/survey
```
**説明:** アンケート入力フォーム。評価、来店目的、雰囲気、推薦度、コメントを入力。

---

### 3. 口コミ確認ページ ✅
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/review_confirm
```
**説明:** AI生成の口コミプレビュー。Google口コミへの誘導。
**注意:** アンケート送信後にのみアクセス可能（セッション必要）

---

### 4. スロットページ ✅
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/slot
```
**説明:** 5回スピンのスロットゲーム。合計ポイントに応じて景品を獲得。
**注意:** アンケート送信後にのみアクセス可能（セッション必要）

---

## 管理者向けページ（ログイン必須）

### 5. ログイン選択ページ ✅
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/select_login
```
**説明:** ロール選択画面（システム管理者、テナント管理者、管理者、従業員）

---

### 6. 管理者ログインページ ✅
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin_login
```
**説明:** 店舗管理者用のログイン画面

---

### 7. 店舗設定トップ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin/store_settings/
```
**説明:** 店舗一覧と設定メニュー
**注意:** ログイン必須（管理者・テナント管理者・システム管理者）

---

### 8. ホルモンダイニングGON - 景品設定
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin/store_settings/1/prizes
```
**説明:** 景品の追加・編集・削除。得点範囲、在庫数、有効/無効を管理
**注意:** ログイン必須

---

### 9. ホルモンダイニングGON - Google口コミURL設定
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin/store_settings/1/google_review
```
**説明:** Google口コミURLの設定。アンケート完了後の誘導先を指定
**注意:** ログイン必須

---

## APIエンドポイント

### 10. アンケート送信API ✅
```
POST https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/submit_survey
```

### 11. スロット設定取得API ✅
```
GET https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/config
```

### 12. スロット回転API ✅
```
POST https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/spin
```

### 13. 確率計算API ✅
```
POST https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/calc_prob
```

---

## QRコード推奨URL

### 店舗入口用QRコード
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/survey
```
**用途:** 顧客がスマホでスキャンして直接アンケートページにアクセス

---

## 動作確認済み機能

✅ 店舗選択ページ  
✅ アンケート送信  
✅ スロット5回スピン  
✅ 合計ポイント計算  
✅ 履歴記録  
✅ 管理画面ログイン選択  
✅ テンプレート表示  

---

## 修正完了項目

1. ✅ URLベースの店舗識別機能
2. ✅ 店舗ごとのデータ管理
3. ✅ スロット5回スピン対応
4. ✅ 管理画面blueprintsインポートエラー修正
5. ✅ テンプレートディレクトリ設定

---

## 次のステップ

1. 管理者アカウントでログイン
2. 店舗設定ページで景品とGoogle口コミURLを設定
3. QRコードを生成して店舗に配置
4. 顧客体験のテスト

---

## 技術的な注意事項

- **開発サーバー:** 現在はFlask開発サーバーで動作中
- **本番環境:** Gunicorn等のWSGIサーバーを使用することを推奨
- **データベース:** SQLite（`database/login_auth.db`）を使用
- **セッション管理:** Flask標準のセッション機能を使用
