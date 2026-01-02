"""
口コミ再生成API
"""
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import os
import sys

# store_dbをインポート
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import store_db
from openai import OpenAI

bp = Blueprint('review_regenerate', __name__)

# ===== 店舗識別ミドルウェア =====
@bp.url_value_preprocessor
def pull_store_slug(endpoint, values):
    """からURLから店舗slugを取得してgに保存"""
    store_slug = None
    if values and 'store_slug' in values:
        store_slug = values.pop('store_slug')
    elif hasattr(request, 'view_args') and request.view_args and 'store_slug' in request.view_args:
        store_slug = request.view_args.get('store_slug')
    
    if store_slug:
        g.store_slug = store_slug
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
    """店舗情報が必要なエンドポイント用デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'store') or g.store is None:
            return jsonify({"ok": False, "error": "店舗が見つかりません"}), 404
        return f(*args, **kwargs)
    return decorated_function


def get_openai_client(app_type='survey', app_id=None, store_id=None):
    """
    OpenAIクライアントを取得
    優先順位: アプリ設定 > 店舗設定 > テナント設定
    """
    api_key = None
    
    # 1. アプリ設定からAPIキーを取得
    if app_id:
        try:
            conn = store_db.get_db_connection()
            cursor = conn.cursor()
            if app_type == 'survey':
                from db_config import execute_query
            execute_query(cursor, "SELECT openai_api_key FROM T_店舗_アンケート設定 WHERE id = ?", (app_id,))
            result = cursor.fetchone()
            if result and result[0]:
                api_key = result[0]
            conn.close()
        except Exception as e:
            print(f"Error getting app API key: {e}")
    
    # 2. 店舗設定からAPIキーを取得
    if not api_key and store_id:
        try:
            conn = store_db.get_db_connection()
            cursor = store_db.get_cursor(conn)
            from db_config import execute_query
            execute_query(cursor, "SELECT openai_api_key FROM T_店舗 WHERE id = ?", (store_id,))
            result = cursor.fetchone()
            if result and result[0]:
                api_key = result[0]
            conn.close()
        except Exception as e:
            print(f"Error getting store API key: {e}")
    
    # 3. テナント設定からAPIキーを取得
    if not api_key and store_id:
        try:
            conn = store_db.get_db_connection()
            cursor = store_db.get_cursor(conn)
            from db_config import execute_query
            execute_query(cursor, """
                SELECT t.openai_api_key 
                FROM T_テナント t
                JOIN T_店舗 s ON s.tenant_id = t.id
                WHERE s.id = ?
            """, (store_id,))
            result = cursor.fetchone()
            if result and result[0]:
                api_key = result[0]
            conn.close()
        except Exception as e:
            print(f"Error getting tenant API key: {e}")
    
    if not api_key:
        raise ValueError("OpenAI APIキーが設定されていません。")
    
    return OpenAI(api_key=api_key, base_url='https://api.openai.com/v1')


# テイスト別のプロンプト設定
TASTE_PROMPTS = {
    'polite': {
        'name': '丁寧',
        'system_addition': """
文体は非常に丁寧で落ち着いた表現を使ってください。
- 「大変」「非常に」「誠に」などの丁寧な表現を使う
- 「です・ます」調を徹底する
- 敬語を適切に使用する
- 落ち着いた印象を与える
例：「大変満足いたしました」「非常に美味しく頂戴しました」
"""
    },
    'casual': {
        'name': 'カジュアル',
        'system_addition': """
文体はカジュアルで親しみやすい表現を使ってください。
- 「めっちゃ」「すごく」「かなり」「本当に」などの口語的な表現を使う
- 「です・ます」調だが親しみやすいトーンにする
- 絵文字は使わない
- 友人に話すような自然な表現
例：「めっちゃ美味しかったです」「すごく良かったです」
"""
    },
    'enthusiastic': {
        'name': '熱量高め',
        'system_addition': """
文体は熱量が高く、感動や興奮が伝わる表現を使ってください。
- 「最高」「素晴らしい」「感動」「また絶対来たい」などの強い表現を使う
- 感嘆符を適度に使用する（使いすぎない）
- ポジティブな感情を前面に出す
- 「です・ます」調を基本とする
例：「本当に最高でした！」「感動しました」「また絶対来たいです！」
"""
    },
    'concise': {
        'name': '簡潔',
        'system_addition': """
文体は簡潔で要点を押さえた表現を使ってください。
- 150～180文字程度で短くまとめる
- 無駄な表現を省き、要点だけを伝える
- シンプルで分かりやすい文章にする
- 「です・ます」調を基本とする
例：「料理が美味しく、サービスも良かったです。また利用したいと思います。」
"""
    },
    'balanced': {
        'name': 'バランス型',
        'system_addition': """
文体は丁寧さと親しみやすさのバランスが取れた表現を使ってください。
- 「とても」「かなり」「非常に」などの適度な表現を使う
- 「です・ます」調で統一する
- 自然で読みやすい文章にする
- 極端な表現は避ける
例：「とても美味しかったです」「かなり満足しました」
"""
    }
}


def _generate_review_with_taste(survey_data, store_id, taste='balanced'):
    """
    アンケートデータからAIを使って口コミ投稿文を生成（テイスト指定可能）
    """
    # アンケートアプリIDを取得
    survey_app_id = None
    try:
        conn = store_db.get_db_connection()
        cursor = store_db.get_cursor(conn)
        from db_config import execute_query
        execute_query(cursor, "SELECT id FROM T_店舗_アンケート設定 WHERE store_id = ?", (store_id,))
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
    
    # アンケート設定を取得して質問文を取得
    survey_config = None
    try:
        conn = store_db.get_db_connection()
        cursor = store_db.get_cursor(conn)
        from db_config import execute_query
        execute_query(cursor, "SELECT config_json FROM T_店舗_アンケート設定 WHERE store_id = ?", (store_id,))
        result = cursor.fetchone()
        if result and result[0]:
            import json
            survey_config = json.loads(result[0])
        conn.close()
    except Exception as e:
        print(f"Error getting survey config: {e}")
    
    # アンケート回答を質問と結びつけて整形
    qa_pairs = []
    
    if survey_config and 'questions' in survey_config:
        questions = survey_config['questions']
        for i, question in enumerate(questions):
            question_id = f"q{i+1}"
            if question_id in survey_data:
                answer = survey_data[question_id]
                question_text = question.get('text', '')
                
                # 回答を整形
                if isinstance(answer, list):
                    answer_text = '、'.join(answer)
                elif question.get('type') == 'rating':
                    answer_text = f"{answer}点（5点満点）"
                else:
                    answer_text = str(answer)
                
                qa_pairs.append(f"質問: {question_text}\n回答: {answer_text}")
    else:
        # 設定がない場合は従来通り
        for key, value in survey_data.items():
            if key.startswith('q'):
                if isinstance(value, list):
                    qa_pairs.append(', '.join(value))
                else:
                    qa_pairs.append(str(value))
    
    qa_text = '\n\n'.join(qa_pairs)
    
    # テイスト設定を取得
    taste_config = TASTE_PROMPTS.get(taste, TASTE_PROMPTS['balanced'])
    
    # プロンプト作成
    prompt = f"""以下のアンケート回答から、実際の人間が書いたような自然な口コミ投稿文を日本語で作成してください。

【アンケート回答】
{qa_text}

【絶対に守るべきルール】
1. 上記のすべての質問と回答を考慮してください
2. 「○○がおいしい」「特に○○が印象的」「おすすめの一品」のような曖昧な表現は絶対に使わないでください
3. 料理やメニューについて言及する場合は、必ず具体的な名前（例：ハラミ、ホルモン、カルビなど）を使ってください
4. 回答に具体的な料理名が含まれている場合は、それを曖昧な表現に置き換えず、そのまま使ってください
5. 例：「ハラミ」と回答されている場合→「ハラミが美味しかった」と書く（「おすすめの一品」と書かない）
6. 自由記入欄に肯定的な文言があれば積極的に活用してください
7. 自由記入欄に「○○」のような曖昧な表現があれば、その部分を省略するか、他の質問の回答から具体的な名前を探して使ってください
8. AIが書いたと分からないよう、自然な言い回しや表現を使ってください

【要件】
- 180～220文字程度で簡潔にまとめる（簡潔モードの場合は150～180文字）
- 自然な口語体で書く
- 具体的な体験を含める
- 句読点や改行を適度に使って読みやすくする

口コミ投稿文:"""
    
    try:
        sys.stderr.write(f"DEBUG: 口コミ再生成 (taste={taste})\n")
        sys.stderr.flush()
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": f"""あなたは実際の人間が書いたような自然な口コミ投稿文を作成する専門家です。

絶対に守るべきルール:
1. すべてのアンケート回答を考慮してください
2. 「○○がおいしい」「特に○○が印象的」「おすすめの一品」のような曖昧な表現は絶対に使わないでください
3. 料理やメニューについて言及する場合は、必ず具体的な名前（例：ハラミ、ホルモン、カルビ）を使ってください
4. 回答に具体的な料理名が含まれている場合は、それを曖昧な表現に置き換えず、そのまま使ってください
5. 例：「ハラミ」と回答→「ハラミが美味しかった」（「おすすめの一品」と書かない）
6. 自由記入欄に肯定的な文言があれば積極的に活用してください
7. 自由記入欄に「○○」のような曖昧な表現があれば、他の質問の回答から具体的な名前を探して使ってください
8. AIが書いたと分からないよう、自然な言い回しや表現を使ってください

{taste_config['system_addition']}"""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # 再生成時は少し高めに設定してバリエーションを出す
            max_tokens=500
        )
        
        generated_text = response.choices[0].message.content.strip()
        
        sys.stderr.write(f"DEBUG: 生成完了 (taste={taste}): {generated_text[:100]}...\n")
        sys.stderr.flush()
        
        return generated_text
    except Exception as e:
        sys.stderr.write(f"ERROR: 口コミ生成失敗: {e}\n")
        sys.stderr.flush()
        return "口コミ投稿文の生成に失敗しました。"


@bp.post("/store/<store_slug>/regenerate_review")
@require_store
def regenerate_review():
    """口コミを再生成するAPIエンドポイント"""
    try:
        data = request.get_json() or {}
        taste = data.get('taste', 'balanced')
        
        # アンケート回答をセッションから取得
        survey_data = session.get(f'survey_data_{g.store_id}')
        
        if not survey_data:
            return jsonify({
                "ok": False,
                "error": "アンケートデータが見つかりません。再度アンケートを送信してください。"
            }), 404
        
        # 口コミを再生成
        generated_review = _generate_review_with_taste(survey_data, g.store_id, taste)
        
        # セッションに保存
        session[f'generated_review_{g.store_id}'] = generated_review
        
        return jsonify({
            "ok": True,
            "generated_review": generated_review,
            "taste": taste
        })
        
    except Exception as e:
        sys.stderr.write(f"ERROR regenerate_review: {e}\n")
        import traceback
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500
