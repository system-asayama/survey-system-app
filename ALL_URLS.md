# スロットアプリ - 全ページURL一覧

## ベースURL
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer
```

---

## 顧客向けページ

### 1. 店舗選択ページ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/
```
**説明:** 利用可能な店舗一覧を表示。QRコードのランディングページとして使用可能。

---

### 2. ホルモンダイニングGON - アンケートページ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/survey
```
**説明:** アンケート入力フォーム。評価、来店目的、雰囲気、推薦度、コメントを入力。

---

### 3. ホルモンダイニングGON - 口コミ確認ページ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/review_confirm
```
**説明:** AI生成の口コミプレビュー。Google口コミへの誘導。
**注意:** アンケート送信後にのみアクセス可能（セッション必要）

---

### 4. ホルモンダイニングGON - スロットページ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/slot
```
**説明:** 5回スピンのスロットゲーム。合計ポイントに応じて景品を獲得。
**注意:** アンケート送信後にのみアクセス可能（セッション必要）

---

## 管理者向けページ

### 5. ログインページ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/login
```
**説明:** 管理者ログイン画面。

---

### 6. 管理画面ダッシュボード
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin
```
**説明:** 管理者ダッシュボード。
**注意:** ログイン必須

---

### 7. 店舗設定トップ
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin/store_settings/
```
**説明:** 店舗一覧と設定メニュー。
**注意:** ログイン必須（管理者・テナント管理者・システム管理者）

---

### 8. ホルモンダイニングGON - 景品設定
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin/store_settings/1/prizes
```
**説明:** 景品の追加・編集・削除。得点範囲、在庫数、有効/無効を管理。
**注意:** ログイン必須

---

### 9. ホルモンダイニングGON - Google口コミURL設定
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/admin/store_settings/1/google_review
```
**説明:** Google口コミURLの設定。アンケート完了後の誘導先を指定。
**注意:** ログイン必須

---

## APIエンドポイント

### 10. アンケート送信API
```
POST https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/submit_survey
```
**説明:** アンケートデータを送信。

---

### 11. スロット設定取得API
```
GET https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/config
```
**説明:** 店舗のスロット設定（シンボル、確率、配当）を取得。

---

### 12. スロット回転API
```
POST https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/spin
```
**説明:** 5回分のスロット結果を生成。

---

### 13. 確率計算API
```
POST https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/calc_prob
```
**説明:** スロット確率の計算（デバッグ用）。

---

## QRコード推奨URL

### 店舗入口用QRコード
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/horumon-gon/survey
```
**用途:** 顧客がスマホでスキャンして直接アンケートページにアクセス。

---

## 店舗追加時のURL構造

新しい店舗を追加する場合、以下のパターンでURLが生成されます。

```
/store/<店舗slug>/survey              # アンケート
/store/<店舗slug>/review_confirm      # 口コミ確認
/store/<店舗slug>/slot                # スロット
/admin/store_settings/<店舗ID>/prizes           # 景品設定
/admin/store_settings/<店舗ID>/google_review    # Google口コミURL設定
```

**例:** 新店舗「渋谷店」（slug: shibuya）の場合
```
https://5001-i3gjrskfqpsj8g9tekp41-2228fcf2.manus-asia.computer/store/shibuya/survey
```

---

## 注意事項

1. **セッション管理:** スロットページと口コミ確認ページはアンケート送信後にのみアクセス可能です。
2. **認証:** 管理画面は全てログイン必須です。
3. **店舗ID:** 景品設定とGoogle口コミURL設定のURLには店舗IDを使用します。
4. **開発サーバー:** 現在は開発サーバー（Flask debug mode）で動作しています。本番環境ではWSGIサーバー（Gunicorn等）を使用してください。

---

## テスト用アカウント情報

管理画面にアクセスするには、既存のアカウント情報が必要です。
データベースに登録されている管理者アカウントを使用してください。

```sql
-- 管理者情報を確認
SELECT * FROM T_管理者;
```
