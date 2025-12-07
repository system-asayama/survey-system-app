# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from flask import Flask, jsonify, request, render_template, send_from_directory
import os, json, secrets, time, math
from decimal import Decimal, getcontext

getcontext().prec = 28  # 小数演算の安全側

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

app = Flask(__name__)

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

# ===== ルート =====
@app.get("/")
def index():
    return render_template("slot.html")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
