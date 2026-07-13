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

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(learning_bp, url_prefix="/learning")
    app.register_blueprint(practice_bp, url_prefix="/practice")

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

    return app
