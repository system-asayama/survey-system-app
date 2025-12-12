# -*- coding: utf-8 -*-
"""
アンケート機能 Blueprint
"""
from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for
import os
import json
from datetime import datetime
from openai import OpenAI

bp = Blueprint('survey', __name__)

# OpenAI クライアント初期化
openai_client = OpenAI()

# パス設定
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
SURVEY_DATA_PATH = os.path.join(DATA_DIR, "survey_responses.json")

def _load_google_review_url():
    """settings.jsonからGoogle口コミURLを読み込み"""
    settings_path = os.path.join(DATA_DIR, "settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return settings.get("google_review_url", "#")
        except:
            pass
    return "#"

def _load_survey_responses():
    """アンケート回答データを読み込み"""
    if not os.path.exists(SURVEY_DATA_PATH):
        return []
    with open(SURVEY_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_survey_response(response_data):
    """アンケート回答データを保存"""
    os.makedirs(DATA_DIR, exist_ok=True)
    responses = _load_survey_responses()
    response_data['timestamp'] = datetime.now().isoformat()
    response_data['id'] = len(responses) + 1
    responses.append(response_data)
    with open(SURVEY_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)

def _generate_review_text(survey_data):
    """
    アンケートデータからAIを使って口コミ投稿文を生成
    """
    rating = survey_data.get('rating', 3)
    visit_purpose = survey_data.get('visit_purpose', '')
    atmosphere = ', '.join(survey_data.get('atmosphere', []))
    recommend = survey_data.get('recommend', '')
    comment = survey_data.get('comment', '')
    
    # プロンプト作成
    prompt = f"""以下のアンケート回答から、自然で読みやすいお店の口コミ投稿文を日本語で作成してください。

【アンケート内容】
- 総合評価: {rating}つ星
- 訪問目的: {visit_purpose}
- お店の雰囲気: {atmosphere}
- おすすめ度: {recommend}
- 自由コメント: {comment if comment else 'なし'}

【要件】
- 200文字程度で簡潔にまとめる
- 自然な口語体で書く
- 具体的な体験を含める
- {rating}つ星の評価に相応しいトーンで書く
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
        # エラー時はデフォルトの文章を返す
        return f"{visit_purpose}で訪問しました。{atmosphere}な雰囲気で、{recommend}と思います。{comment}"


# ===== ルート =====
@bp.get("/")
def index():
    """トップページ：アンケート未回答の場合はアンケートページへ"""
    if not session.get('survey_completed'):
        return redirect(url_for('survey.survey'))
    return redirect(url_for('survey.slot_page'))

@bp.get("/survey")
def survey():
    """アンケートページ"""
    survey_config_path = os.path.join(DATA_DIR, "survey_config.json")
    
    if os.path.exists(survey_config_path):
        with open(survey_config_path, "r", encoding="utf-8") as f:
            survey_config = json.load(f)
    else:
        # デフォルト設定
        survey_config = {
            "title": "お店アンケート",
            "description": "ご来店ありがとうございます！",
            "questions": [
                {
                    "id": 1,
                    "text": "総合評価",
                    "type": "rating",
                    "required": True
                },
                {
                    "id": 2,
                    "text": "訪問目的",
                    "type": "radio",
                    "required": True,
                    "options": ["食事", "カフェ", "買い物", "その他"]
                },
                {
                    "id": 3,
                    "text": "お店の雰囲気（複数選択可）",
                    "type": "checkbox",
                    "required": False,
                    "options": ["静か", "賑やか", "落ち着く", "おしゃれ", "カジュアル"]
                },
                {
                    "id": 4,
                    "text": "おすすめ度",
                    "type": "radio",
                    "required": True,
                    "options": ["ぜひおすすめしたい", "おすすめしたい", "どちらでもない", "おすすめしない"]
                },
                {
                    "id": 5,
                    "text": "ご感想・ご意見（任意）",
                    "type": "text",
                    "required": False
                }
            ]
        }
    
    return render_template("survey.html", survey_config=survey_config)

@bp.get("/review_confirm")
def review_confirm():
    """口コミ確認ページ"""
    if not session.get('survey_completed'):
        return redirect(url_for('survey.survey'))
    
    rating = session.get('survey_rating', 3)
    generated_review = session.get('generated_review', '')
    google_review_url = _load_google_review_url()
    
    return render_template(
        "review_confirm.html",
        rating=rating,
        generated_review=generated_review,
        google_review_url=google_review_url
    )

@bp.post("/submit_survey")
def submit_survey():
    """アンケート送信"""
    body = request.get_json(silent=True) or {}
    
    # バリデーション
    required_fields = ['rating', 'visit_purpose', 'atmosphere', 'recommend']
    for field in required_fields:
        if field not in body or not body[field]:
            return jsonify({"ok": False, "error": f"{field}は必須項目です"}), 400
    
    rating = body.get('rating', 3)
    
    # 星4以上の場合のみAI投稿文を生成
    if rating >= 4:
        generated_review = _generate_review_text(body)
        body['generated_review'] = generated_review
    else:
        # 星3以下の場合はAI生成をスキップ
        generated_review = ''
        body['generated_review'] = ''
    
    # アンケートデータを保存
    _save_survey_response(body)
    
    # セッションにアンケート完了フラグと評価を設定
    session['survey_completed'] = True
    session['survey_timestamp'] = datetime.now().isoformat()
    session['survey_rating'] = rating
    session['generated_review'] = generated_review
    
    # 星3以下の場合は直接スロットページへ
    if rating <= 3:
        return jsonify({
            "ok": True, 
            "message": "貴重なご意見をありがとうございます。社内で改善に活用させていただきます。",
            "rating": rating,
            "redirect_url": url_for('survey.slot_page')
        })
    
    # 星4以上の場合は口コミ確認ページへ
    return jsonify({
        "ok": True, 
        "message": "アンケートを受け付けました",
        "rating": rating,
        "generated_review": generated_review,
        "redirect_url": url_for('survey.review_confirm')
    })

@bp.post("/reset_survey")
def reset_survey():
    """アンケートをリセット"""
    session.pop('survey_completed', None)
    session.pop('survey_timestamp', None)
    session.pop('survey_rating', None)
    session.pop('generated_review', None)
    return jsonify({"ok": True, "message": "アンケートをリセットしました"})

@bp.get("/slot")
def slot_page():
    """スロットページ"""
    if not session.get('survey_completed'):
        return redirect(url_for('survey.survey'))
    
    # 設定ファイルからメッセージと景品データを読み込み
    settings_path = os.path.join(DATA_DIR, "settings.json")
    survey_complete_message = "アンケートにご協力いただきありがとうございます！スロットをお楽しみください。"
    prizes = []
    
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            survey_complete_message = settings.get("survey_complete_message", survey_complete_message)
            prizes = settings.get("prizes", [])
    
    return render_template("slot.html", survey_complete_message=survey_complete_message, prizes=prizes)

@bp.get("/demo")
def demo_page():
    """デモプレイページ：アンケートなしでスロットを何度でもプレイ可能"""
    settings_path = os.path.join(DATA_DIR, "settings.json")
    prizes = []
    
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            prizes = settings.get("prizes", [])
    
    return render_template("demo.html", prizes=prizes)
