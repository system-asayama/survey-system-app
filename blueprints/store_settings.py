"""
店舗設定管理
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from ..utils import require_roles, ROLES, get_db_connection
from ..utils.db import _sql

bp = Blueprint('store_settings', __name__, url_prefix='/admin/store_settings')


@bp.route('/')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def index():
    """店舗設定トップページ"""
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # セッションにtenant_idがない場合、管理者情報から取得
    if not tenant_id:
        cur.execute(_sql(conn, 'SELECT tenant_id FROM "T_管理者" WHERE id = %s'), (user_id,))
        admin_row = cur.fetchone()
        if admin_row and admin_row[0]:
            tenant_id = admin_row[0]
    
    # テナント配下の店舗一覧を取得
    cur.execute(_sql(conn, '''
        SELECT id, 名称, slug, 住所, 電話番号 
        FROM "T_店舗" 
        WHERE tenant_id = %s 
        ORDER BY id
    '''), (tenant_id,))
    
    stores = []
    for row in cur.fetchall():
        stores.append({
            'id': row[0],
            'name': row[1],
            'slug': row[2],
            'address': row[3],
            'phone': row[4]
        })
    
    conn.close()
    return render_template('store_settings/index.html', stores=stores)


@bp.route('/<int:store_id>/prizes')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def prizes(store_id):
    """景品設定ページ"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 店舗情報を取得
    cur.execute(_sql(conn, 'SELECT id, 名称, slug FROM "T_店舗" WHERE id = %s'), (store_id,))
    store_row = cur.fetchone()
    
    if not store_row:
        flash('店舗が見つかりません', 'error')
        conn.close()
        return redirect(url_for('store_settings.index'))
    
    store = {
        'id': store_row[0],
        'name': store_row[1],
        'slug': store_row[2]
    }
    
    # 景品一覧を取得
    cur.execute(_sql(conn, '''
        SELECT id, 景品名, 最小得点, 最大得点, 在庫数, 有効フラグ 
        FROM "T_店舗景品設定" 
        WHERE 店舗ID = %s 
        ORDER BY 最小得点
    '''), (store_id,))
    
    prizes = []
    for row in cur.fetchall():
        prizes.append({
            'id': row[0],
            'name': row[1],
            'min_score': row[2],
            'max_score': row[3],
            'stock': row[4],
            'enabled': row[5]
        })
    
    conn.close()
    return render_template('store_settings/prizes.html', store=store, prizes=prizes)


@bp.route('/<int:store_id>/prizes/add', methods=['POST'])
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def add_prize(store_id):
    """景品追加"""
    name = request.form.get('name')
    min_score = request.form.get('min_score', type=float)
    max_score = request.form.get('max_score', type=float)
    stock = request.form.get('stock', type=int)
    enabled = request.form.get('enabled') == 'on'
    
    if not name or min_score is None or max_score is None:
        flash('必須項目を入力してください', 'error')
        return redirect(url_for('store_settings.prizes', store_id=store_id))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(_sql(conn, '''
        INSERT INTO "T_店舗景品設定" (店舗ID, 景品名, 最小得点, 最大得点, 在庫数, 有効フラグ)
        VALUES (%s, %s, %s, %s, %s, %s)
    '''), (store_id, name, min_score, max_score, stock or 0, enabled))
    
    conn.commit()
    conn.close()
    
    flash('景品を追加しました', 'success')
    return redirect(url_for('store_settings.prizes', store_id=store_id))


@bp.route('/<int:store_id>/prizes/<int:prize_id>/delete', methods=['POST'])
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def delete_prize(store_id, prize_id):
    """景品削除"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(_sql(conn, 'DELETE FROM "T_店舗景品設定" WHERE id = %s AND 店舗ID = %s'), (prize_id, store_id))
    
    conn.commit()
    conn.close()
    
    flash('景品を削除しました', 'success')
    return redirect(url_for('store_settings.prizes', store_id=store_id))


@bp.route('/<int:store_id>/google_review')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def google_review(store_id):
    """Google口コミURL設定ページ"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 店舗情報を取得
    cur.execute(_sql(conn, 'SELECT id, 名称, slug FROM "T_店舗" WHERE id = %s'), (store_id,))
    store_row = cur.fetchone()
    
    if not store_row:
        flash('店舗が見つかりません', 'error')
        conn.close()
        return redirect(url_for('store_settings.index'))
    
    store = {
        'id': store_row[0],
        'name': store_row[1],
        'slug': store_row[2]
    }
    
    # Google口コミURL設定を取得
    cur.execute(_sql(conn, '''
        SELECT Google口コミURL 
        FROM "T_店舗Google口コミ設定" 
        WHERE 店舗ID = %s
    '''), (store_id,))
    
    url_row = cur.fetchone()
    google_review_url = url_row[0] if url_row else ''
    
    conn.close()
    return render_template('store_settings/google_review.html', store=store, google_review_url=google_review_url)


@bp.route('/<int:store_id>/google_review/save', methods=['POST'])
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def save_google_review(store_id):
    """Google口コミURL保存"""
    google_review_url = request.form.get('google_review_url', '').strip()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 既存の設定があるか確認
    cur.execute(_sql(conn, 'SELECT id FROM "T_店舗Google口コミ設定" WHERE 店舗ID = %s'), (store_id,))
    existing = cur.fetchone()
    
    if existing:
        # 更新
        cur.execute(_sql(conn, '''
            UPDATE "T_店舗Google口コミ設定" 
            SET Google口コミURL = %s, 更新日時 = CURRENT_TIMESTAMP 
            WHERE 店舗ID = %s
        '''), (google_review_url, store_id))
    else:
        # 新規作成
        cur.execute(_sql(conn, '''
            INSERT INTO "T_店舗Google口コミ設定" (店舗ID, Google口コミURL)
            VALUES (%s, %s)
        '''), (store_id, google_review_url))
    
    conn.commit()
    conn.close()
    
    flash('Google口コミURLを保存しました', 'success')
    return redirect(url_for('store_settings.google_review', store_id=store_id))
