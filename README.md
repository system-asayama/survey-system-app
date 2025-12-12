# Survey System App - マルチテナント対応アンケート＆スロットシステム

アンケート収集、AI口コミ生成、スロットゲーム機能を備えたマルチテナント対応Webアプリケーション

## 主な機能

### 1. アンケートシステム
- 📝 カスタマイズ可能な質問項目
- ⭐ 星評価、ラジオボタン、チェックボックス、自由記述
- 🤖 AI自動口コミ生成（OpenAI API）
- 📊 回答データの収集・分析

### 2. スロットゲーム
- 🎰 5回スピン方式
- 🎨 カスタマイズ可能なシンボルと配当
- 📈 履歴記録と統計
- 🎵 効果音とアニメーション

### 3. マルチテナント認証
- 👤 4つの役割（システム管理者、テナント管理者、管理者、従業員）
- 🏢 テナント（店舗・拠点）管理
- 🔐 セッションベース認証
- 🔑 パスワードハッシュ化

### 4. 管理画面
- 📊 ダッシュボード（統計情報）
- ⚙️ 設定管理
- 📝 アンケート編集
- 📥 CSVエクスポート

## 技術スタック

- **Backend:** Flask 3.1.0
- **Database:** SQLite3
- **ORM:** SQLAlchemy
- **AI:** OpenAI API (gpt-4.1-mini)
- **Frontend:** Vanilla JavaScript, Custom CSS
- **Template Engine:** Jinja2

## セットアップ

### 必要要件
- Python 3.11+
- pip3

### インストール

```bash
# リポジトリのクローン
cd /home/ubuntu/survey-system-app

# 依存関係のインストール
pip3 install -r requirements.txt

# アプリケーションの起動
python3.11 run.py
```

アプリケーションは `http://localhost:5000` で起動します。

### 環境変数

```bash
# OpenAI API（Manus Proxy経由）
export OPENAI_API_KEY="your-api-key"

# Flaskセッション暗号化キー（自動生成）
# SECRET_KEYは自動的に生成されます
```

## 使い方

### 初回セットアップ

1. **システム管理者アカウントの作成**
   - `/first_admin_setup` にアクセス
   - sysadminアカウントを作成

2. **テナントの作成**
   - システム管理者でログイン
   - テナント管理からテナントを作成

3. **管理者アカウントの設定**
   - 既存の管理画面 (`/admin/login`) でログイン
   - 店舗コード: `default`
   - ログインID: `admin`
   - パスワード: `admin123`

### アンケートの利用

1. `/survey` にアクセス
2. アンケートに回答
3. AI生成口コミを確認
4. スロットゲームをプレイ

### 管理画面の利用

1. `/admin/login` にアクセス
2. 認証情報を入力
3. ダッシュボードで統計確認
4. 設定やアンケート編集

## ファイル構造

```
survey-system-app/
├── app/
│   ├── __init__.py              # アプリケーション初期化
│   ├── models.py                # データベースモデル
│   ├── blueprints/              # Blueprint（機能モジュール）
│   │   ├── auth.py              # 基本認証
│   │   ├── system_admin.py      # システム管理者
│   │   ├── tenant_admin.py      # テナント管理者
│   │   ├── employee.py          # 従業員
│   │   ├── survey.py            # アンケート機能
│   │   ├── slot.py              # スロット機能
│   │   └── survey_admin.py      # 管理画面
│   ├── utils/                   # ユーティリティ
│   │   ├── db.py                # データベース管理
│   │   ├── slot_logic.py        # スロット計算
│   │   ├── config.py            # 設定管理
│   │   └── admin_auth.py        # 管理画面認証
│   ├── templates/               # HTMLテンプレート
│   └── static/                  # 静的ファイル（CSS, JS）
├── run.py                       # エントリーポイント
├── requirements.txt             # Python依存関係
├── README.md                    # 本ファイル
├── INTEGRATION_REPORT.md        # 統合レポート
└── MIGRATION_STATUS.md          # 移行ステータス
```

## API エンドポイント

### 公開エンドポイント
- `GET /survey` - アンケートページ
- `POST /submit_survey` - アンケート送信
- `GET /review_confirm` - 口コミ確認
- `GET /slot` - スロットページ
- `POST /api/spin` - スロット実行
- `GET /api/config` - スロット設定取得

### 認証が必要なエンドポイント
- `GET /admin/login` - 管理画面ログイン
- `POST /admin/login` - ログイン処理
- `GET /admin` - ダッシュボード
- `GET /admin/settings` - 設定
- `GET /admin/survey_editor` - アンケート編集
- `GET /admin/responses` - 回答一覧
- `GET /admin/export_csv` - CSVエクスポート

### システム管理者エンドポイント
- `GET /first_admin_setup` - 初回セットアップ
- `GET /system_admin/login` - システム管理者ログイン
- `GET /system_admin/dashboard` - システム管理者ダッシュボード
- `GET /system_admin/tenants` - テナント管理

## デフォルトアカウント

### システム管理者
- **URL:** `/system_admin/login`
- **ユーザーID:** sysadmin
- **パスワード:** Admin@123

### 管理者
- **URL:** `/admin/login`
- **店舗コード:** default
- **ログインID:** admin
- **パスワード:** admin123

## セキュリティ

- ✅ パスワードハッシュ化（Werkzeug Security）
- ✅ セッション管理
- ✅ 認証デコレータによるアクセス制御
- ✅ CSRF対策（Flaskデフォルト）

### 推奨事項
- HTTPSの使用
- セッションタイムアウトの設定
- パスワードポリシーの強化
- レート制限の実装

## トラブルシューティング

### データベースエラー
```bash
# データベースを再初期化
rm -f instance/survey.db
python3.11 run.py
```

### ポート競合
```bash
# 別のポートで起動
PORT=5001 python3.11 run.py
```

### OpenAI APIエラー
- `OPENAI_API_KEY` 環境変数が設定されているか確認
- API使用量の制限を確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHubのIssuesページで報告してください。

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずIssueを開いて変更内容を議論してください。

---

**バージョン:** 1.0  
**最終更新:** 2025年12月12日
