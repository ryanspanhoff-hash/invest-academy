import os
from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from app.extensions import db, login_manager, limiter


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Render sits behind a reverse proxy: without this, request.remote_addr
    # (and anything keyed on it, like rate limiting) sees the proxy's IP for
    # every visitor instead of each person's real one.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

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

    @app.errorhandler(404)
    def not_found(e):
        return render_template(
            "errors/error.html", code=404, emoji="🔍",
            heading="Page not found",
            message="That page doesn't exist — it may have moved, or the link might be off.",
        ), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template(
            "errors/error.html", code=429, emoji="⏳",
            heading="Slow down a little",
            message="You've hit a rate limit meant to keep the site safe from abuse. Try again in a bit.",
        ), 429

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template(
            "errors/error.html", code=500, emoji="⚠️",
            heading="Something went wrong",
            message="That's on us, not you — please try again in a moment.",
        ), 500

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
    table_names = set(inspector.get_table_names())
    is_sqlite = db.engine.url.get_backend_name() == "sqlite"

    if "user" in table_names:
        columns = {c["name"] for c in inspector.get_columns("user")}
        if "is_admin" not in columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE'))

    # Widened for crypto tickers like "BTC-USD". SQLite doesn't enforce VARCHAR
    # length at all, so there's nothing to migrate there — only Postgres needs this.
    if not is_sqlite:
        for table in ("holding", "transaction"):
            if table not in table_names:
                continue
            columns = {c["name"]: c for c in inspector.get_columns(table)}
            symbol_col = columns.get("symbol")
            if symbol_col is not None and getattr(symbol_col["type"], "length", None) not in (None, 20):
                with db.engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE "{table}" ALTER COLUMN symbol TYPE VARCHAR(20)'))
