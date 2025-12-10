# スロットページ完了メッセージのカスタマイズ機能

## 概要

管理者画面からスロットページの緑色バナーに表示されるアンケート完了メッセージを自由に設定できる機能を実装しました。

---

## 実装した機能

### 1. 管理者設定画面の拡張

#### 追加項目
- **スロットページ表示メッセージ**: アンケート完了後、スロットページの緑色バナーに表示されるメッセージ
- **説明文**: 「アンケート完了後、スロットページの緑色バナーに表示されるメッセージです。」

#### デフォルト値
```
アンケートにご協力いただきありがとうございます！スロットをお楽しみください。
```

---

### 2. データ保存

#### ファイル: `data/settings.json`
```json
{
  "survey_complete_message": "ご来店ありがとうございます！アンケートに回答いただいた感謝を込めて、スロットゲームをプレゼント🎁",
  "google_review_url": ""
}
```

#### 保存タイミング
- 管理者が設定画面で「保存」ボタンをクリックした時

---

### 3. スロットページでの動的表示

#### 変更前（固定メッセージ）
```html
<div class="alert alert-success">
    ✓ アンケートにご協力いただきありがとうございます！スロットをお楽しみください。
</div>
```

#### 変更後（動的メッセージ）
```html
<div class="alert alert-success">
    ✓ {{ survey_complete_message }}
</div>
```

#### テンプレート変数
- `survey_complete_message`: 設定ファイルから読み込まれたメッセージ

---

## 使用方法

### 管理者側

1. **ログイン**
   - URL: `/admin/login`
   - 店舗コード: `default`
   - ログインID: `admin`
   - パスワード: `admin123`

2. **設定画面へアクセス**
   - ダッシュボード → 「⚙️ 設定」ボタンをクリック
   - または直接 `/admin/settings` にアクセス

3. **メッセージを編集**
   - 「スロットページ表示メッセージ」フィールドに任意のメッセージを入力
   - 絵文字やHTMLタグも使用可能

4. **保存**
   - 「保存」ボタンをクリック
   - 「設定を更新しました」の成功メッセージが表示される

5. **確認**
   - スロットページ (`/slot`) にアクセスして、緑色バナーのメッセージを確認

---

### ユーザー側

1. **アンケート回答**
   - `/survey` でアンケートに回答

2. **スロットページへ遷移**
   - アンケート送信後、自動的にスロットページへリダイレクト

3. **カスタムメッセージの表示**
   - 緑色のバナーに管理者が設定したメッセージが表示される

---

## メッセージのカスタマイズ例

### 例1: 感謝のメッセージ
```
ご来店ありがとうございます！アンケートに回答いただいた感謝を込めて、スロットゲームをプレゼント🎁
```

### 例2: キャンペーン告知
```
アンケートにご協力ありがとうございました！今なら当たりが出たら次回10%オフ！🎉
```

### 例3: 季節のメッセージ
```
🎄 クリスマスキャンペーン実施中！アンケート回答でスロットに挑戦して豪華景品をゲット！
```

### 例4: シンプルなメッセージ
```
アンケートありがとうございます！スロットをお楽しみください。
```

---

## 技術的な詳細

### バックエンド（app.py）

#### 設定の読み込み
```python
# グローバル変数
survey_complete_message = "アンケートにご協力いただきありがとうございます！スロットをお楽しみください。"

def load_settings():
    global survey_complete_message
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            survey_complete_message = settings.get('survey_complete_message', survey_complete_message)
```

#### スロットページでの渡し方
```python
@app.route('/slot')
def slot_page():
    # ... 他のロジック ...
    return render_template('slot.html', 
                         survey_complete_message=survey_complete_message)
```

#### 設定の保存
```python
@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    global survey_complete_message
    
    if request.method == 'POST':
        survey_complete_message = request.form.get('survey_complete_message', survey_complete_message)
        
        settings = {
            'survey_complete_message': survey_complete_message,
            'google_review_url': request.form.get('google_review_url', '')
        }
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
```

---

### フロントエンド（templates/slot.html）

#### メッセージ表示部分
```html
{% if session.get('survey_completed') %}
<div class="alert alert-success" role="alert">
    ✓ {{ survey_complete_message }}
</div>
{% endif %}
```

---

## テスト結果

### ✅ 設定画面
- メッセージ入力フィールドが正常に表示
- デフォルト値が正しく読み込まれる
- 保存ボタンで設定が正常に保存される
- 成功メッセージが表示される

### ✅ スロットページ
- 設定したメッセージが緑色バナーに表示される
- 絵文字が正しく表示される
- メッセージが長い場合も適切に折り返される

### ✅ データ永続化
- `data/settings.json`に正しく保存される
- アプリケーション再起動後も設定が保持される

---

## ファイル構成

```
survey-system-app/
├── app.py                          # メイン: 設定読み込み・保存ロジック追加
├── data/
│   └── settings.json               # 新規: 設定データ保存
├── templates/
│   ├── admin_settings.html         # 更新: メッセージ設定フィールド追加
│   └── slot.html                   # 更新: 動的メッセージ表示
└── CUSTOM_MESSAGE_FEATURE.md       # このドキュメント
```

---

## GitHubリポジトリ

**https://github.com/system-asayama/survey-system-app**

**最新コミット:**
- `c8f22af` - 管理者画面からスロットページのアンケート完了メッセージを設定可能に

---

## まとめ

この機能により、管理者は：
- ✅ スロットページのメッセージを自由にカスタマイズ可能
- ✅ 季節やキャンペーンに応じてメッセージを変更可能
- ✅ 店舗のブランディングに合わせたメッセージを設定可能
- ✅ コードを触らずに簡単に変更可能

顧客体験をパーソナライズし、エンゲージメントを向上させることができます。
