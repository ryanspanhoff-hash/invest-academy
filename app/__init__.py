import os
from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.learning.routes import learning_bp
    from app.practice.routes import practice_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(learning_bp, url_prefix="/learning")
    app.register_blueprint(practice_bp, url_prefix="/practice")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.practice.leveling import level_info_and_flash

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        ctx = {}
        if current_user.is_authenticated and current_user.portfolio:
            ctx["nav_level_info"] = level_info_and_flash(current_user.portfolio)
        return ctx

    with app.app_context():
        db.create_all()
        _run_light_migrations()

    return app


def _run_light_migrations():
    """This app has no formal migration system (db.create_all() only creates
    missing tables, not new columns on existing ones), so new columns are
    added here in a small, idempotent, cross-DB-safe way."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("user")}
    if "is_admin" not in columns:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE'))
