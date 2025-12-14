"""
店舗設定ルート（app.pyから直接インポート）
"""

from flask import render_template, request, redirect, url_for, flash, session
from app.utils import require_roles, ROLES, get_db_connection
from app.utils.db import _sql
import json


def register_store_settings_routes(app):
    """店舗設定ルートを登録"""
    
    @app.route('/admin/store_settings/')
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_settings_index():
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
            SELECT id, 名称, slug
            FROM "T_店舗" 
            WHERE tenant_id = %s 
            ORDER BY id
        '''), (tenant_id,))
        
        stores = []
        for row in cur.fetchall():
            stores.append({
                'id': row[0],
                'name': row[1],
                'slug': row[2]
            })
        
        conn.close()
        return render_template('store_settings/index.html', stores=stores)
    
    
    @app.route('/admin/store_settings/<int:store_id>/prizes')
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_settings_prizes(store_id):
        """景品設定ページ"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 店舗情報を取得
        cur.execute(_sql(conn, 'SELECT id, 名称, slug FROM "T_店舗" WHERE id = %s'), (store_id,))
        store_row = cur.fetchone()
        
        if not store_row:
            flash('店舗が見つかりません', 'error')
            conn.close()
            return redirect(url_for('store_settings_index'))
        
        store = {
            'id': store_row[0],
            'name': store_row[1],
            'slug': store_row[2]
        }
        
        # 景品設定をJSON形式で取得
        cur.execute(_sql(conn, '''
            SELECT prizes_json 
            FROM "T_店舗_景品設定" 
            WHERE store_id = %s
        '''), (store_id,))
        
        prizes_row = cur.fetchone()
        prizes = []
        
        if prizes_row and prizes_row[0]:
            try:
                prizes = json.loads(prizes_row[0])
            except:
                prizes = []
        
        conn.close()
        return render_template('store_settings/prizes.html', store=store, prizes=prizes)
    
    
    @app.route('/admin/store_settings/<int:store_id>/prizes/add', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_settings_add_prize(store_id):
        """景品追加"""
        label = request.form.get('label')
        min_val = request.form.get('min', type=float)
        max_val = request.form.get('max', type=float)
        
        if not label or min_val is None:
            flash('必須項目を入力してください', 'error')
            return redirect(url_for('store_settings_prizes', store_id=store_id))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 既存の景品設定を取得
        cur.execute(_sql(conn, 'SELECT prizes_json FROM "T_店舗_景品設定" WHERE store_id = %s'), (store_id,))
        prizes_row = cur.fetchone()
        
        prizes = []
        if prizes_row and prizes_row[0]:
            try:
                prizes = json.loads(prizes_row[0])
            except:
                prizes = []
        
        # 新しい景品を追加
        new_prize = {
            'label': label,
            'min': min_val,
            'max': max_val
        }
        prizes.append(new_prize)
        
        prizes_json = json.dumps(prizes, ensure_ascii=False)
        
        # 既存レコードがあれば更新、なければ挿入
        if prizes_row:
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
        
        flash('景品を追加しました', 'success')
        return redirect(url_for('store_settings_prizes', store_id=store_id))
    
    
    @app.route('/admin/store_settings/<int:store_id>/prizes/<int:prize_id>/delete', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_settings_delete_prize(store_id, prize_id):
        """景品削除"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 既存の景品設定を取得
        cur.execute(_sql(conn, 'SELECT prizes_json FROM "T_店舗_景品設定" WHERE store_id = %s'), (store_id,))
        prizes_row = cur.fetchone()
        
        if prizes_row and prizes_row[0]:
            try:
                prizes = json.loads(prizes_row[0])
                # 指定されたインデックスの景品を削除
                if 0 <= prize_id < len(prizes):
                    prizes.pop(prize_id)
                
                prizes_json = json.dumps(prizes, ensure_ascii=False)
                cur.execute(_sql(conn, '''
                    UPDATE "T_店舗_景品設定" 
                    SET prizes_json = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE store_id = %s
                '''), (prizes_json, store_id))
                
                conn.commit()
                flash('景品を削除しました', 'success')
            except:
                flash('景品の削除に失敗しました', 'error')
        
        conn.close()
        return redirect(url_for('store_settings_prizes', store_id=store_id))
    
    
    @app.route('/admin/store_settings/<int:store_id>/google_review')
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_settings_google_review(store_id):
        """Google口コミURL設定ページ"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 店舗情報を取得
        cur.execute(_sql(conn, 'SELECT id, 名称, slug FROM "T_店舗" WHERE id = %s'), (store_id,))
        store_row = cur.fetchone()
        
        if not store_row:
            flash('店舗が見つかりません', 'error')
            conn.close()
            return redirect(url_for('store_settings_index'))
        
        store = {
            'id': store_row[0],
            'name': store_row[1],
            'slug': store_row[2]
        }
        
        # Google口コミURL設定を取得（T_店舗_Google設定テーブルを使用）
        cur.execute(_sql(conn, '''
            SELECT review_url 
            FROM "T_店舗_Google設定" 
            WHERE store_id = %s
        '''), (store_id,))
        
        url_row = cur.fetchone()
        google_review_url = url_row[0] if url_row else ''
        
        conn.close()
        return render_template('store_settings/google_review.html', store=store, google_review_url=google_review_url)
    
    
    @app.route('/admin/store_settings/<int:store_id>/google_review/save', methods=['POST'])
    @require_roles(ROLES["ADMIN"], ROLES["TENANT_ADMIN"], ROLES["SYSTEM_ADMIN"])
    def store_settings_save_google_review(store_id):
        """Google口コミURL保存"""
        google_review_url = request.form.get('google_review_url', '').strip()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 既存の設定があるか確認
        cur.execute(_sql(conn, 'SELECT id FROM "T_店舗_Google設定" WHERE store_id = %s'), (store_id,))
        existing = cur.fetchone()
        
        if existing:
            # 更新
            cur.execute(_sql(conn, '''
                UPDATE "T_店舗_Google設定" 
                SET review_url = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE store_id = %s
            '''), (google_review_url, store_id))
        else:
            # 新規作成
            cur.execute(_sql(conn, '''
                INSERT INTO "T_店舗_Google設定" (store_id, review_url)
                VALUES (%s, %s)
            '''), (store_id, google_review_url))
        
        conn.commit()
        conn.close()
        
        flash('Google口コミURLを保存しました', 'success')
        return redirect(url_for('store_settings_google_review', store_id=store_id))
