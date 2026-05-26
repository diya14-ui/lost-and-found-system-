from flask import request, jsonify

# Minimal CSRF protection middleware.
# - If an incoming unsafe request (POST/PUT/DELETE/PATCH) contains an Authorization Bearer header, it's allowed.
# - Otherwise, if the request contains cookies that may indicate cookie-based auth, require a matching
#   `X-CSRF-Token` header and `csrf_token` cookie (double-submit cookie pattern).
# This is intentionally lightweight and opt-in for cookie-based sessions; it does not affect Bearer token flows.

UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def register_csrf(app):
    @app.before_request
    def _csrf_check():
        try:
            method = request.method.upper()
            if method not in UNSAFE_METHODS:
                return None

            # If Authorization header (Bearer) is present, assume token-based auth (skip CSRF)
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return None

            # If no cookies are present, likely not using cookie auth — allow
            if not request.cookies:
                return None

            # If there's no csrf_token cookie, allow (no cookie-based session in use)
            csrf_cookie = request.cookies.get("csrf_token")
            if not csrf_cookie:
                return None

            # Require header X-CSRF-Token matching cookie
            csrf_header = request.headers.get("X-CSRF-Token")
            if not csrf_header or csrf_header != csrf_cookie:
                return jsonify({"success": False, "message": "CSRF token missing or invalid"}), 403

            return None
        except Exception:
            # Fail open on unexpected errors to avoid blocking legitimate traffic
            return None
