# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from flask import Flask, jsonify, request, render_template, send_from_directory, session, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import os, json, secrets, time, math
from datetime import datetime
from decimal import Decimal, getcontext
from openai import OpenAI

getcontext().prec = 28  # 小数演算の安全側

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
SURVEY_DATA_PATH = os.path.join(DATA_DIR, "survey_responses.json")

# Google口コミのURL（環境変数またはデフォルト値）
# 実際のお店のPlace IDを設定してください
# 例: https://search.google.com/local/writereview?placeid=ChIJN1t_tDeuEmsRUsoyG83frY4
GOOGLE_REVIEW_URL = os.environ.get('GOOGLE_REVIEW_URL', '#')

app = Flask(__name__)
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

@dataclass
class Config:
    symbols: List[Symbol]
    reels: int = 3
    base_bet: int = 1
    expected_total_5: float = 2500.0

# ===== ユーティリティ =====
def _default_config() -> Config:
    defaults = [
        {"id": "seven", "label": "7", "payout_3": 100, "color": "#ff0000"},
        {"id": "bell", "label": "🔔", "payout_3": 50, "color": "#fbbf24"},
        {"id": "bar", "label": "BAR", "payout_3": 25, "color": "#ffffff"},
        {"id": "grape", "label": "🍇", "payout_3": 20, "color": "#7c3aed"},
        {"id": "cherry", "label": "🍒", "payout_3": 12.5, "color": "#ef4444"},
        {"id": "lemon", "label": "🍋", "payout_3": 12.5, "color": "#fde047"},
    ]
    cfg = Config(symbols=[Symbol(**d) for d in defaults])
    _recalc_probs_inverse_and_expected(cfg)
    _save_config(cfg)
    return cfg

def _load_config() -> Config:
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        return _default_config()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    syms = [Symbol(**s) for s in raw["symbols"]]
    return Config(
        symbols=syms,
        reels=raw.get("reels", 3),
        base_bet=raw.get("base_bet", 1),
        expected_total_5=raw.get("expected_total_5", 2500.0),
    )

def _save_config(cfg: Config) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = asdict(cfg)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

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
    cfg.expected_total_5 = _expected_total5_from_inverse(payouts)

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

# ===== アンケートデータ管理 =====
def _load_survey_responses():
    if not os.path.exists(SURVEY_DATA_PATH):
        return []
    with open(SURVEY_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_survey_response(response_data):
    os.makedirs(DATA_DIR, exist_ok=True)
    responses = _load_survey_responses()
    response_data['timestamp'] = datetime.now().isoformat()
    response_data['id'] = len(responses) + 1
    responses.append(response_data)
    with open(SURVEY_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)

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
    # アンケート未回答の場合はアンケートページへ
    if not session.get('survey_completed'):
        return redirect(url_for('survey'))
    return redirect(url_for('slot_page'))

@app.get("/survey")
def survey():
    return render_template("survey.html")

@app.get("/review_confirm")
def review_confirm():
    # アンケート未回答の場合はアンケートページへ
    if not session.get('survey_completed'):
        return redirect(url_for('survey'))
    
    rating = session.get('survey_rating', 3)
    generated_review = session.get('generated_review', '')
    
    return render_template(
        "review_confirm.html",
        rating=rating,
        generated_review=generated_review,
        google_review_url=GOOGLE_REVIEW_URL
    )

@app.get("/slot")
def slot_page():
    # アンケート未回答の場合はアンケートページへリダイレクト
    if not session.get('survey_completed'):
        return redirect(url_for('survey'))
    return render_template("slot.html")

@app.post("/reset_survey")
def reset_survey():
    """アンケートをリセットして再度回答できるようにする"""
    session.pop('survey_completed', None)
    session.pop('survey_timestamp', None)
    session.pop('survey_rating', None)
    session.pop('generated_review', None)
    return jsonify({"ok": True, "message": "アンケートをリセットしました"})

@app.post("/submit_survey")
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
        # 星3以下の場合はAI生成をスキップ
        generated_review = ''
        body['generated_review'] = ''
    
    # アンケートデータを保存
    _save_survey_response(body)
    
    # セッションにアンケート完了フラグと評価を設定
    session['survey_completed'] = True
    session['survey_timestamp'] = datetime.now().isoformat()
    session['survey_rating'] = rating
    session['generated_review'] = generated_review
    
    # 星3以下の場合は直接スロットページへ
    if rating <= 3:
        return jsonify({
            "ok": True, 
            "message": "貴重なご意見をありがとうございます。社内で改善に活用させていただきます。",
            "rating": rating,
            "redirect_url": url_for('slot_page')
        })
    
    # 星4以上の場合は口コミ確認ページへ
    return jsonify({
        "ok": True, 
        "message": "アンケートを受け付けました",
        "rating": rating,
        "generated_review": generated_review,
        "redirect_url": url_for('review_confirm')
    })

@app.get("/config")
def get_config():
    cfg = _load_config()
    return jsonify({
        "symbols": [asdict(s) for s in cfg.symbols],
        "reels": cfg.reels,
        "base_bet": cfg.base_bet,
        "expected_total_5": cfg.expected_total_5
    })

@app.post("/config")
def set_config():
    body = request.get_json(silent=True) or {}
    reels = int(body.get("reels", 3))
    base_bet = int(body.get("base_bet", 1))
    symbols_in = body.get("symbols", [])
    if not isinstance(symbols_in, list) or len(symbols_in) == 0:
        return jsonify({"ok": False, "error": "symbolsを1件以上送信してください"}), 400
    parsed = [Symbol(**s) for s in symbols_in]
    cfg = Config(symbols=parsed, reels=reels, base_bet=base_bet)
    target_total5 = body.get("target_expected_total_5", None)
    if target_total5 is not None:
        target_total5 = float(target_total5)
        target_e1 = target_total5 / 5.0
        payouts = [s.payout_3 for s in cfg.symbols]
        probs = _solve_probs_for_target_expectation(payouts, target_e1)
        for s, p in zip(cfg.symbols, probs):
            s.prob = float(p) * 100.0
        cfg.expected_total_5 = float(target_total5)
    else:
        _recalc_probs_inverse_and_expected(cfg)
    _save_config(cfg)
    return jsonify({"ok": True})

@app.post("/spin")
def spin():
    cfg = _load_config()
    psum = sum(float(s.prob) for s in cfg.symbols) or 100.0
    for s in cfg.symbols:
        s.prob = float(s.prob) * 100.0 / psum
    spins = []
    total_payout = 0.0
    for _ in range(5):
        sym = _choice_by_prob(cfg.symbols)
        spins.append({"id": sym.id, "label": sym.label, "color": sym.color, "payout": sym.payout_3})
        total_payout += sym.payout_3
    return jsonify({"ok": True, "spins": spins, "total_payout": total_payout,
                    "expected_total_5": cfg.expected_total_5, "ts": int(time.time())})

@app.post("/calc_prob")
def calc_prob():
    """
    body: {"threshold_min":200, "threshold_max":500, "spins":5}
    - threshold_maxがNoneまたは未指定なら上限なし（∞）
    """
    body = request.get_json(silent=True) or {}
    tmin = float(body.get("threshold_min", 0))
    tmax = body.get("threshold_max")
    tmax = None if tmax in (None, "", "null") else float(tmax)
    spins = int(body.get("spins", 5))
    spins = max(1, spins)

    cfg = _load_config()
    psum = sum(float(s.prob) for s in cfg.symbols) or 100.0
    for s in cfg.symbols:
        s.prob = float(s.prob) * 100.0 / psum

    prob_ge = _prob_total_ge(cfg.symbols, spins, tmin)
    prob_le = 1.0 if tmax is None else _prob_total_le(cfg.symbols, spins, tmax)
    prob_range = max(0.0, prob_le - (1.0 - prob_ge))

    return jsonify({
        "ok": True,
        "prob_ge": prob_ge,
        "prob_le": prob_le,
        "prob_range": prob_range,
        "tmin": tmin,
        "tmax": tmax,
        "spins": spins
    })

@app.get("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(APP_DIR, "static"), filename)


# ===== 管理者認証 =====
ADMINS_PATH = os.path.join(DATA_DIR, "admins.json")

def load_admins():
    """管理者データを読み込む"""
    if not os.path.exists(ADMINS_PATH):
        default_admin = [{
            "id": 1,
            "store_code": "default",
            "login_id": "admin",
            "password_hash": generate_password_hash("admin123"),
            "name": "管理者",
            "email": "admin@example.com",
            "active": True,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }]
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ADMINS_PATH, "w", encoding="utf-8") as f:
            json.dump(default_admin, f, ensure_ascii=False, indent=2)
        return default_admin
    with open(ADMINS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_admins(admins):
    """管理者データを保存"""
    with open(ADMINS_PATH, "w", encoding="utf-8") as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

def authenticate_admin(store_code, login_id, password):
    """管理者認証"""
    admins = load_admins()
    for admin in admins:
        if (admin.get("store_code") == store_code and 
            admin.get("login_id") == login_id and 
            admin.get("active", True)):
            if check_password_hash(admin["password_hash"], password):
                admin["last_login"] = datetime.now().isoformat()
                save_admins(admins)
                return admin
    return None

def login_admin_session(admin):
    """管理者セッションを確立"""
    session.clear()
    session["logged_in"] = True
    session["admin_id"] = admin["id"]
    session["admin_name"] = admin["name"]
    session["store_code"] = admin["store_code"]
    session["login_id"] = admin["login_id"]

def logout_admin_session():
    """管理者セッションをクリア"""
    session.clear()

def is_admin_logged_in():
    """管理者がログインしているか確認"""
    return session.get("logged_in", False) and session.get("admin_id") is not None

def require_admin_login(f):
    """管理者ログインが必要なルートのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            flash("ログインが必要です", "error")
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_admin():
    """現在ログイン中の管理者情報を取得"""
    if not is_admin_logged_in():
        return None
    admin_id = session.get("admin_id")
    admins = load_admins()
    for admin in admins:
        if admin["id"] == admin_id:
            return admin
    return None

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """管理者ログイン（POSシステムと同じ方式）"""
    if request.method == "POST":
        store_code = request.form.get("store_code", "").strip()
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")
        
        admin = authenticate_admin(store_code, login_id, password)
        
        if admin:
            login_admin_session(admin)
            flash(f"ようこそ、{admin['name']}さん", "success")
            next_url = request.args.get("next") or url_for("admin_dashboard")
            return redirect(next_url)
        else:
            flash("店舗コード、ログインID、またはパスワードが正しくありません", "error")
            return render_template("admin_login.html", 
                                 store_code=store_code, 
                                 login_id=login_id)
    
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    """管理者ログアウト"""
    logout_admin_session()
    flash("ログアウトしました", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin")
@require_admin_login
def admin_dashboard():
    """管理画面ダッシュボード"""
    admin = get_current_admin()
    
    # アンケート回答データを読み込み
    survey_responses = []
    if os.path.exists(SURVEY_DATA_PATH):
        with open(SURVEY_DATA_PATH, "r", encoding="utf-8") as f:
            survey_responses = json.load(f)
    
    # 統計情報を計算
    total_responses = len(survey_responses)
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    for response in survey_responses:
        rating = response.get("rating", 0)
        if rating in rating_counts:
            rating_counts[rating] += 1
    
    avg_rating = 0
    if total_responses > 0:
        total_rating = sum(r.get("rating", 0) for r in survey_responses)
        avg_rating = round(total_rating / total_responses, 2)
    
    return render_template("admin_dashboard.html",
                         admin=admin,
                         total_responses=total_responses,
                         rating_counts=rating_counts,
                         avg_rating=avg_rating,
                         recent_responses=survey_responses[-10:][::-1])  # 最新10件を逆順


@app.route("/admin/responses")
@require_admin_login
def admin_responses():
    """全回答データを表示"""
    admin = get_current_admin()
    
    survey_responses = []
    if os.path.exists(SURVEY_DATA_PATH):
        with open(SURVEY_DATA_PATH, "r", encoding="utf-8") as f:
            survey_responses = json.load(f)
    
    # 最新順にソート
    survey_responses.reverse()
    
    return render_template("admin_responses.html",
                         admin=admin,
                         responses=survey_responses)

@app.route("/admin/export/csv")
@require_admin_login
def admin_export_csv():
    """回答データをCSVでエクスポート"""
    import csv
    from io import StringIO
    from flask import make_response
    
    survey_responses = []
    if os.path.exists(SURVEY_DATA_PATH):
        with open(SURVEY_DATA_PATH, "r", encoding="utf-8") as f:
            survey_responses = json.load(f)
    
    # CSVデータを作成
    output = StringIO()
    writer = csv.writer(output)
    
    # ヘッダー
    writer.writerow([
        "ID", "評価", "訪問目的", "雰囲気", "おすすめ度", 
        "コメント", "AI生成レビュー", "日時"
    ])
    
    # データ行
    for response in survey_responses:
        atmosphere = ", ".join(response.get("atmosphere", []))
        writer.writerow([
            response.get("id", ""),
            response.get("rating", ""),
            response.get("visit_purpose", ""),
            atmosphere,
            response.get("recommend", ""),
            response.get("comment", ""),
            response.get("generated_review", ""),
            response.get("timestamp", "")
        ])
    
    # レスポンスを作成
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=survey_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"  # Excel用にBOM付きUTF-8
    
    return response

@app.route("/admin/settings", methods=["GET", "POST"])
@require_admin_login
def admin_settings():
    """管理画面設定"""
    admin = get_current_admin()
    
    if request.method == "POST":
        # Google口コミURLの更新
        google_url = request.form.get("google_review_url", "").strip()
        
        # 設定を環境変数またはファイルに保存
        # ここでは簡易的にグローバル変数を更新
        global GOOGLE_REVIEW_URL
        GOOGLE_REVIEW_URL = google_url
        
        flash("設定を更新しました", "success")
        return redirect(url_for("admin_settings"))
    
    return render_template("admin_settings.html",
                         admin=admin,
                         google_review_url=GOOGLE_REVIEW_URL)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
