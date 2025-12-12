# スロットマシン Web アプリ
起動:
```
python -m venv .venv
# Windows:  . .venv/Scripts/activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
```
右上「設定」から各シンボルの重み（確率比）/配当を編集できます。
```
POST /spin {bet} -> { outcome, payout, reason }
```
