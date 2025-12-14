"""
テンプレートレンダリングのテスト
"""
from flask import Flask, render_template
import json

app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

# テストデータ
store = {
    'id': 1,
    'name': 'ホルモンダイニングGON',
    'slug': 'horumon-gon'
}

prizes = [
    {"label": "🎁 特賞", "min": 500, "max": None},
    {"label": "🏆 1等", "min": 250, "max": 499},
    {"label": "🥈 2等", "min": 150, "max": 249},
    {"label": "🥉 3等", "min": 100, "max": 149},
    {"label": "🎊 参加賞", "min": 0, "max": 99}
]

google_review_url = "https://g.page/r/example/review"

print("=== 景品設定テンプレートのテスト ===")
try:
    with app.app_context():
        html = render_template('store_settings/prizes.html', store=store, prizes=prizes)
    print("✅ 景品設定テンプレートのレンダリング成功")
    print(f"HTMLサイズ: {len(html)} bytes")
except Exception as e:
    print(f"❌ 景品設定テンプレートのレンダリング失敗: {e}")

print("\n=== Google口コミURL設定テンプレートのテスト ===")
try:
    with app.app_context():
        html = render_template('store_settings/google_review.html', store=store, google_review_url=google_review_url)
    print("✅ Google口コミURL設定テンプレートのレンダリング成功")
    print(f"HTMLサイズ: {len(html)} bytes")
except Exception as e:
    print(f"❌ Google口コミURL設定テンプレートのレンダリング失敗: {e}")

print("\n=== 店舗設定トップテンプレートのテスト ===")
stores = [store]
try:
    with app.app_context():
        html = render_template('store_settings/index.html', stores=stores)
    print("✅ 店舗設定トップテンプレートのレンダリング成功")
    print(f"HTMLサイズ: {len(html)} bytes")
except Exception as e:
    print(f"❌ 店舗設定トップテンプレートのレンダリング失敗: {e}")
