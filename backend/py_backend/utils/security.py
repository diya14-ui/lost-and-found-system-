from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from py_backend.config import Config


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_token(payload: dict) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=Config.JWT_EXPIRES_IN_DAYS)
    data = {**payload, "exp": expires_at}
    return jwt.encode(data, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
