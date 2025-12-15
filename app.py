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

# OpenAI クライアントを動的に取得する関数
def get_openai_client(app_type=None, app_id=None, store_id=None, tenant_id=None):
    """
    OpenAIクライアントを階層的に取得。
    優先順位: アプリ設定 > 店舗設定 > テナント設定 > 環境変数
    
    app_type: 'survey' または 'slot'
    app_id: アプリ設定ID (T_店舗_アンケート設定.id または T_店舗_スロット設定.id)
    """
    api_key = None
    
    try:
        conn = store_db.get_db_connection()
        cursor = conn.cursor()
        
        # 1. アプリ設定のキーを確認
        if app_type and app_id:
            if app_type == 'survey':
                cursor.execute("SELECT openai_api_key, store_id FROM T_店舗_アンケート設定 WHERE id = ?", (app_id,))
            elif app_type == 'slot':
                cursor.execute("SELECT openai_api_key, store_id FROM T_店舗_スロット設定 WHERE id = ?", (app_id,))
            
            result = cursor.fetchone()
            if result:
                if result[0]:  # アプリにAPIキーが設定されている
                    api_key = result[0]
                    conn.close()
                    return OpenAI(api_key=api_key)
                # アプリにキーがない場合、store_idを取得
                if not store_id and result[1]:
                    store_id = result[1]
        
        # 2. 店舗設定のキーを確認
        if store_id:
            cursor.execute("SELECT openai_api_key, tenant_id FROM T_店舗 WHERE id = ?", (store_id,))
            result = cursor.fetchone()
            if result:
                if result[0]:  # 店舗にAPIキーが設定されている
                    api_key = result[0]
                    conn.close()
                    return OpenAI(api_key=api_key)
                # 店舗にキーがない場合、tenant_idを取得
                if not tenant_id and result[1]:
                    tenant_id = result[1]
        
        # 3. テナント設定のキーを確認
        if tenant_id:
            cursor.execute("SELECT openai_api_key FROM T_テナント WHERE id = ?", (tenant_id,))
            result = cursor.fetchone()
            if result and result[0]:
                api_key = result[0]
                conn.close()
                return OpenAI(api_key=api_key)
        
        conn.close()
    except Exception as e:
        print(f"Error getting OpenAI API key from database: {e}")
    
    # 4. 環境変数を確認
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("OpenAI APIキーが設定されていません。アプリ、店舗、またはテナントの管理画面でAPIキーを設定してください。")
    
    return OpenAI(api_key=api_key)

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
    is_disabled: bool = False  # 不使用フラグ
    is_default: bool = False  # デフォルト役フラグ

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

def _generate_review_text(survey_data, store_id=None, app_id=None):
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
        # アプリ設定に応じたOpenAIクライアントを取得
        client = get_openai_client(app_type='survey', app_id=app_id, store_id=store_id)
        response = client.chat.completions.create(
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
    """トップページ - 管理画面ログインへリダイレクト"""
    return redirect(url_for('auth.select_login'))

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
    
    # アンケートアプリIDを取得
    survey_app_id = None
    try:
        conn = store_db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM T_店舗_アンケート設定 WHERE store_id = ?", (g.store_id,))
        result = cursor.fetchone()
        if result:
            survey_app_id = result[0]
        conn.close()
    except Exception as e:
        print(f"Error getting survey app id: {e}")
    
    # 星4以上の場合のみAI投稿文を生成
    if rating >= 4:
        generated_review = _generate_review_text(body, g.store_id, survey_app_id)
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
        store_slug=g.store_slug,
        generated_review=generated_review,
        google_review_url=google_review_url,
        rating=rating
    )

@app.get("/store/<store_slug>/slot")
@require_store
def slot_page():
    """スロットページ"""
    # デモプレイモードの場合はセッションチェックをスキップ
    is_demo = request.args.get('demo') == 'true'
    
    # アンケート未回答の場合はアンケートページへリダイレクト（デモモード除く）
    if not is_demo and not session.get(f'survey_completed_{g.store_id}'):
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
    import random
    
    cfg_dict = store_db.get_slot_config(g.store_id)
    symbols = [Symbol(**s) for s in cfg_dict["symbols"]]
    
    # 確率の正規化
    psum = sum(float(s.prob) for s in symbols) or 100.0
    for s in symbols:
        s.prob = float(s.prob) / psum * 100.0
    
    spins = []
    total_payout = 0.0
    miss_rate = cfg_dict.get("miss_probability", 0.0) / 100.0
    
    # 通常シンボルとリーチ専用シンボルを分類
    normal_symbols = [s for s in symbols if not (hasattr(s, 'is_reach') and s.is_reach)]
    reach_symbols = [s for s in symbols if hasattr(s, 'is_reach') and s.is_reach]
    
    # 5回スピン
    for _ in range(5):
        # まずハズレかどうかを判定
        if random.random() < miss_rate:
            # ハズレ：1コマ目と2コマ目は必ず異なるシンボル
            reel1 = random.choice(normal_symbols)
            # reel2はreel1と異なるものを選ぶ
            other_symbols = [s for s in normal_symbols if s.id != reel1.id]
            if other_symbols:
                reel2 = random.choice(other_symbols)
            else:
                reel2 = reel1  # シンボルが1つしかない場合
            reel3 = random.choice(normal_symbols)
            
            spins.append({
                "reels": [
                    {"id": reel1.id, "label": reel1.label, "color": reel1.color},
                    {"id": reel2.id, "label": reel2.label, "color": reel2.color},
                    {"id": reel3.id, "label": reel3.label, "color": reel3.color}
                ],
                "matched": False,
                "is_reach": False,
                "payout": 0
            })
        else:
            # 当たりまたはリーチハズレ：シンボルを確率で抽選
            symbol = _choice_by_prob(symbols)
            
            # リーチ専用シンボルの場合
            is_reach_symbol = hasattr(symbol, 'is_reach') and symbol.is_reach
            
            if is_reach_symbol:
                # リーチハズレ：1,2コマ目は同じ、3コマ目は必ず異なる
                reach_symbol_id = symbol.reach_symbol if hasattr(symbol, 'reach_symbol') else symbol.id
                # 元のシンボルを探す
                original_symbol = next((s for s in normal_symbols if s.id == reach_symbol_id), symbol)
                
                # リール3用に異なるシンボルを選ぶ（リーチ専用シンボルも除外）
                other_symbols = [s for s in normal_symbols if s.id != reach_symbol_id]
                if other_symbols:
                    reel3_symbol = random.choice(other_symbols)
                else:
                    reel3_symbol = original_symbol
                
                spins.append({
                    "reels": [
                        {"id": original_symbol.id, "label": original_symbol.label, "color": original_symbol.color},
                        {"id": original_symbol.id, "label": original_symbol.label, "color": original_symbol.color},
                        {"id": reel3_symbol.id, "label": reel3_symbol.label, "color": reel3_symbol.color}
                    ],
                    "matched": False,
                    "is_reach": True,
                    "reach_symbol": {"id": original_symbol.id, "label": original_symbol.label, "color": original_symbol.color},
                    "payout": 0
                })
            else:
                # 通常の当たり：3つ揃い
                payout = symbol.payout_3
                total_payout += payout
                
                spins.append({
                    "reels": [
                        {"id": symbol.id, "label": symbol.label, "color": symbol.color},
                        {"id": symbol.id, "label": symbol.label, "color": symbol.color},
                        {"id": symbol.id, "label": symbol.label, "color": symbol.color}
                    ],
                    "matched": True,
                    "is_reach": False,
                    "symbol": {"id": symbol.id, "label": symbol.label, "color": symbol.color},
                    "payout": payout
                })
    
    # 景品判定
    prizes = store_db.get_prizes_config(g.store_id)
    matched_prize = None
    for prize in prizes:
        min_score = prize.get('min_score', 0)
        max_score = prize.get('max_score')
        if max_score is None:
            # 上限なし
            if total_payout >= min_score:
                matched_prize = prize
                break
        else:
            # 範囲内
            if min_score <= total_payout <= max_score:
                matched_prize = prize
                break
    
    result = {
        "ok": True,
        "spins": spins,
        "total_payout": total_payout,
        "ts": int(time.time())
    }
    
    if matched_prize:
        result["prize"] = {
            "rank": matched_prize.get('rank', ''),
            "name": matched_prize.get('name', '')
        }
    
    return jsonify(result)

@app.post("/store/<store_slug>/calc_prob")
@require_store
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
    
    cfg_dict = store_db.get_slot_config(g.store_id)
    symbols = [Symbol(**s) for s in cfg_dict["symbols"]]
    miss_probability = cfg_dict.get("miss_probability", 0.0)
    
    # ハズレ確率を考慮するため、ハズレ（0点）をシンボルリストに追加
    symbols_with_miss = list(symbols)
    
    # ハズレシンボルを追加
    miss_symbol = Symbol(
        id="miss",
        label="ハズレ",
        payout_3=0.0,
        prob=miss_probability,
        color="#000000"
    )
    symbols_with_miss.append(miss_symbol)
    
    # 確率を正規化（ハズレ確率 + シンボル確率の合計 = 100%）
    psum = sum(float(s.prob) for s in symbols_with_miss)
    for s in symbols_with_miss:
        s.prob = float(s.prob) * 100.0 / psum
    
    prob_ge = _prob_total_ge(symbols_with_miss, spins, tmin)
    prob_le = 1.0 if tmax is None else _prob_total_le(symbols_with_miss, spins, tmax)
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
    from app.blueprints.survey_admin import bp as survey_admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_admin_bp)
    app.register_blueprint(tenant_admin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(survey_admin_bp)
    
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

## ===== QRコード印刷ルート =====
try:
    from qr_print_routes import register_qr_print_routes
    register_qr_print_routes(app)
    print("✅ QRコード印刷ルート登録完了")
except Exception as e:
    print(f"⚠️ QRコード印刷ルート登録失敗: {e}")

# ===== OpenAI APIキー設定ルート =====
try:
    from openai_key_routes import openai_key_bp
    app.register_blueprint(openai_key_bp)
    print("✅ OpenAI APIキー設定ルート登録完了")
except Exception as e:
    print(f"⚠️ OpenAI APIキー設定ルート登録失敗: {e}")



if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    app.run(host="0.0.0.0", port=port, debug=True)
