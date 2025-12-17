# バグ分析レポート: アンケート☆3以下で「店舗が見つかりません」エラー

## 1. 問題の概要

アンケートで☆3以下の評価を回答した際に、スロットページへ遷移すると「設定の読み込みに失敗しました: 店舗が見つかりません」というエラーが表示される。

### エラーログの証拠

```
127.0.0.1 - - [16/Dec/2025 17:36:48] "GET /slot?store_slug=horumon-gon HTTP/1.1" 200 -
127.0.0.1 - - [16/Dec/2025 17:36:48] "GET /store/undefined/config HTTP/1.1" 404 -
127.0.0.1 - - [16/Dec/2025 17:36:51] "POST /store/undefined/spin HTTP/1.1" 404 -
```

**注目点**: `/slot?store_slug=horumon-gon` にアクセスした後、JavaScriptが `/store/undefined/config` にリクエストを送信している。

---

## 2. 原因分析

### 2.1 ルーティングの問題

**app.py** には2つの `slot_page` ルートが存在する：

| ルート | 定義場所 | URL形式 | store_slugの渡し方 |
|--------|----------|---------|-------------------|
| `slot_page` | app.py (534行目) | `/store/<store_slug>/slot` | URLパスから取得、テンプレートに渡す |
| `slot.slot_page` | app/blueprints/slot.py (26行目) | `/slot` | クエリパラメータで受け取り |

### 2.2 リダイレクト先の不整合

**app.py 505行目** のアンケート送信処理（☆3以下の場合）：

```python
if rating <= 3:
    return jsonify({
        "ok": True, 
        "message": "貴重なご意見をありがとうございます。...",
        "rating": rating,
        "redirect_url": url_for('slot.slot_page', store_slug=g.store_slug)
    })
```

`url_for('slot.slot_page', store_slug='horumon-gon')` は `/slot?store_slug=horumon-gon` を生成する。

### 2.3 JavaScriptの問題

**app/static/slot.js** の `loadConfig()` 関数（423-449行目）：

```javascript
async function loadConfig(){
  try {
    const storeSlug = window.location.pathname.split('/')[2];  // ← 問題箇所
    const cfg = await fetchJSON(`/store/${storeSlug}/config`);
    ...
  } catch (e) {
    alert('設定の読み込みに失敗しました: ' + e.message);
    throw e;
  }
}
```

**問題点**: 
- URLが `/slot?store_slug=horumon-gon` の場合、`pathname.split('/')[2]` は `undefined` を返す
- その結果、`/store/undefined/config` にリクエストが送信され、404エラーが発生

### 2.4 テンプレートの問題

**app/templates/slot.html** の171行目：

```html
<script>
  window.STORE_SLUG = "{{ store_slug or '' }}";
</script>
```

**app/blueprints/slot.py** の `slot_page()` 関数は `store_slug` をテンプレートに渡しているが、**app/static/slot.js** はこの `window.STORE_SLUG` を使用していない。

---

## 3. 根本原因のまとめ

| 要素 | 期待される動作 | 実際の動作 |
|------|---------------|-----------|
| リダイレクトURL | `/store/horumon-gon/slot` | `/slot?store_slug=horumon-gon` |
| slot.js | `window.STORE_SLUG` を使用 | `pathname.split('/')[2]` を使用 |
| 結果 | 正常に設定を読み込む | `undefined` で404エラー |

**2つのslot.jsファイルの違い**:
- `static/slot.js`: `window.STORE_SLUG` を優先的に使用（正しい実装）
- `app/static/slot.js`: `pathname.split('/')[2]` のみ使用（バグあり）

---

## 4. 解決策

### 解決策A: リダイレクト先を修正（推奨）

**app.py 505行目** を修正：

```python
# 修正前
"redirect_url": url_for('slot.slot_page', store_slug=g.store_slug)

# 修正後
"redirect_url": url_for('slot_page', store_slug=g.store_slug)
```

これにより `/store/horumon-gon/slot` にリダイレクトされ、既存のJavaScriptコードが正しく動作する。

### 解決策B: app/static/slot.jsを修正

**app/static/slot.js** の `loadConfig()` 関数を修正：

```javascript
async function loadConfig(){
  try {
    // store_slugを取得（グローバル変数 > URLパス > クエリパラメータ）
    let storeSlug = window.STORE_SLUG;
    if (!storeSlug) {
      const pathParts = window.location.pathname.split('/');
      storeSlug = pathParts[2]; // /store/{slug}/slot の形式を想定
    }
    if (!storeSlug) {
      const urlParams = new URLSearchParams(window.location.search);
      storeSlug = urlParams.get('store_slug');
    }
    const cfg = await fetchJSON(`/store/${storeSlug}/config`);
    ...
  }
}
```

### 解決策C: 両方のslot.jsを統一

`static/slot.js` と `app/static/slot.js` の内容を統一し、どちらか一方を削除する。

---

## 5. 推奨される修正

**最も簡単で安全な修正は解決策A**です。

### 修正ファイル: app.py

```python
# 505行目を修正
if rating <= 3:
    return jsonify({
        "ok": True, 
        "message": "貴重なご意見をありがとうございます。社内で改善に活用させていただきます。",
        "rating": rating,
        "redirect_url": url_for('slot_page', store_slug=g.store_slug)  # 'slot.slot_page' → 'slot_page'
    })
```

この修正により：
- リダイレクト先が `/store/horumon-gon/slot` になる
- 既存の `app/static/slot.js` の `pathname.split('/')[2]` が正しく `horumon-gon` を取得できる
- エラーが解消される

---

## 6. 追加の推奨事項

1. **slot.jsファイルの統一**: 2つの異なるバージョンが存在することで混乱が生じている。どちらかに統一することを推奨。

2. **Blueprint構成の見直し**: `slot.slot_page` と `slot_page` の2つのルートが存在し、混乱の原因となっている。不要なルートを削除することを推奨。

3. **テスト追加**: ☆3以下のアンケート回答フローのE2Eテストを追加することを推奨。
