"""
スタンプカード管理画面のBlueprint
管理者向けのスタンプカード管理機能を提供
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from ..utils import get_db_connection, require_roles, ROLES

stampcard_admin_bp = Blueprint('stampcard_admin', __name__)

# ===== スタンプカード設定 =====

@stampcard_admin_bp.route('/admin/store/<int:store_id>/stampcard/settings', methods=['GET', 'POST'])
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def settings(store_id):
    """スタンプカード設定"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 店舗情報取得
    cur.execute('SELECT 名称 FROM "T_店舗" WHERE id = %s', (store_id,))
    store = cur.fetchone()
    
    if not store:
        conn.close()
        flash('店舗が見つかりません', 'error')
        return redirect(url_for('admin.store_info'))
    
    store_name = store[0]
    
    if request.method == 'POST':
        required_stamps = request.form.get('required_stamps', 10, type=int)
        reward_description = request.form.get('reward_description', '')
        card_title = request.form.get('card_title', 'スタンプカード')
        enabled = 1 if request.form.get('enabled') == 'on' else 0
        
        try:
            # 既存設定を確認
            cur.execute('SELECT id FROM "T_店舗_スタンプカード設定" WHERE store_id = %s', (store_id,))
            existing = cur.fetchone()
            
            if existing:
                # 更新
                cur.execute('''
                    UPDATE "T_店舗_スタンプカード設定"
                    SET required_stamps = %s,
                        reward_description = %s,
                        card_title = %s,
                        enabled = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE store_id = %s
                ''', (required_stamps, reward_description, card_title, enabled, store_id))
            else:
                # 新規作成
                cur.execute('''
                    INSERT INTO "T_店舗_スタンプカード設定" 
                    (store_id, required_stamps, reward_description, card_title, enabled, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (store_id, required_stamps, reward_description, card_title, enabled))
            
            conn.commit()
            conn.close()
            flash('設定を保存しました', 'success')
            return redirect(url_for('stampcard_admin.settings', store_id=store_id))
            
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f'設定の保存に失敗しました: {str(e)}', 'error')
    
    # 現在の設定を取得
    cur.execute('''
        SELECT required_stamps, reward_description, card_title, enabled
        FROM "T_店舗_スタンプカード設定"
        WHERE store_id = %s
    ''', (store_id,))
    settings = cur.fetchone()
    
    conn.close()
    
    # デフォルト値
    if not settings:
        settings = (10, '', 'スタンプカード', 1)
    
    return render_template('stampcard_admin_settings.html',
                         store_id=store_id,
                         store_name=store_name,
                         settings={
                             'required_stamps': settings[0],
                             'reward_description': settings[1],
                             'card_title': settings[2],
                             'enabled': settings[3]
                         })

# ===== 顧客管理 =====

@stampcard_admin_bp.route('/admin/store/<int:store_id>/stampcard/customers')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def customers(store_id):
    """顧客一覧"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 店舗情報取得
    cur.execute('SELECT 名称 FROM "T_店舗" WHERE id = %s', (store_id,))
    store = cur.fetchone()
    
    if not store:
        conn.close()
        flash('店舗が見つかりません', 'error')
        return redirect(url_for('admin.store_info'))
    
    store_name = store[0]
    
    # 顧客一覧取得
    cur.execute('''
        SELECT 
            c.id,
            c.name,
            c.phone,
            c.email,
            c.created_at,
            c.last_login,
            sc.current_stamps,
            sc.total_stamps,
            sc.rewards_used
        FROM "T_顧客" c
        LEFT JOIN "T_スタンプカード" sc ON c.id = sc.customer_id AND sc.store_id = %s
        WHERE c.store_id = %s
        ORDER BY c.created_at DESC
    ''', (store_id, store_id))
    
    customers_data = cur.fetchall()
    conn.close()
    
    return render_template('stampcard_admin_customers.html',
                         store_id=store_id,
                         store_name=store_name,
                         customers=customers_data)

@stampcard_admin_bp.route('/admin/store/<int:store_id>/stampcard/customers/<int:customer_id>')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def customer_detail(store_id, customer_id):
    """顧客詳細"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 店舗情報取得
    cur.execute('SELECT 名称 FROM "T_店舗" WHERE id = %s', (store_id,))
    store = cur.fetchone()
    
    if not store:
        conn.close()
        flash('店舗が見つかりません', 'error')
        return redirect(url_for('admin.store_info'))
    
    store_name = store[0]
    
    # 顧客情報取得
    cur.execute('''
        SELECT id, name, phone, email, created_at, last_login
        FROM "T_顧客"
        WHERE id = %s AND store_id = %s
    ''', (customer_id, store_id))
    customer = cur.fetchone()
    
    if not customer:
        conn.close()
        flash('顧客が見つかりません', 'error')
        return redirect(url_for('stampcard_admin.customers', store_id=store_id))
    
    # スタンプカード情報取得
    cur.execute('''
        SELECT id, current_stamps, total_stamps, rewards_used, created_at
        FROM "T_スタンプカード"
        WHERE customer_id = %s AND store_id = %s
    ''', (customer_id, store_id))
    card = cur.fetchone()
    
    # スタンプ履歴取得
    cur.execute('''
        SELECT stamps_added, action_type, note, created_by, created_at
        FROM "T_スタンプ履歴"
        WHERE customer_id = %s AND store_id = %s
        ORDER BY created_at DESC
        LIMIT 50
    ''', (customer_id, store_id))
    history = cur.fetchall()
    
    # 特典利用履歴取得
    cur.execute('''
        SELECT stamps_used, reward_description, used_by, created_at
        FROM "T_特典利用履歴"
        WHERE customer_id = %s AND store_id = %s
        ORDER BY created_at DESC
        LIMIT 20
    ''', (customer_id, store_id))
    reward_history = cur.fetchall()
    
    conn.close()
    
    return render_template('stampcard_admin_customer_detail.html',
                         store_id=store_id,
                         store_name=store_name,
                         customer=customer,
                         card=card,
                         history=history,
                         reward_history=reward_history)

@stampcard_admin_bp.route('/admin/store/<int:store_id>/stampcard/customers/<int:customer_id>/add_stamp', methods=['POST'])
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def add_stamp(store_id, customer_id):
    """スタンプを手動で追加"""
    stamps_to_add = request.form.get('stamps', 1, type=int)
    note = request.form.get('note', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # スタンプカード取得
        cur.execute('''
            SELECT id, current_stamps, total_stamps
            FROM "T_スタンプカード"
            WHERE customer_id = %s AND store_id = %s
        ''', (customer_id, store_id))
        card = cur.fetchone()
        
        if not card:
            conn.close()
            flash('スタンプカードが見つかりません', 'error')
            return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))
        
        card_id = card[0]
        
        # スタンプを追加
        cur.execute('''
            UPDATE "T_スタンプカード"
            SET current_stamps = current_stamps + %s,
                total_stamps = total_stamps + %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (stamps_to_add, stamps_to_add, card_id))
        
        # 履歴を記録
        admin_name = session.get('admin_name', 'admin')
        cur.execute('''
            INSERT INTO "T_スタンプ履歴" 
            (card_id, customer_id, store_id, stamps_added, action_type, note, created_by, created_at)
            VALUES (%s, %s, %s, %s, 'add', %s, %s, CURRENT_TIMESTAMP)
        ''', (card_id, customer_id, store_id, stamps_to_add, note, admin_name))
        
        conn.commit()
        conn.close()
        
        flash(f'スタンプを{stamps_to_add}個追加しました', 'success')
        return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f'スタンプの追加に失敗しました: {str(e)}', 'error')
        return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))

@stampcard_admin_bp.route('/admin/store/<int:store_id>/stampcard/customers/<int:customer_id>/remove_stamp', methods=['POST'])
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def remove_stamp(store_id, customer_id):
    """スタンプを手動で削除"""
    stamps_to_remove = request.form.get('stamps', 1, type=int)
    note = request.form.get('note', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # スタンプカード取得
        cur.execute('''
            SELECT id, current_stamps, total_stamps
            FROM "T_スタンプカード"
            WHERE customer_id = %s AND store_id = %s
        ''', (customer_id, store_id))
        card = cur.fetchone()
        
        if not card:
            conn.close()
            flash('スタンプカードが見つかりません', 'error')
            return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))
        
        card_id = card[0]
        current_stamps = card[1]
        
        # スタンプが足りるかチェック
        if current_stamps < stamps_to_remove:
            conn.close()
            flash(f'スタンプが足りません（現在: {current_stamps}個）', 'error')
            return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))
        
        # スタンプを削除
        cur.execute('''
            UPDATE "T_スタンプカード"
            SET current_stamps = current_stamps - %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (stamps_to_remove, card_id))
        
        # 履歴を記録
        admin_name = session.get('admin_name', 'admin')
        cur.execute('''
            INSERT INTO "T_スタンプ履歴" 
            (card_id, customer_id, store_id, stamps_added, action_type, note, created_by, created_at)
            VALUES (%s, %s, %s, %s, 'remove', %s, %s, CURRENT_TIMESTAMP)
        ''', (card_id, customer_id, store_id, -stamps_to_remove, note, admin_name))
        
        conn.commit()
        conn.close()
        
        flash(f'スタンプを{stamps_to_remove}個削除しました', 'success')
        return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f'スタンプの削除に失敗しました: {str(e)}', 'error')
        return redirect(url_for('stampcard_admin.customer_detail', store_id=store_id, customer_id=customer_id))

# ===== 統計・レポート =====

@stampcard_admin_bp.route('/admin/store/<int:store_id>/stampcard/stats')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def stats(store_id):
    """統計・レポート"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 店舗情報取得
    cur.execute('SELECT 名称 FROM "T_店舗" WHERE id = %s', (store_id,))
    store = cur.fetchone()
    
    if not store:
        conn.close()
        flash('店舗が見つかりません', 'error')
        return redirect(url_for('admin.store_info'))
    
    store_name = store[0]
    
    # 登録顧客数
    cur.execute('SELECT COUNT(*) FROM "T_顧客" WHERE store_id = %s', (store_id,))
    total_customers = cur.fetchone()[0]
    
    # アクティブ顧客数（過去30日間にログインした顧客）
    cur.execute('''
        SELECT COUNT(*) 
        FROM "T_顧客" 
        WHERE store_id = %s 
        AND last_login >= CURRENT_TIMESTAMP - INTERVAL '30 days'
    ''', (store_id,))
    active_customers = cur.fetchone()[0]
    
    # 累計スタンプ付与数
    cur.execute('''
        SELECT COALESCE(SUM(total_stamps), 0)
        FROM "T_スタンプカード"
        WHERE store_id = %s
    ''', (store_id,))
    total_stamps = cur.fetchone()[0]
    
    # 累計特典利用回数
    cur.execute('''
        SELECT COALESCE(SUM(rewards_used), 0)
        FROM "T_スタンプカード"
        WHERE store_id = %s
    ''', (store_id,))
    total_rewards = cur.fetchone()[0]
    
    # 過去30日間のスタンプ付与数推移
    cur.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM "T_スタンプ履歴"
        WHERE store_id = %s 
        AND action_type = 'add'
        AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    ''', (store_id,))
    stamp_trend = cur.fetchall()
    
    # 過去30日間の特典利用数推移
    cur.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM "T_特典利用履歴"
        WHERE store_id = %s
        AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    ''', (store_id,))
    reward_trend = cur.fetchall()
    
    conn.close()
    
    return render_template('stampcard_admin_stats.html',
                         store_id=store_id,
                         store_name=store_name,
                         stats={
                             'total_customers': total_customers,
                             'active_customers': active_customers,
                             'total_stamps': total_stamps,
                             'total_rewards': total_rewards
                         },
                         stamp_trend=stamp_trend,
                         reward_trend=reward_trend)
