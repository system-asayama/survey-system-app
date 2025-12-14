# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from flask import Flask, jsonify, request, render_template, send_from_directory, session, redirect, url_for, flash, g
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import os, json, secrets, time, math
from datetime import datetime
from decimal import Decimal, getcontext
from openai import OpenAI
from optimizer import optimize_symbol_probabilities as _optimize_symbol_probabilities
import store_db

getcontext().prec = 28  # 小数演算の安全側

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")

app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# OpenAI クライアント初期化
openai_client = OpenAI()

# ===== モデル =====
@dataclass
class Symbol:
    id: str
    label: str
    payout_3: float
    color: str | None = None
    prob: float = 0.0  # 保存時は [%]
    is_reach: bool = False  # リーチ専用シンボルかどうか
    reach_symbol: str | None = None  # リーチ時に表示する元のシンボルID

@dataclass
class Config:
    symbols: List[Symbol]
    reels: int = 3
    base_bet: int = 1
    expected_total_5: float = 2500.0
    miss_probability: float = 0.0  # ハズレ確率 [%]
    target_probabilities: Dict[str, float] | None = None  # 目標確率設定 {"500-2500": 1.0, ...}

# ===== 店舗識別ミドルウェア =====
@app.url_value_preprocessor
def pull_store_slug(endpoint, values):
    """URLから店舗slugを取得してgに保存"""
    if values and 'store_slug' in values:
        g.store_slug = values.pop('store_slug')
        store = store_db.get_store_by_slug(g.store_slug)
        if store:
            g.store = store
            g.store_id = store['id']
        else:
            g.store = None
            g.store_id = None
    else:
        g.store_slug = None
        g.store = None
        g.store_id = None

def require_store(f):
    """店舗が必須のルートで使用するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.store:
            return "店舗が見つかりません", 404
        return f(*args, **kwargs)
    return decorated_function

# ===== ユーティリティ =====
def _choice_by_prob(symbols: List[Symbol]) -> Symbol:
    buckets = []
    acc = 0
    for s in symbols:
        w = max(0, int(round(float(s.prob) * 100)))
        acc += w
        buckets.append((acc, s))
    if acc <= 0:
        return symbols[-1]
    r = secrets.randbelow(acc)
    for edge, s in buckets:
        if r < edge:
            return s
    return symbols[-1]

# --- 期待値関連 ---
def _expected_total5_from_inverse(payouts: List[float]) -> float:
    vals = [max(1e-9, float(v)) for v in payouts if float(v) > 0]
    if not vals:
        return 0.0
    n = len(vals)
    hm = n / sum(1.0 / v for v in vals)
    return 5.0 * hm

def _recalc_probs_inverse_and_expected(cfg: Config) -> None:
    payouts = [max(1e-9, float(s.payout_3)) for s in cfg.symbols]
    inv = [1.0 / p for p in payouts]
    S = sum(inv) or 1.0
    for s, v in zip(cfg.symbols, inv):
        s.prob = float(v / S * 100.0)
    expected_e1 = sum(p * (v / S) for p, v in zip(payouts, inv))
    cfg.expected_total_5 = float(expected_e1 * 5.0)

def _solve_probs_for_target_expectation(payouts: List[float], target_e1: float) -> List[float]:
    vs = [float(v) for v in payouts if float(v) >= 0]
    n = len(vs)
    if n == 0:
        return []
    vmin, vmax = min(vs), max(vs)
    if target_e1 <= vmin + 1e-12:
        return [1.0 if v == vmin else 0.0 for v in vs]
    if target_e1 >= vmax - 1e-12:
        return [1.0 if v == vmax else 0.0 for v in vs]

    def e_for_beta(beta: float) -> float:
        ws = [math.exp(beta * v) for v in vs]
        Z = sum(ws)
        ps = [w / Z for w in ws]
        return sum(p * v for p, v in zip(ps, vs))

    lo, hi = -1.0, 1.0
    for _ in range(60):
        elo, ehi = e_for_beta(lo), e_for_beta(hi)
        if elo > target_e1:
            lo *= 2
            continue
        if ehi < target_e1:
            hi *= 2
            continue
        break
    for _ in range(80):
        mid = (lo + hi) / 2.0
        em = e_for_beta(mid)
        if em < target_e1:
            lo = mid
        else:
            hi = mid
    beta = (lo + hi) / 2.0
    ws = [math.exp(beta * v) for v in vs]
    Z = sum(ws)
    return [w / Z for w in ws]

# --- DP確率 ---
def _decimal_scale(values: List[float]) -> int:
    max_dec = 0
    for v in values:
        s = f"{Decimal(v):f}"
        if "." in s:
            d = len(s.split(".")[1].rstrip("0"))
            if d > max_dec:
                max_dec = d
    return 10 ** max_dec

def _prob_total_ge(symbols: List[Symbol], spins: int, threshold: float) -> float:
    vs = [float(s.payout_3) for s in symbols]
    ps = [float(s.prob) / 100.0 for s in symbols]
    if not vs or not ps:
        return 0.0
    S = sum(ps) or 1.0
    ps = [p / S for p in ps]
    scale = _decimal_scale(vs + [threshold])
    ivs = [int(round(v * scale)) for v in vs]
    thr = int(round(threshold * scale))
    max_sum = spins * max(ivs)
    pmf = [0.0] * (max_sum + 1)
    pmf[0] = 1.0
    for _ in range(spins):
        nxt = [0.0] * (max_sum + 1)
        for ssum, pcur in enumerate(pmf):
            if pcur == 0.0:
                continue
            for vi, pi in zip(ivs, ps):
                nxt[ssum + vi] += pcur * pi
        pmf = nxt
    return float(sum(pmf[thr:]))

def _prob_total_le(symbols: List[Symbol], spins: int, threshold: float) -> float:
    """spins 回の合計配当が threshold 以下となる確率"""
    vs = [float(s.payout_3) for s in symbols]
    ps = [float(s.prob) / 100.0 for s in symbols]
    if not vs or not ps:
        return 0.0
    S = sum(ps) or 1.0
    ps = [p / S for p in ps]
    scale = _decimal_scale(vs + [threshold])
    ivs = [int(round(v * scale)) for v in vs]
    thr = int(round(threshold * scale))
    max_sum = spins * max(ivs)
    pmf = [0.0] * (max_sum + 1)
    pmf[0] = 1.0
    for _ in range(spins):
        nxt = [0.0] * (max_sum + 1)
        for ssum, pcur in enumerate(pmf):
            if pcur == 0.0:
                continue
            for vi, pi in zip(ivs, ps):
                nxt[ssum + vi] += pcur * pi
        pmf = nxt
    return float(sum(pmf[:thr + 1]))

def _generate_review_text(survey_data):
    """
    アンケートデータからAIを使って口コミ投稿文を生成
    """
    rating = survey_data.get('rating', 3)
    visit_purpose = survey_data.get('visit_purpose', '')
    atmosphere = ', '.join(survey_data.get('atmosphere', []))
    recommend = survey_data.get('recommend', '')
    comment = survey_data.get('comment', '')
    
    # プロンプト作成
    prompt = f"""以下のアンケート回答から、自然で読みやすいお店の口コミ投稿文を日本語で作成してください。

【アンケート内容】
- 総合評価: {rating}つ星
- 訪問目的: {visit_purpose}
- お店の雰囲気: {atmosphere}
- おすすめ度: {recommend}
- 自由コメント: {comment if comment else 'なし'}

【要件】
- 200文字程度で簡潔にまとめる
- 自然な口語体で書く
- 具体的な体験を含める
- {rating}つ星の評価に相応しいトーンで書く
- 「です・ます」調で統一する

口コミ投稿文:"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "あなたは自然で読みやすい口コミ投稿文を作成する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # エラー時はデフォルトの文章を返す
        return f"{visit_purpose}で訪問しました。{atmosphere}な雰囲気で、{recommend}と思います。{comment}"

# ===== ルート =====
@app.get("/")
def index():
    """トップページ - 店舗選択またはリダイレクト"""
    return render_template("store_select.html")

@app.get("/store/<store_slug>/")
@require_store
def store_index():
    """店舗トップ - アンケートへリダイレクト"""
    # アンケート未回答の場合はアンケートページへ
    if not session.get(f'survey_completed_{g.store_id}'):
        return redirect(url_for('survey', store_slug=g.store_slug))
    return redirect(url_for('slot_page', store_slug=g.store_slug))

@app.get("/store/<store_slug>/survey")
@require_store
def survey():
    """アンケートページ"""
    survey_config = store_db.get_survey_config(g.store_id)
    return render_template("survey.html", 
                         store=g.store,
                         survey_config=survey_config)

@app.post("/store/<store_slug>/submit_survey")
@require_store
def submit_survey():
    body = request.get_json(silent=True) or {}
    
    # バリデーション
    required_fields = ['rating', 'visit_purpose', 'atmosphere', 'recommend']
    for field in required_fields:
        if field not in body or not body[field]:
            return jsonify({"ok": False, "error": f"{field}は必須項目です"}), 400
    
    rating = body.get('rating', 3)
    
    # 星4以上の場合のみAI投稿文を生成
    if rating >= 4:
        generated_review = _generate_review_text(body)
        body['generated_review'] = generated_review
    else:
        generated_review = ''
        body['generated_review'] = ''
    
    # アンケートデータを保存
    store_db.save_survey_response(g.store_id, body)
    
    # セッションにアンケート完了フラグと評価を設定
    session[f'survey_completed_{g.store_id}'] = True
    session[f'survey_timestamp_{g.store_id}'] = datetime.now().isoformat()
    session[f'survey_rating_{g.store_id}'] = rating
    session[f'generated_review_{g.store_id}'] = generated_review
    
    # 星3以下の場合は直接スロットページへ
    if rating <= 3:
        return jsonify({
            "ok": True, 
            "message": "貴重なご意見をありがとうございます。社内で改善に活用させていただきます。",
            "rating": rating,
            "redirect_url": url_for('slot_page', store_slug=store_slug)
        })
    
    # 星4以上の場合は口コミ確認ページへ
    return jsonify({
        "ok": True, 
        "message": "アンケートを受け付けました",
        "rating": rating,
        "generated_review": generated_review,
        "redirect_url": url_for('review_confirm', store_slug=g.store_slug)
    })

@app.get("/store/<store_slug>/review_confirm")
@require_store
def review_confirm():
    """口コミ確認ページ"""
    generated_review = session.get(f'generated_review_{g.store_id}', '')
    google_review_url = store_db.get_google_review_url(g.store_id)
    rating = session.get(f'survey_rating_{g.store_id}', 0)
    
    return render_template("review_confirm.html",
        store=g.store,
        generated_review=generated_review,
        google_review_url=google_review_url,
        rating=rating
    )

@app.get("/store/<store_slug>/slot")
@require_store
def slot_page():
    """スロットページ"""
    # アンケート未回答の場合はアンケートページへリダイレクト
    if not session.get(f'survey_completed_{g.store_id}'):
        return redirect(url_for('survey', store_slug=g.store_slug))
    
    # 店舗の景品データを読み込み
    prizes = store_db.get_prizes_config(g.store_id)
    survey_complete_message = "アンケートにご協力いただきありがとうございます！スロットをお楽しみください。"
    
    return render_template("slot.html",
        store=g.store,
        survey_complete_message=survey_complete_message,
        prizes=prizes
    )

@app.get("/store/<store_slug>/demo")
@require_store
def demo():
    """デモページ"""
    prizes = store_db.get_prizes_config(g.store_id)
    return render_template("demo.html", store=g.store, prizes=prizes)

@app.post("/store/<store_slug>/reset_survey")
@require_store
def reset_survey():
    """アンケートをリセットして再度回答できるようにする"""
    session.pop(f'survey_completed_{g.store_id}', None)
    session.pop(f'survey_timestamp_{g.store_id}', None)
    session.pop(f'survey_rating_{g.store_id}', None)
    session.pop(f'generated_review_{g.store_id}', None)
    return jsonify({"ok": True, "message": "アンケートをリセットしました"})

@app.get("/store/<store_slug>/config")
@require_store
def get_config():
    """スロット設定を取得"""
    cfg_dict = store_db.get_slot_config(g.store_id)
    return jsonify(cfg_dict)

@app.post("/store/<store_slug>/config")
@require_store
def set_config():
    """スロット設定を保存"""
    body = request.get_json(silent=True) or {}
    
    # 設定を保存
    store_db.save_slot_config(g.store_id, body)
    
    return jsonify({"ok": True})

@app.post("/store/<store_slug>/spin")
@require_store
def spin():
    """スロット回転（5回分）"""
    cfg_dict = store_db.get_slot_config(g.store_id)
    symbols = [Symbol(**s) for s in cfg_dict["symbols"]]
    reels = cfg_dict.get("reels", 3)
    
    # 5回分のスピン結果を生成
    spins = []
    for _ in range(5):
        # 確率に基づいてシンボルを選択
        result = [_choice_by_prob(symbols) for _ in range(reels)]
        
        # 全て同じシンボルかチェック
        matched = len(set(s.id for s in result)) == 1
        if matched:
            payout = result[0].payout_3
            symbol = {"id": result[0].id, "label": result[0].label}
        else:
            payout = 0
            symbol = None
        
        # リーチ判定（最初の2つが同じ）
        is_reach = result[0].id == result[1].id and not matched
        
        spins.append({
            "reels": [{"id": s.id, "label": s.label} for s in result],
            "payout": payout,
            "matched": matched,
            "is_reach": is_reach,
            "symbol": symbol
        })
    
    return jsonify({
        "ok": True,
        "spins": spins
    })

# ===== 静的ファイル =====
@app.get("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

# ===== 管理画面用のインポート =====
# 既存の管理画面blueprintをインポート
try:
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.system_admin import bp as system_admin_bp
    from app.blueprints.tenant_admin import bp as tenant_admin_bp
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.employee import bp as employee_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_admin_bp)
    app.register_blueprint(tenant_admin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    
    print("✅ 管理画面blueprints登録完了")
except Exception as e:
    print(f"⚠️ 管理画面blueprints登録エラー: {e}")
    import traceback
    traceback.print_exc()

# ===== 店舗設定ルート =====
try:
    from store_settings_routes import register_store_settings_routes
    register_store_settings_routes(app)
    print("✅ 店舗設定ルート登録完了")
except Exception as e:
    print(f"⚠️ 店舗設定ルート登録エラー: {e}")

# ===== 店舗スロット設定ルート =====
try:
    from store_slot_settings_routes import register_store_slot_settings_routes
    register_store_slot_settings_routes(app)
    print("✅ 店舗スロット設定ルート登録完了")
except Exception as e:
    print(f"⚠️ 店舗スロット設定ルート登録エラー: {e}")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
