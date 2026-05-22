from functools import wraps
from flask import request, jsonify, g
import jwt
from py_backend.utils.security import decode_token


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Authorization token missing"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            decoded = decode_token(token)
            g.user = decoded
        except jwt.PyJWTError:
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401

        return fn(*args, **kwargs)

    return wrapper
