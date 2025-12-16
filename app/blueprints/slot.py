# -*- coding: utf-8 -*-
"""
スロット機能 Blueprint - 元の仕様に準拠
"""
from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for
from dataclasses import asdict
import os
import time
import random
from ..models import Symbol, Config
from ..utils.config import load_config, save_config
from ..utils.slot_logic import (
    choice_by_prob,
    recalc_probs_inverse_and_expected,
    prob_total_ge,
    prob_total_le
)

bp = Blueprint('slot', __name__, url_prefix='')

# パス設定
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")


@bp.get("/slot")
def slot_page():
    """スロットページ"""
    import store_db
    
    # store_slugからstore_idを取得
    store_slug = request.args.get('store_slug')
    store_id = None
    if store_slug:
        try:
            conn = store_db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM T_店舗 WHERE slug = ?", (store_slug,))
            result = cursor.fetchone()
            if result:
                store_id = result[0]
            conn.close()
        except Exception as e:
            print(f"Error getting store_id: {e}")
    
    # アンケート未回答の場合はアンケートページへリダイレクト
    # セッションキーは survey_completed_{store_id} 形式
    survey_completed = session.get(f'survey_completed_{store_id}') if store_id else session.get('survey_completed')
    if not survey_completed:
        if store_slug:
            return redirect(url_for('survey', store_slug=store_slug))
        return redirect('/')  # store_slugがない場合はトップへ
    
    # 設定ファイルからメッセージと景品データを読み込み
    import json
    settings_path = os.path.join(DATA_DIR, "settings.json")
    survey_complete_message = "アンケートにご協力いただきありがとうございます！スロットをお楽しみください。"
    prizes = []
    
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            survey_complete_message = settings.get("survey_complete_message", survey_complete_message)
            prizes = settings.get("prizes", [])
    
    return render_template('slot.html', survey_complete_message=survey_complete_message, prizes=prizes)


@bp.get("/config")
def get_config():
    """スロット設定を取得"""
    cfg = load_config()
    return jsonify({
        "symbols": [asdict(s) for s in cfg.symbols],
        "reels": cfg.reels,
        "base_bet": cfg.base_bet,
        "expected_total_5": cfg.expected_total_5
    })


@bp.post("/config")
def set_config():
    """スロット設定を更新"""
    body = request.get_json(silent=True) or {}
    reels = int(body.get("reels", 3))
    base_bet = int(body.get("base_bet", 1))
    symbols_in = body.get("symbols", [])
    if not isinstance(symbols_in, list) or len(symbols_in) == 0:
        return jsonify({"ok": False, "error": "symbolsを1件以上送信してください"}), 400
    
    parsed = [Symbol(**s) for s in symbols_in]
    cfg = load_config()
    cfg.symbols = parsed
    cfg.reels = reels
    cfg.base_bet = base_bet
    
    # 確率を逆算して期待値を再計算
    recalc_probs_inverse_and_expected(cfg)
    save_config(cfg)
    
    return jsonify({"ok": True})


@bp.post("/spin")
def spin():
    """スロット実行 - 元の仕様に準拠"""
    from prize_logic import get_prize_for_score
    import copy
    
    cfg = load_config()
    
    # 確率の正規化
    psum = sum(float(s.prob) for s in cfg.symbols) or 100.0
    for s in cfg.symbols:
        s.prob = float(s.prob) / psum * 100.0
    
    spins = []
    total_payout = 0.0
    miss_rate = cfg.miss_probability / 100.0
    
    # 通常シンボルとリーチ専用シンボルを分類
    normal_symbols = [s for s in cfg.symbols if not (hasattr(s, 'is_reach') and s.is_reach)]
    reach_symbols = [s for s in cfg.symbols if hasattr(s, 'is_reach') and s.is_reach]
    
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
            symbol = choice_by_prob(cfg.symbols)
            
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
    settings_path = os.path.join(DATA_DIR, "settings.json")
    prize = get_prize_for_score(int(total_payout), settings_path)
    
    result = {
        "ok": True, 
        "spins": spins, 
        "total_payout": total_payout,
        "expected_total_5": cfg.expected_total_5, 
        "ts": int(time.time())
    }
    
    if prize:
        result["prize"] = prize
    
    return jsonify(result)


@bp.post("/calc_prob")
def calc_prob():
    """
    確率計算
    body: {"threshold_min":200, "threshold_max":500, "spins":5}
    - threshold_maxがNoneまたは未指定なら上限なし（∞）
    """
    body = request.get_json(silent=True) or {}
    tmin = float(body.get("threshold_min", 0))
    tmax = body.get("threshold_max")
    tmax = None if tmax in (None, "", "null") else float(tmax)
    spins = int(body.get("spins", 5))
    spins = max(1, spins)

    # リクエストボディにsymbolsが含まれている場合はそれを使用
    if "symbols" in body and body["symbols"]:
        symbols_data = body["symbols"]
        symbols = [Symbol(
            id=s.get("id", ""),
            label=s.get("label", ""),
            payout_3=float(s.get("payout_3", 0)),
            prob=float(s.get("prob", 0)),
            color=s.get("color", "#000000")
        ) for s in symbols_data]
        miss_rate = float(body.get("miss_probability", 0.0))
    else:
        # ファイルから設定を読み込む
        cfg = load_config()
        symbols = list(cfg.symbols)
        miss_rate = cfg.miss_probability
    
    # ハズレ確率を考慮するため、ハズレ（0点）をシンボルリストに追加
    symbols_with_miss = list(symbols)
    
    # ハズレシンボルを追加
    miss_symbol = Symbol(
        id="miss",
        label="ハズレ",
        payout_3=0.0,
        prob=miss_rate,
        color="#000000"
    )
    symbols_with_miss.append(miss_symbol)
    
    # 確率を正規化（ハズレ確率 + シンボル確率の合計 = 100%）
    psum = sum(float(s.prob) for s in symbols_with_miss)
    for s in symbols_with_miss:
        s.prob = float(s.prob) * 100.0 / psum

    prob_ge = prob_total_ge(symbols_with_miss, spins, tmin)
    prob_le = 1.0 if tmax is None else prob_total_le(symbols_with_miss, spins, tmax)
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
