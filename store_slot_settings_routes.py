"""
店舗ごとのスロット設定ルート
元のadmin/settingsを店舗ごとに移植
"""
from flask import request, redirect, url_for, flash, render_template, jsonify, session
from app.utils import require_roles, ROLES, get_db_connection
from app.utils.db import _sql
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from optimizer import optimize_symbol_probabilities as _optimize_symbol_probabilities
import store_db
from decimal import Decimal
import math


@dataclass
class Symbol:
    id: str
    label: str
    payout_3: float
    color: str | None = None
    prob: float = 0.0
    is_reach: bool = False
    reach_symbol: str | None = None


@dataclass
class Config:
    symbols: List[Symbol]
    reels: int = 3
    base_bet: int = 1
    expected_total_5: float = 100.0
    miss_probability: float = 20.0
    target_probabilities: Dict[str, float] | None = None


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

def _default_config() -> Config:
    """デフォルトのスロット設定"""
    defaults = [
        {"id": "seven", "label": "7", "payout_3": 100, "color": "#ff0000"},
        {"id": "bell", "label": "🔔", "payout_3": 50, "color": "#fbbf24"},
        {"id": "bar", "label": "BAR", "payout_3": 25, "color": "#ffffff"},
        {"id": "grape", "label": "🍇", "payout_3": 20, "color": "#7c3aed"},
        {"id": "cherry", "label": "🍒", "payout_3": 12.5, "color": "#ef4444"},
        {"id": "lemon", "label": "🍋", "payout_3": 12.5, "color": "#fde047"},
    ]
    return Config(symbols=[Symbol(**d) for d in defaults])


def register_store_slot_settings_routes(app):
    """店舗ごとのスロット設定ルートを登録"""
    
    @app.route('/admin/store/<int:store_id>/settings', methods=['GET', 'POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_slot_settings(store_id):
        """店舗ごとのスロット設定画面"""
        tenant_id = session.get('tenant_id')
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 店舗情報を取得
        cur.execute(_sql(conn, 'SELECT id, 名称, slug FROM "T_店舗" WHERE id = %s AND tenant_id = %s'), 
                   (store_id, tenant_id))
        store_row = cur.fetchone()
        
        if not store_row:
            flash('店舗が見つかりません', 'error')
            conn.close()
            return redirect(url_for('admin.store_info'))
        
        store = {
            'id': store_row[0],
            'name': store_row[1],
            'slug': store_row[2]
        }
        
        # Google設定を取得
        cur.execute(_sql(conn, 'SELECT review_url FROM "T_店舗_Google設定" WHERE store_id = %s'), (store_id,))
        google_row = cur.fetchone()
        google_review_url = google_row[0] if google_row and google_row[0] else ''
        
        # 景品設定を取得
        cur.execute(_sql(conn, 'SELECT prizes_json FROM "T_店舗_景品設定" WHERE store_id = %s'), (store_id,))
        prizes_row = cur.fetchone()
        
        if prizes_row and prizes_row[0]:
            try:
                prizes = json.loads(prizes_row[0])
            except:
                prizes = []
        else:
            prizes = [
                {"min": 500, "label": "🎁 特賞"},
                {"min": 250, "max": 499, "label": "🏆 1等"},
                {"min": 150, "max": 249, "label": "🥈 2等"},
                {"min": 100, "max": 149, "label": "🥉 3等"},
                {"min": 0, "max": 99, "label": "🎊 参加賞"}
            ]
        
        # スロット設定を取得
        cur.execute(_sql(conn, 'SELECT config_json FROM "T_店舗_スロット設定" WHERE store_id = %s'), (store_id,))
        slot_row = cur.fetchone()
        
        if slot_row and slot_row[0]:
            try:
                slot_config_dict = json.loads(slot_row[0])
                slot_config = Config(
                    symbols=[Symbol(**s) for s in slot_config_dict.get('symbols', [])],
                    reels=slot_config_dict.get('reels', 3),
                    base_bet=slot_config_dict.get('base_bet', 1),
                    expected_total_5=slot_config_dict.get('expected_total_5', 100.0),
                    miss_probability=slot_config_dict.get('miss_probability', 20.0),
                    target_probabilities=slot_config_dict.get('target_probabilities')
                )
            except:
                slot_config = _default_config()
        else:
            slot_config = _default_config()
        
        conn.close()
        
        if request.method == 'POST':
            # フォームデータを処理
            google_url = request.form.get("google_review_url", "").strip()
            survey_message = request.form.get("survey_complete_message", "").strip()
            
            # Google設定を保存
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(_sql(conn, 'SELECT id FROM "T_店舗_Google設定" WHERE store_id = %s'), (store_id,))
            if cur.fetchone():
                cur.execute(_sql(conn, '''
                    UPDATE "T_店舗_Google設定"
                    SET review_url = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE store_id = %s
                '''), (google_url, store_id))
            else:
                cur.execute(_sql(conn, '''
                    INSERT INTO "T_店舗_Google設定" (store_id, review_url)
                    VALUES (%s, %s)
                '''), (store_id, google_url))
            
            conn.commit()
            conn.close()
            
            flash('設定を更新しました', 'success')
            return redirect(url_for('store_slot_settings', store_id=store_id))
        
        # 管理者情報を取得
        user_id = session.get('user_id')
        admin_conn = get_db_connection()
        admin_cur = admin_conn.cursor()
        admin_cur.execute(_sql(admin_conn, 'SELECT login_id, name, email FROM "T_管理者" WHERE id = %s'), (user_id,))
        admin_row = admin_cur.fetchone()
        admin_conn.close()
        
        admin = {
            'store_code': store.get('slug', ''),
            'login_id': admin_row[0] if admin_row else '',
            'name': admin_row[1] if admin_row else '',
            'email': admin_row[2] if admin_row else '',
            'last_login': ''
        }
        
        return render_template('admin_settings.html',
                             store=store,
                             admin=admin,
                             google_review_url=google_review_url,
                             survey_complete_message="アンケートにご協力いただきありがとうございます！スロットをお楽しみください。",
                             prizes=prizes,
                             slot_config=asdict(slot_config))
    
    
    @app.route('/admin/save_prizes', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def admin_save_prizes():
        """景品設定を保存"""
        try:
            data = request.get_json()
            prizes = data.get('prizes', [])
            
            # 点数で降順ソート
            prizes.sort(key=lambda x: x.get("min", 0), reverse=True)
            
            # セッションから店舗IDを取得
            store_id = session.get('store_id')
            if not store_id:
                return jsonify({"ok": False, "error": "店舗が選択されていません"}), 400
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 既存の景品設定を取得
            cur.execute(_sql(conn, 'SELECT prizes_json FROM "T_店舗_景品設定" WHERE store_id = %s'), (store_id,))
            row = cur.fetchone()
            
            # JSON形式で保存
            prizes_json = json.dumps(prizes, ensure_ascii=False)
            
            if row:
                cur.execute(_sql(conn, '''
                    UPDATE "T_店舗_景品設定"
                    SET prizes_json = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE store_id = %s
                '''), (prizes_json, store_id))
            else:
                cur.execute(_sql(conn, '''
                    INSERT INTO "T_店舗_景品設定" (store_id, prizes_json)
                    VALUES (%s, %s)
                '''), (store_id, prizes_json))
            
            conn.commit()
            conn.close()
            
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    
    
    @app.route('/admin/store/<int:store_id>/save_slot_config', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_save_slot_config(store_id):
        """店舗ごとのスロット設定を保存"""
        try:
            tenant_id = session.get('tenant_id')
            
            # 期待値を取得
            expected_total_5 = float(request.form.get("expected_total_5", 100.0))
            
            # ハズレ確率を取得
            miss_probability = float(request.form.get("miss_probability", 20.0))
            
            # シンボル数を取得
            symbol_count = int(request.form.get("symbol_count", 0))
            
            # シンボルデータを収集
            symbols = []
            for i in range(symbol_count):
                symbol_id = request.form.get(f"symbol_id_{i}", "").strip()
                symbol_label = request.form.get(f"symbol_label_{i}", "").strip()
                symbol_payout = float(request.form.get(f"symbol_payout_{i}", 0))
                symbol_prob = float(request.form.get(f"symbol_prob_{i}", 0))
                symbol_color = request.form.get(f"symbol_color_{i}", "#888888")
                
                if symbol_id and symbol_label:
                    symbols.append(Symbol(
                        id=symbol_id,
                        label=symbol_label,
                        payout_3=symbol_payout,
                        color=symbol_color,
                        prob=symbol_prob
                    ))
            
            # 設定オブジェクトを作成
            config = Config(
                symbols=symbols,
                expected_total_5=expected_total_5,
                miss_probability=miss_probability
            )
            
            # JSON形式で保存
            config_json = json.dumps(asdict(config), ensure_ascii=False)
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 既存レコードがあれば更新、なければ挿入
            cur.execute(_sql(conn, 'SELECT id FROM "T_店舗_スロット設定" WHERE store_id = %s'), (store_id,))
            if cur.fetchone():
                cur.execute(_sql(conn, '''
                    UPDATE "T_店舗_スロット設定"
                    SET config_json = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE store_id = %s
                '''), (config_json, store_id))
            else:
                cur.execute(_sql(conn, '''
                    INSERT INTO "T_店舗_スロット設定" (store_id, config_json)
                    VALUES (%s, %s)
                '''), (store_id, config_json))
            
            conn.commit()
            conn.close()
            
            flash('スロット設定を保存しました', 'success')
            return redirect(url_for('store_slot_settings', store_id=store_id))
            
        except Exception as e:
            flash(f'エラーが発生しました: {str(e)}', 'error')
            return redirect(url_for('store_slot_settings', store_id=store_id))
    
    
    @app.route('/admin/store/<int:store_id>/optimize_probabilities', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_optimize_probabilities(store_id):
        """店舗ごとの確率最適化"""
        try:
            data = request.get_json()
            expected_total_5 = float(data.get('expected_total_5', 100.0))
            symbols_data = data.get('symbols', [])
            target_probabilities = data.get('target_probabilities', {})
            
            # Symbolオブジェクトに変換
            symbols = [Symbol(**s) for s in symbols_data]
            
            # 確率を最適化
            optimized_symbols = _optimize_symbol_probabilities(
                symbols=symbols,
                expected_total_5=expected_total_5,
                target_probabilities=target_probabilities if target_probabilities else None
            )
            
            # 結果を返す
            return jsonify({
                "ok": True,
                "symbols": [asdict(s) for s in optimized_symbols]
            })
            
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    
    @app.route('/admin/store/<int:store_id>/calc_prob', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_calc_prob(store_id):
        """店舗ごとの確率計算"""
        try:
            body = request.get_json(silent=True) or {}
            tmin = float(body.get("threshold_min", 0))
            tmax = body.get("threshold_max")
            tmax = None if tmax in (None, "", "null") else float(tmax)
            spins = int(body.get("spins", 5))
            spins = max(1, spins)
            
            # データベースから設定を取得
            cfg_dict = store_db.get_slot_config(store_id)
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
            
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
