# -*- coding: utf-8 -*-
"""
アンケート機能 Blueprint
"""
from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for, g
from functools import wraps
import os
import sys

# store_dbをインポート
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import store_db

bp = Blueprint('survey', __name__)

# ===== 店舗識別ミドルウェア =====
@bp.url_value_preprocessor
def pull_store_slug(endpoint, values):
    """URLから店舗slugを取得してgに保存"""
    if values and 'store_slug' in values:
        g.store_slug = values.pop('store_slug')
        store = store_db.get_store_by_slug(g.store_slug)
        if store:
            g.store = store
            g.store_id = store['id']
        else:
            g.store = None
            g.store_id = None
    else:
        g.store_slug = None
        g.store = None
        g.store_id = None

def require_store(f):
    """店舗が必須のルートで使用するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.store:
            return "店舗が見つかりません", 404
        return f(*args, **kwargs)
    return decorated_function

# OpenAI クライアントを動的に取得する関数
def get_openai_client(app_type=None, app_id=None, store_id=None, tenant_id=None):
    """
    OpenAIクライアントを階層的に取得。
    優先順位: アプリ設定 > 店舗設定 > テナント設定 > 環境変数
    """
    from openai import OpenAI
    api_key = None
    
    try:
        conn = store_db.get_db_connection()
        cursor = conn.cursor()
        
        # 1. アプリ設定のキーを確認
        if app_type and app_id:
            if app_type == 'survey':
                cursor.execute("SELECT openai_api_key, store_id FROM T_店舗_アンケート設定 WHERE id = ?", (app_id,))
            elif app_type == 'slot':
                cursor.execute("SELECT openai_api_key, store_id FROM T_店舗_スロット設定 WHERE id = ?", (app_id,))
            
            result = cursor.fetchone()
            if result:
                if result[0]:  # アプリにAPIキーが設定されている
                    api_key = result[0]
                    conn.close()
                    return OpenAI(api_key=api_key)
                # アプリにキーがない場合、store_idを取得
                if not store_id and result[1]:
                    store_id = result[1]
        
        # 2. 店舗設定のキーを確認
        if store_id:
            cursor.execute("SELECT openai_api_key, tenant_id FROM T_店舗 WHERE id = ?", (store_id,))
            result = cursor.fetchone()
            if result:
                if result[0]:  # 店舗にAPIキーが設定されている
                    api_key = result[0]
                    conn.close()
                    return OpenAI(api_key=api_key)
                # 店舗にキーがない場合、tenant_idを取得
                if not tenant_id and result[1]:
                    tenant_id = result[1]
        
        # 3. テナント設定のキーを確認
        if tenant_id:
            cursor.execute("SELECT openai_api_key FROM T_テナント WHERE id = ?", (tenant_id,))
            result = cursor.fetchone()
            if result and result[0]:
                api_key = result[0]
                conn.close()
                return OpenAI(api_key=api_key)
        
        conn.close()
    except Exception as e:
        print(f"Error getting OpenAI API key from database: {e}")
    
    # 4. 環境変数を確認
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("OpenAI APIキーが設定されていません。アプリ、店舗、またはテナントの管理画面でAPIキーを設定してください。")
    
    return OpenAI(api_key=api_key)

def _generate_review_text(survey_data, store_id):
    """
    アンケートデータからAIを使って口コミ投稿文を生成
    """
    # アンケートアプリIDを取得
    survey_app_id = None
    try:
        conn = store_db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM T_店舗_アンケート設定 WHERE store_id = ?", (store_id,))
        result = cursor.fetchone()
        if result:
            survey_app_id = result[0]
        conn.close()
    except Exception as e:
        print(f"Error getting survey app ID: {e}")
    
    # OpenAIクライアントを取得
    try:
        openai_client = get_openai_client(
            app_type='survey',
            app_id=survey_app_id,
            store_id=store_id
        )
    except Exception as e:
        print(f"Error getting OpenAI client: {e}")
        return "口コミ投稿文の生成に失敗しました。"
    
    # アンケートデータから情報を抽出
    rating = 5  # デフォルト
    answers = []
    
    for key, value in survey_data.items():
        if key.startswith('q'):
            if isinstance(value, list):
                answers.append(', '.join(value))
            else:
                answers.append(str(value))
    
    answers_text = '\n- '.join(answers)
    
    # プロンプト作成
    prompt = f"""以下のアンケート回答から、自然で読みやすいお店の口コミ投稿文を日本語で作成してください。

【アンケート回答】
- {answers_text}

【要件】
- 200文字程度で簡潔にまとめる
- 自然な口語体で書く
- 具体的な体験を含める
- 「です・ます」調で統一する

口コミ投稿文:"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "あなたは自然で読みやすい口コミ投稿文を作成する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating review text: {e}")
        return "口コミ投稿文の生成に失敗しました。"


# ===== ルート =====
@bp.get("/store/<store_slug>")
@require_store
def store_index():
    """店舗トップ - アンケートへリダイレクト"""
    # アンケート未回答の場合はアンケートページへ
    if not session.get(f'survey_completed_{g.store_id}'):
        return redirect(url_for('survey.survey', store_slug=g.store_slug))
    return redirect(url_for('slot.slot_page', store_slug=g.store_slug))

@bp.get("/store/<store_slug>/survey")
@require_store
def survey():
    """アンケートページ"""
    print(f"DEBUG: survey() called, store_id={g.store_id}, store={g.store}")
    survey_config = store_db.get_survey_config(g.store_id)
    print(f"DEBUG: survey_config={survey_config}")
    return render_template("survey.html", 
                         store=g.store,
                         survey_config=survey_config)

@bp.post("/store/<store_slug>/submit_survey")
@require_store
def submit_survey():
    """アンケート送信"""
    body = request.get_json(silent=True) or {}
    
    # 最初の質問の回答を評価として使用（５段階評価の場合）
    rating = 3  # デフォルト
    first_answer = body.get('q1', '')
    if '非常に満足' in first_answer or '強く思う' in first_answer or '非常に良い' in first_answer:
        rating = 5
    elif '満足' in first_answer or '思う' in first_answer or '良い' in first_answer:
        rating = 4
    elif '普通' in first_answer or 'どちらとも' in first_answer:
        rating = 3
    elif 'やや' in first_answer:
        rating = 2
    else:
        rating = 1
    
    # ratingをbodyに追加
    body['rating'] = rating
    
    # アンケート回答を保存
    store_db.save_survey_response(g.store_id, body)
    
    # 星4以上の場合のみAI投稿文を生成
    generated_review = ''
    if rating >= 4:
        try:
            generated_review = _generate_review_text(body, g.store_id)
        except Exception as e:
            print(f"Error generating review: {e}")
    
    # セッションにアンケート完了フラグと評価を設定
    session[f'survey_completed_{g.store_id}'] = True
    session[f'survey_rating_{g.store_id}'] = rating
    session[f'generated_review_{g.store_id}'] = generated_review
    
    # 星3以下の場合はメッセージを表示
    if rating <= 3:
        return jsonify({
            "ok": True, 
            "message": "貴重なご意見をありがとうございます。社内で改善に活用させていただきます。",
            "rating": rating
        })
    
    # 星4以上の場合は口コミ投稿文を表示
    return jsonify({
        "ok": True, 
        "message": "アンケートにご協力いただきありがとうございます！",
        "rating": rating,
        "generated_review": generated_review
    })

@bp.post("/store/<store_slug>/reset_survey")
@require_store
def reset_survey():
    """アンケートをリセット"""
    session.pop(f'survey_completed_{g.store_id}', None)
    session.pop(f'survey_rating_{g.store_id}', None)
    session.pop(f'generated_review_{g.store_id}', None)
    return jsonify({"ok": True, "message": "アンケートをリセットしました"})
