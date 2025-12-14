import sys
sys.path.insert(0, '/home/ubuntu/survey-system-app')

# app.pyを読み込み
exec(open('app.py').read())

# ポート5003で起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False, use_reloader=False)
