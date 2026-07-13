import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _database_uri():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return "sqlite:///" + os.path.join(BASE_DIR, "instance", "invest_academy.db")
    # Neon/Render/Heroku-style URLs use the "postgres://" scheme, which SQLAlchemy 1.4+ rejects.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-not-for-production")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

    STARTING_BALANCE = 1000.0
    LEVEL_STEP = 5000.0

    # Cookie hardening: in-app browsers (Snapchat, Instagram, etc.) are stricter about
    # dropping non-persistent, non-SameSite-explicit cookies than a normal browser.
    # Secure cookies require HTTPS, which only Render's env (not local dev over
    # plain HTTP) guarantees. Render injects RENDER=true into every service.
    _is_production = bool(os.environ.get("RENDER"))
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _is_production
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = _is_production
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 365
