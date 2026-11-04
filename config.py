"""
Configuration classes for Flask Portfolio CMS.
Uses environment variables exclusively for sensitive values.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Ensure .env is loaded even if WSGI is launched from an arbitrary working directory
_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, ".env"))


class Config:
    """Base configuration shared by all environments."""

    # ── Security ──────────────────────────────────────────────────────────────
    _env_secret = os.environ.get("SECRET_KEY", "").strip()
    if not _env_secret or _env_secret in (
        "CHANGE-ME-BEFORE-DEPLOYING",
        "change-this-to-a-secure-random-key-before-deploying",
        "generate-a-secure-random-secret-key",
    ):
        import secrets
        SECRET_KEY = secrets.token_hex(32)
    else:
        SECRET_KEY = _env_secret
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1-hour CSRF token validity

    # ── Session ───────────────────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _default_db = os.path.join(_base_dir, "portfolio.db").replace("\\", "/")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{_default_db}"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # ── Email ─────────────────────────────────────────────────────────────────
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
    RESEND_FROM_EMAIL = os.environ.get(
        "RESEND_FROM_EMAIL", "Muhammad Hassan Portfolio <onboarding@resend.dev>"
    ).strip()
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
    BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "").strip()
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() in ("true", "1", "on")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "").replace(" ", "").strip()
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", os.environ.get("MAIL_USERNAME", "Muhammad Hassan Portfolio <onboarding@resend.dev>")
    ).strip()
    CONTACT_RECIPIENT_EMAIL = os.environ.get(
        "CONTACT_RECIPIENT_EMAIL", "mhassanawan66521@gmail.com"
    ).strip()
    ALLOWED_ADMIN_EMAILS = [
        email.strip() for email in os.environ.get(
            "ALLOWED_ADMIN_EMAILS", "mhassanawan66521@gmail.com"
        ).split(",") if email.strip()
    ]

    # ── Uploads ───────────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload limit
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")


class DevelopmentConfig(Config):
    """Development environment — debug ON, relaxed security."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing environment — in-memory SQLite, CSRF disabled."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production environment — strict security, HTTPS-aware cookies."""
    DEBUG = False
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "on")
    SESSION_COOKIE_SAMESITE = "Lax"
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year static cache

    @classmethod
    def validate(cls):
        """Validate production configuration without crashing deployment."""
        key = os.environ.get("SECRET_KEY", "").strip()
        if not key or key in (
            "CHANGE-ME-BEFORE-DEPLOYING",
            "change-this-to-a-secure-random-key-before-deploying",
            "generate-a-secure-random-secret-key",
        ):
            import logging
            logging.getLogger("config").warning(
                "Notice: SECRET_KEY was not explicitly configured in .env. A secure random key has been generated automatically."
            )
        elif len(key) < 16:
            import logging
            logging.getLogger("config").warning("Notice: SECRET_KEY is short. Consider using a 64-character hex key.")


# ── Environment name → Config class map ──────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
