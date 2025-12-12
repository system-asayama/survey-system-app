# -*- coding: utf-8 -*-
"""
管理者ダッシュボード
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..utils import require_roles, ROLES, get_db_connection
from ..utils.db import _sql
from werkzeug.security import generate_password_hash

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
def dashboard():
    """管理者ダッシュボード"""
    return render_template('admin_dashboard.html', tenant_id=session.get('tenant_id'))


@bp.route('/store_info')
@require_roles(ROLES["ADMIN"])
def store_info():
    """店舗情報表示"""
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 管理者情報を取得してテナントIDを確認
    cur.execute(_sql(conn, 'SELECT tenant_id FROM "T_管理者" WHERE id = %s'), (user_id,))
    admin_row = cur.fetchone()
    
    if not admin_row or not admin_row[0]:
        flash('テナント情報が見つかりません', 'error')
        conn.close()
        return redirect(url_for('admin.dashboard'))
    
    tenant_id = admin_row[0]
    
    # テナント情報を取得
    cur.execute(_sql(conn, 'SELECT id, 名称, slug, created_at FROM "T_テナント" WHERE id = %s'), (tenant_id,))
    tenant_row = cur.fetchone()
    
    if not tenant_row:
        flash('テナント情報が見つかりません', 'error')
        conn.close()
        return redirect(url_for('admin.dashboard'))
    
    tenant = {
        'id': tenant_row[0],
        '名称': tenant_row[1],
        'slug': tenant_row[2],
        'created_at': tenant_row[3]
    }
    
    # 店舗一覧を取得
    cur.execute(_sql(conn, 'SELECT id, 名称, slug, created_at FROM "T_店舗" WHERE tenant_id = %s ORDER BY id'), (tenant_id,))
    stores = []
    for row in cur.fetchall():
        stores.append({
            'id': row[0],
            '名称': row[1],
            'slug': row[2],
            'created_at': row[3]
        })
    
    conn.close()
    
    return render_template('admin_store_info.html', tenant=tenant, stores=stores)


@bp.route('/console')
@require_roles(ROLES["ADMIN"])
def console():
    """管理者コンソール"""
    tenant_id = session.get('tenant_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 従業員数を取得
    cur.execute(_sql(conn, 'SELECT COUNT(*) FROM "T_従業員" WHERE tenant_id = %s'),
               (tenant_id,))
    employee_count = cur.fetchone()[0]
    
    conn.close()
    
    return render_template('admin_console.html', employee_count=employee_count)


# ========================================
# 管理者管理
# ========================================

@bp.route('/admins')
@require_roles(ROLES["ADMIN"])
def admins():
    """管理者一覧"""
    user_id = session.get('user_id')
    tenant_id = session.get('tenant_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # オーナー権限チェック
    cur.execute(_sql(conn, 'SELECT is_owner, can_manage_admins FROM "T_管理者" WHERE id = %s'), (user_id,))
    row = cur.fetchone()
    if not row or (row[0] != 1 and row[1] != 1):
        flash('管理者を管理する権限がありません', 'error')
        conn.close()
        return redirect(url_for('admin.dashboard'))
    
    is_owner = row[0] == 1
    
    cur.execute(_sql(conn, '''
        SELECT id, login_id, name, is_owner, created_at 
        FROM "T_管理者" 
        WHERE tenant_id = %s AND role = %s
        ORDER BY id
    '''), (tenant_id, ROLES["ADMIN"]))
    
    admins_list = []
    for row in cur.fetchall():
        admins_list.append({
            'id': row[0],
            'login_id': row[1],
            'name': row[2],
            'is_owner': row[3] == 1,
            'created_at': row[4]
        })
    conn.close()
    
    return render_template('admin_admins.html', admins=admins_list, is_owner=is_owner, current_user_id=user_id)


@bp.route('/admins/new', methods=['GET', 'POST'])
@require_roles(ROLES["ADMIN"])
def admin_new():
    """管理者新規作成"""
    user_id = session.get('user_id')
    tenant_id = session.get('tenant_id')
    
    # オーナー権限チェック
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(_sql(conn, 'SELECT is_owner, can_manage_admins FROM "T_管理者" WHERE id = %s'), (user_id,))
    row = cur.fetchone()
    if not row or (row[0] != 1 and row[1] != 1):
        flash('管理者を管理する権限がありません', 'error')
        conn.close()
        return redirect(url_for('admin.dashboard'))
    conn.close()
    
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        
        if not login_id or not name or not password:
            flash('全ての項目を入力してください', 'error')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 重複チェック
            cur.execute(_sql(conn, 'SELECT id FROM "T_管理者" WHERE login_id = %s'), (login_id,))
            if cur.fetchone():
                flash('このログインIDは既に使用されています', 'error')
                conn.close()
            else:
                ph = generate_password_hash(password)
                cur.execute(_sql(conn, '''
                    INSERT INTO "T_管理者" (login_id, name, password_hash, role, tenant_id, active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                '''), (login_id, name, ph, ROLES['ADMIN'], tenant_id, 1))
                conn.commit()
                conn.close()
                flash('管理者を作成しました', 'success')
                return redirect(url_for('admin.admins'))
    
    return render_template('admin_admin_new.html', back_url=url_for('admin.admins'))


@bp.route('/admins/<int:admin_id>/delete', methods=['POST'])
@require_roles(ROLES["ADMIN"])
def admin_delete(admin_id):
    """管理者削除"""
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # オーナー権限チェック
    cur.execute(_sql(conn, 'SELECT is_owner, can_manage_admins FROM "T_管理者" WHERE id = %s'), (user_id,))
    row = cur.fetchone()
    if not row or (row[0] != 1 and row[1] != 1):
        flash('管理者を管理する権限がありません', 'error')
        conn.close()
        return redirect(url_for('admin.dashboard'))
    
    # 自分自身の削除を防止
    if admin_id == user_id:
        flash('自分自身を削除することはできません', 'error')
        conn.close()
        return redirect(url_for('admin.admins'))
    
    # テナントIDの確認
    cur.execute(_sql(conn, 'SELECT name FROM "T_管理者" WHERE id = %s AND tenant_id = %s AND role = %s'),
               (admin_id, tenant_id, ROLES["ADMIN"]))
    row = cur.fetchone()
    
    if not row:
        flash('管理者が見つかりません', 'error')
    else:
        cur.execute(_sql(conn, 'DELETE FROM "T_管理者" WHERE id = %s'), (admin_id,))
        conn.commit()
        flash(f'{row[0]} を削除しました', 'success')
    
    conn.close()
    return redirect(url_for('admin.admins'))


@bp.route('/admins/<int:admin_id>/transfer_owner', methods=['POST'])
@require_roles(ROLES["ADMIN"])
def admin_transfer_owner(admin_id):
    """オーナー権限移譲"""
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 現在のユーザーがオーナーか確認
    cur.execute(_sql(conn, 'SELECT is_owner FROM "T_管理者" WHERE id = %s'), (user_id,))
    row = cur.fetchone()
    if not row or row[0] != 1:
        flash('オーナー権限を移譲する権限がありません', 'error')
        conn.close()
        return redirect(url_for('admin.admins'))
    
    # 自分自身への移譲を防止
    if admin_id == user_id:
        flash('自分自身にオーナー権限を移譲することはできません', 'error')
        conn.close()
        return redirect(url_for('admin.admins'))
    
    # 移譲先の管理者が同じテナントか確認
    cur.execute(_sql(conn, 'SELECT name FROM "T_管理者" WHERE id = %s AND tenant_id = %s AND role = %s'),
               (admin_id, tenant_id, ROLES["ADMIN"]))
    row = cur.fetchone()
    
    if not row:
        flash('管理者が見つかりません', 'error')
    else:
        # 現在のオーナーの権限を解除（can_manage_adminsも解除）
        cur.execute(_sql(conn, 'UPDATE "T_管理者" SET is_owner = 0, can_manage_admins = 0 WHERE id = %s'), (user_id,))
        # 新しいオーナーに権限を付与
        cur.execute(_sql(conn, 'UPDATE "T_管理者" SET is_owner = 1, can_manage_admins = 1 WHERE id = %s'), (admin_id,))
        conn.commit()
        flash(f'{row[0]} にオーナー権限を移譲しました', 'success')
    
    conn.close()
    return redirect(url_for('admin.admins'))


# ========================================
# 従業員管理
# ========================================

@bp.route('/employees')
@require_roles(ROLES["ADMIN"])
def employees():
    """従業員一覧"""
    tenant_id = session.get('tenant_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(_sql(conn, '''
        SELECT id, login_id, name, email, created_at 
        FROM "T_従業員" 
        WHERE tenant_id = %s 
        ORDER BY id
    '''), (tenant_id,))
    
    employees_list = []
    for row in cur.fetchall():
        employees_list.append({
            'id': row[0],
            'login_id': row[1],
            'name': row[2],
            'email': row[3],
            'created_at': row[4]
        })
    conn.close()
    
    return render_template('admin_employees.html', employees=employees_list)


@bp.route('/employees/new', methods=['GET', 'POST'])
@require_roles(ROLES["ADMIN"])
def employee_new():
    """従業員新規作成"""
    tenant_id = session.get('tenant_id')
    
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not login_id or not name or not email or not password:
            flash('全ての項目を入力してください', 'error')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 重複チェック
            cur.execute(_sql(conn, 'SELECT id FROM "T_従業員" WHERE login_id = %s OR email = %s'), (login_id, email))
            if cur.fetchone():
                flash('このログインIDまたはメールアドレスは既に使用されています', 'error')
                conn.close()
            else:
                ph = generate_password_hash(password)
                cur.execute(_sql(conn, '''
                    INSERT INTO "T_従業員" (login_id, name, email, password_hash, tenant_id, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                '''), (login_id, name, email, ph, tenant_id, ROLES['EMPLOYEE']))
                conn.commit()
                conn.close()
                flash('従業員を作成しました', 'success')
                return redirect(url_for('admin.employees'))
    
    return render_template('admin_employee_new.html', back_url=url_for('admin.employees'))


@bp.route('/employees/<int:employee_id>/delete', methods=['POST'])
@require_roles(ROLES["ADMIN"])
def employee_delete(employee_id):
    """従業員削除"""
    tenant_id = session.get('tenant_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # テナントIDの確認
    cur.execute(_sql(conn, 'SELECT name FROM "T_従業員" WHERE id = %s AND tenant_id = %s'),
               (employee_id, tenant_id))
    row = cur.fetchone()
    
    if not row:
        flash('従業員が見つかりません', 'error')
    else:
        cur.execute(_sql(conn, 'DELETE FROM "T_従業員" WHERE id = %s'), (employee_id,))
        conn.commit()
        flash(f'{row[0]} を削除しました', 'success')
    
    conn.close()
    return redirect(url_for('admin.employees'))
