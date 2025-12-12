# -*- coding: utf-8 -*-
"""
スロット機能 Blueprint
"""
from flask import Blueprint, jsonify, request
from dataclasses import asdict
import os
import time
import random
from ..models import Symbol
from ..utils.config import load_config, save_config
from ..utils.slot_logic import (
    choice_by_prob,
    solve_probs_for_target_expectation,
    prob_total_ge,
    prob_total_le
)

bp = Blueprint('slot', __name__, url_prefix='/api')

# パス設定
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")


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
    from ..utils.slot_logic import recalc_probs_inverse_and_expected
    
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
    
    # ハズレ確率を取得
    miss_prob = body.get("miss_probability", None)
    if miss_prob is not None:
        cfg.miss_probability = float(miss_prob)
    
    target_total5 = body.get("target_expected_total_5", None)
    if target_total5 is not None:
        target_total5 = float(target_total5)
        target_e1 = target_total5 / 5.0
        payouts = [s.payout_3 for s in cfg.symbols]
        
        # ハズレ確率を考慮した期待値計算
        miss_rate = cfg.miss_probability / 100.0
        if miss_rate >= 1.0:
            return jsonify({"ok": False, "error": "ハズレ確率は100%未満である必要があります"}), 400
        
        adjusted_target_e1 = target_e1 / (1.0 - miss_rate)
        probs = solve_probs_for_target_expectation(payouts, adjusted_target_e1)
        
        if probs:
            for s, p in zip(cfg.symbols, probs):
                s.prob = float(p * 100.0)
            # 実際の期待値を再計算
            actual_e1 = sum(s.payout_3 * (s.prob / 100.0) for s in cfg.symbols)
            cfg.expected_total_5 = float(actual_e1 * 5.0 * (1.0 - miss_rate))
    else:
        recalc_probs_inverse_and_expected(cfg)
    
    save_config(cfg)
    return jsonify({"ok": True, "expected_total_5": cfg.expected_total_5})


@bp.post("/spin")
def spin():
    """スロットを5回スピン"""
    from prize_logic import get_prize_for_score
    
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
    """確率計算"""
    body = request.get_json(silent=True) or {}
    symbols_in = body.get("symbols", [])
    spins_count = int(body.get("spins", 5))
    threshold = float(body.get("threshold", 100))
    mode = body.get("mode", "ge")  # "ge" or "le"
    
    if not isinstance(symbols_in, list) or len(symbols_in) == 0:
        return jsonify({"ok": False, "error": "symbolsを1件以上送信してください"}), 400
    
    parsed = [Symbol(**s) for s in symbols_in]
    
    if mode == "le":
        prob = prob_total_le(parsed, spins_count, threshold)
    else:
        prob = prob_total_ge(parsed, spins_count, threshold)
    
    return jsonify({
        "ok": True,
        "probability": float(prob),
        "percentage": float(prob * 100.0)
    })
