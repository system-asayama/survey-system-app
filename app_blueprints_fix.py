# ===== 管理画面用のインポート =====
# 既存の管理画面blueprintをインポート
try:
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.system_admin import bp as system_admin_bp
    from app.blueprints.tenant_admin import bp as tenant_admin_bp
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.employee import bp as employee_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_admin_bp)
    app.register_blueprint(tenant_admin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    
    print("✅ 管理画面blueprints登録完了")
except Exception as e:
    print(f"⚠️ 管理画面blueprints登録エラー: {e}")
    import traceback
    traceback.print_exc()
