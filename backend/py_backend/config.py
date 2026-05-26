import os
from dotenv import load_dotenv

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_backend_dir, ".env"))

class Config:
    PORT = int(os.getenv("PORT", "5000"))
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "maindatabase")
    # If JWT_SECRET is not provided, generate an ephemeral secret and warn.
    JWT_SECRET = os.getenv("JWT_SECRET")
    if not JWT_SECRET:
        try:
            import secrets as _secrets
            JWT_SECRET = _secrets.token_urlsafe(32)
        except Exception:
            JWT_SECRET = ""
        print("Warning: JWT_SECRET is not set. Using an ephemeral secret — tokens will be invalid after restart. Set JWT_SECRET in your .env for persistent tokens.")
    JWT_EXPIRES_IN_DAYS = int(os.getenv("JWT_EXPIRES_DAYS", "7"))
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
    # SMTP / email settings (optional)
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@example.com")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "15"))
    DB_CONN_TIMEOUT = int(os.getenv("DB_CONN_TIMEOUT", "10"))
