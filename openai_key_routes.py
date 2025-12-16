from flask import Blueprint, request, redirect, url_for, flash, session
from store_db import get_db_connection

openai_key_bp = Blueprint('openai_key', __name__)

@openai_key_bp.route('/admin/save_openai_key', methods=['POST'])
def save_openai_key():
    """OpenAI APIキーを保存（アプリ個別）"""
    print("=== save_openai_key called ===")
    print(f"Session user_id: {session.get('user_id')}")
    
    if 'user_id' not in session:
        print("No user_id in session, redirecting to login")
        return redirect(url_for('auth.select_login'))
    
    openai_api_key = request.form.get('openai_api_key', '').strip()
    print(f"Received API key: {openai_api_key[:10]}..." if openai_api_key else "No API key received")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 現在のログインユーザーの店舗IDをT_管理者_店舗テーブルから取得
        cursor.execute("""
            SELECT store_id FROM T_管理者_店舗 WHERE admin_id = ? LIMIT 1
        """, (session['user_id'],))
        result = cursor.fetchone()
        
        if not result:
            print("Store not found for user")
            flash('店舗情報が見つかりません', 'error')
            conn.close()
            return redirect(request.referrer or url_for('admin.dashboard'))
        
        store_id = result[0]
        print(f"Store ID: {store_id}")
        
        # スロットアプリ設定のOpenAI APIキーを更新
        cursor.execute("""
            SELECT id FROM T_店舗_スロット設定 WHERE store_id = ?
        """, (store_id,))
        slot_result = cursor.fetchone()
        
        if slot_result:
            # 既存のスロット設定がある場合は更新
            print(f"Updating existing slot config (id={slot_result[0]})")
            cursor.execute("""
                UPDATE T_店舗_スロット設定
                SET openai_api_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE store_id = ?
            """, (openai_api_key if openai_api_key else None, store_id))
            print(f"Rows affected: {cursor.rowcount}")
        else:
            # スロット設定がない場合は新規作成
            print("Creating new slot config")
            cursor.execute("""
                INSERT INTO T_店舗_スロット設定 (store_id, openai_api_key, config_json)
                VALUES (?, ?, '{}')
            """, (store_id, openai_api_key if openai_api_key else None))
        
        conn.commit()
        print("Database commit successful")
        
        # 保存後の確認
        cursor.execute("""
            SELECT openai_api_key FROM T_店舗_スロット設定 WHERE store_id = ?
        """, (store_id,))
        verify_result = cursor.fetchone()
        print(f"Verification - saved key: {verify_result[0][:10]}..." if verify_result and verify_result[0] else "No key saved")
        
        conn.close()
        
        flash('OpenAI APIキーを保存しました', 'success')
        print("Flash message set")
        
    except Exception as e:
        print(f"Error saving OpenAI API key: {e}")
        import traceback
        traceback.print_exc()
        flash('APIキーの保存に失敗しました', 'error')
    
    # 正しいリダイレクト先に変更（元のページに戻る）
    redirect_url = request.referrer or url_for('admin.dashboard')
    print(f"Redirecting to: {redirect_url}")
    return redirect(redirect_url)
