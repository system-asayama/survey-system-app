# -*- coding: utf-8 -*-
"""
管理者認証システム
POSシステムと同じログイン方式を採用
"""

import json
import os
from datetime import datetime
from flask import session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
ADMINS_PATH = os.path.join(DATA_DIR, "admins.json")

def load_admins():
    """管理者データを読み込む"""
    if not os.path.exists(ADMINS_PATH):
        # デフォルト管理者を作成
        default_admin = [{
            "id": 1,
            "store_code": "default",
            "login_id": "admin",
            "password_hash": generate_password_hash("admin123"),
            "name": "管理者",
            "email": "admin@example.com",
            "active": True,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }]
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ADMINS_PATH, "w", encoding="utf-8") as f:
            json.dump(default_admin, f, ensure_ascii=False, indent=2)
        return default_admin
    
    with open(ADMINS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_admins(admins):
    """管理者データを保存"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ADMINS_PATH, "w", encoding="utf-8") as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

def authenticate_admin(store_code, login_id, password):
    """
    管理者認証
    POSシステムと同じ方式: 店舗コード + ログインID + パスワード
    """
    admins = load_admins()
    
    for admin in admins:
        if (admin.get("store_code") == store_code and 
            admin.get("login_id") == login_id and 
            admin.get("active", True)):
            
            if check_password_hash(admin["password_hash"], password):
                # ログイン成功 - 最終ログイン時刻を更新
                admin["last_login"] = datetime.now().isoformat()
                save_admins(admins)
                return admin
    
    return None

def login_admin_session(admin):
    """管理者セッションを確立"""
    session.clear()
    session["logged_in"] = True
    session["admin_id"] = admin["id"]
    session["admin_name"] = admin["name"]
    session["store_code"] = admin["store_code"]
    session["login_id"] = admin["login_id"]

def logout_admin_session():
    """管理者セッションをクリア"""
    session.clear()

def is_admin_logged_in():
    """管理者がログインしているか確認"""
    return session.get("logged_in", False) and session.get("admin_id") is not None

def require_admin_login(f):
    """管理者ログインが必要なルートのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            flash("ログインが必要です", "error")
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_admin():
    """現在ログイン中の管理者情報を取得"""
    if not is_admin_logged_in():
        return None
    
    admin_id = session.get("admin_id")
    admins = load_admins()
    
    for admin in admins:
        if admin["id"] == admin_id:
            return admin
    
    return None
