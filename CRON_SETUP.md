# 定期リマインド機能のcron設定手順

## 概要

「星4以上のみ投稿を促す」設定を使用している店舗に対して、30日ごとにリマインドメールを送信します。

## 設定方法

### 1. cronジョブの追加

以下のコマンドでcron設定を編集します：

```bash
crontab -e
```

### 2. 以下の行を追加

```
# 口コミ投稿促進設定リマインド（毎月1日 午前9時に実行）
0 9 1 * * cd /home/ubuntu/survey-system-app && /usr/bin/python3 send_review_prompt_reminders.py >> /var/log/review_prompt_reminders.log 2>&1
```

### 3. 保存して終了

- viエディタの場合：`:wq`
- nanoエディタの場合：`Ctrl+X` → `Y` → `Enter`

## cron設定の説明

| フィールド | 値 | 意味 |
|----------|---|------|
| 分 | 0 | 0分 |
| 時 | 9 | 9時 |
| 日 | 1 | 1日 |
| 月 | * | 毎月 |
| 曜日 | * | 毎曜日 |

**実行タイミング**：毎月1日の午前9時

## ログの確認

リマインド送信のログは以下のファイルに記録されます：

```bash
tail -f /var/log/review_prompt_reminders.log
```

## 手動実行（テスト用）

以下のコマンドで手動実行できます：

```bash
cd /home/ubuntu/survey-system-app
python3 send_review_prompt_reminders.py
```

## メール送信の実装

現在、`send_review_prompt_reminders.py`のメール送信部分はデモ実装です。

実際のメール送信を実装する場合は、以下を参考にしてください：

### SMTPを使用する場合

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to, subject, body):
    """SMTPでメール送信"""
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = "your-email@gmail.com"
    smtp_password = "your-app-password"
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = ', '.join(to)
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
```

### SendGridを使用する場合

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to, subject, body):
    """SendGridでメール送信"""
    message = Mail(
        from_email='noreply@your-domain.com',
        to_emails=to,
        subject=subject,
        plain_text_content=body
    )
    
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    sg.send(message)
```

## トラブルシューティング

### cronが実行されない場合

1. cronサービスが起動しているか確認：
   ```bash
   sudo service cron status
   ```

2. cronログを確認：
   ```bash
   grep CRON /var/log/syslog
   ```

3. Pythonのパスを確認：
   ```bash
   which python3
   ```

### メールが送信されない場合

1. SMTPサーバーの設定を確認
2. ファイアウォールの設定を確認
3. メール送信ログを確認

## セキュリティ上の注意

- SMTPパスワードは環境変数に保存してください
- ログファイルに機密情報が含まれないように注意してください
- メール送信APIキーは適切に管理してください
