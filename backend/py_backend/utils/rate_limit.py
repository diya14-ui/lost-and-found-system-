import time
from functools import wraps
from flask import request, jsonify

# Simple in-memory rate limiter. Not distributed; good for single-process testing/dev.
_store = {}

def _cleanup_window(timestamps, window):
    cutoff = time.time() - window
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)


def rate_limit(max_calls=5, per_seconds=60, by='ip'):
    """
    Decorator to rate-limit endpoints.
    - max_calls: allowed calls within window
    - per_seconds: time window in seconds
    - by: 'ip' or 'email_or_ip' - for password-reset use 'email_or_ip' to key by email when present
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                if by == 'email_or_ip':
                    data = request.get_json(silent=True) or request.form or {}
                    email = data.get('email') if isinstance(data, dict) else None
                    key_id = (email or request.headers.get('X-Forwarded-For') or request.remote_addr or 'anon').lower()
                else:
                    key_id = (request.headers.get('X-Forwarded-For') or request.remote_addr or 'anon')

                key = f"rl:{fn.__name__}:{key_id}"
                now = time.time()

                entry = _store.get(key)
                if not entry:
                    entry = []
                    _store[key] = entry

                # cleanup old timestamps
                _cleanup_window(entry, per_seconds)

                if len(entry) >= max_calls:
                    retry_after = int(per_seconds - (now - entry[0])) if entry else per_seconds
                    return jsonify({"success": False, "message": "Too many requests. Try again later.", "retryAfter": retry_after}), 429

                entry.append(now)
                return fn(*args, **kwargs)
            except Exception:
                # In case of any error, fail open (do not block request)
                return fn(*args, **kwargs)

        return wrapper
    return decorator
