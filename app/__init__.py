from __future__ import annotations
import os
from flask import Flask

def create_app() -> Flask:
    """
    Flaskアプリケーションを生成して返します。
    survey-system-app + login-system-app統合版
    """
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')

    # SECRET_KEY設定
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # デフォルト設定を読み込み
    app.config.update(
        APP_NAME=os.getenv("APP_NAME", "survey-system-app"),
        ENVIRONMENT=os.getenv("ENV", "dev"),
        DEBUG=os.getenv("DEBUG", "1") in ("1", "true", "True"),
        VERSION=os.getenv("APP_VERSION", "0.1.0"),
        TZ=os.getenv("TZ", "Asia/Tokyo"),
    )

    # config.py があれば上書き
    try:
        from .config import settings  # type: ignore
        app.config.update(
            ENVIRONMENT=getattr(settings, "ENV", app.config["ENVIRONMENT"]),
            DEBUG=getattr(settings, "DEBUG", app.config["DEBUG"]),
            VERSION=getattr(settings, "VERSION", app.config["VERSION"]),
            TZ=getattr(settings, "TZ", app.config["TZ"]),
        )
    except Exception:
        pass

    # logging.py があればロガーを初期化
    try:
        from .logging import setup_logging  # type: ignore
        setup_logging(debug=app.config["DEBUG"])
    except Exception:
        pass

    # CSRF トークンをテンプレートで使えるようにする
    @app.context_processor
    def inject_csrf():
        from .utils import get_csrf
        return {"get_csrf": get_csrf}

    # データベース初期化
    try:
        from .utils import get_db
        conn = get_db()
        try:
            conn.close()
        except:
            pass
        print("✅ データベース初期化完了")
    except Exception as e:
        print(f"⚠️ データベース初期化エラー: {e}")

    # blueprints 登録
    try:
        from .blueprints.health import bp as health_bp
        app.register_blueprint(health_bp)
    except Exception:
        pass

    # 認証関連blueprints
    try:
        from .blueprints.auth import bp as auth_bp
        app.register_blueprint(auth_bp)
    except Exception as e:
        print(f"⚠️ auth blueprint 登録エラー: {e}")

    try:
        from .blueprints.system_admin import bp as system_admin_bp
        app.register_blueprint(system_admin_bp)
    except Exception as e:
        print(f"⚠️ system_admin blueprint 登録エラー: {e}")

    try:
        from .blueprints.tenant_admin import bp as tenant_admin_bp
        app.register_blueprint(tenant_admin_bp)
    except Exception as e:
        print(f"⚠️ tenant_admin blueprint 登録エラー: {e}")

    # login-systemのadmin blueprintを有効化
    try:
        from .blueprints.admin import bp as admin_bp
        app.register_blueprint(admin_bp)
    except Exception as e:
        print(f"⚠️ admin blueprint 登録エラー: {e}")

    try:
        from .blueprints.employee import bp as employee_bp
        app.register_blueprint(employee_bp)
    except Exception as e:
        print(f"⚠️ employee blueprint 登録エラー: {e}")

    # survey-system-app の既存機能をBlueprintとして登録
    try:
        from .blueprints.survey import bp as survey_bp
        app.register_blueprint(survey_bp)
    except Exception as e:
        print(f"⚠️ survey blueprint 登録エラー: {e}")

    try:
        from .blueprints.slot import bp as slot_bp
        app.register_blueprint(slot_bp)
    except Exception as e:
        print(f"⚠️ slot blueprint 登録エラー: {e}")

    try:
        from .blueprints.survey_admin import bp as survey_admin_bp
        app.register_blueprint(survey_admin_bp)
    except Exception as e:
        print(f"⚠️ survey_admin blueprint 登録エラー: {e}")

    # スタンプカード機能
    try:
        from .blueprints.stampcard import stampcard_bp
        app.register_blueprint(stampcard_bp)
        print("✅ Stamp Card Blueprint登録完了")
    except Exception as e:
        print(f"⚠️ Stamp Card Blueprint登録エラー: {e}")

    try:
        from .blueprints.stampcard_admin import stampcard_admin_bp
        app.register_blueprint(stampcard_admin_bp)
        print("✅ Stamp Card Admin Blueprint登録完了")
    except Exception as e:
        print(f"⚠️ Stamp Card Admin Blueprint登録エラー: {e}")

    # 予約システム機能
    try:
        from .blueprints.reservation import reservation_bp
        app.register_blueprint(reservation_bp)
        print("✅ Reservation Blueprint登録完了")
    except Exception as e:
        print(f"⚠️ Reservation Blueprint登録エラー: {e}")

    try:
        from .blueprints.reservation_admin import reservation_admin_bp
        app.register_blueprint(reservation_admin_bp)
        print("✅ Reservation Admin Blueprint登録完了")
    except Exception as e:
        print(f"⚠️ Reservation Admin Blueprint登録エラー: {e}")

    # 店舗スロット設定ルート
    try:
        import sys
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        from store_slot_settings_routes import register_store_slot_settings_routes
        register_store_slot_settings_routes(app)
        print("✅ 店舗スロット設定ルート登録完了")
    except Exception as e:
        print(f"⚠️ 店舗スロット設定ルート登録エラー: {e}")

    # QR印刷ルート
    try:
        from qr_print_routes import register_qr_print_routes
        register_qr_print_routes(app)
        print("✅ QR印刷ルート登録完了")
    except Exception as e:
        print(f"⚠️ QR印刷ルート登録エラー: {e}")

    # エラーハンドラ
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('500.html'), 500

    return app
