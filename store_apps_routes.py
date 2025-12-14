"""
店舗アプリ一覧ページのルート
"""
from flask import render_template, session
from app.utils.db import get_db_connection
from app.utils.auth import require_roles, ROLES


def register_store_apps_routes(app):
    """店舗アプリ一覧ページのルートを登録"""
    
    @app.route('/admin/store/<int:store_id>/apps')
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_apps(store_id):
        """店舗アプリ一覧ページ"""
        tenant_id = session.get('tenant_id')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 店舗情報を取得
        cur.execute('''
            SELECT id, store_name, store_code
            FROM "T_店舗"
            WHERE id = %s
        ''', (store_id,))
        
        store_row = cur.fetchone()
        conn.close()
        
        if not store_row:
            return "店舗が見つかりません", 404
        
        store = {
            'id': store_row[0],
            'store_name': store_row[1],
            'store_code': store_row[2]
        }
        
        return render_template('admin_store_apps.html', store=store)
