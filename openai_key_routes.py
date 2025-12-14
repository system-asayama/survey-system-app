from flask import Blueprint, request, redirect, url_for, flash, session
from store_db import get_db_connection

openai_key_bp = Blueprint('openai_key', __name__)

@openai_key_bp.route('/admin/save_openai_key', methods=['POST'])
def save_openai_key():
    """OpenAI APIキーを保存"""
    if 'user_id' not in session:
        return redirect(url_for('auth.select_login'))
    
    openai_api_key = request.form.get('openai_api_key', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 現在のログインユーザーの店舗IDをT_管理者_店舗テーブルから取得
        cursor.execute("""
            SELECT store_id FROM T_管理者_店舗 WHERE admin_id = ? LIMIT 1
        """, (session['user_id'],))
        result = cursor.fetchone()
        
        if not result:
            flash('店舗情報が見つかりません', 'error')
            return redirect(request.referrer or url_for('admin.dashboard'))
        
        store_id = result[0]
        
        # OpenAI APIキーを更新
        cursor.execute("""
            UPDATE T_店舗
            SET openai_api_key = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (openai_api_key if openai_api_key else None, store_id))
        
        conn.commit()
        conn.close()
        
        flash('OpenAI APIキーを保存しました', 'success')
        
    except Exception as e:
        print(f"Error saving OpenAI API key: {e}")
        flash('APIキーの保存に失敗しました', 'error')
    
    return redirect(url_for('store_slot_settings', store_id=store_id))
