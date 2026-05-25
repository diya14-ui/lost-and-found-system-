from flask import Blueprint, request, jsonify, g
import mysql.connector
from py_backend.db import get_connection
from py_backend.utils.security import verify_password, generate_token
from py_backend.utils.email import send_email
from py_backend.middleware.auth import require_auth
from functools import wraps
from datetime import date, datetime, time, timedelta

admin_bp = Blueprint("admin", __name__)


def _get_reporter_email_for_item(item_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT reporter_email, reporter_name FROM items WHERE id = %s LIMIT 1", (item_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def _json_safe_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date, time, timedelta)):
        return str(value)
    return str(value)


def _serialize_item_row(row):
    return {key: _json_safe_value(value) for key, value in row.items()}


def _format_dashboard_event(event_type: str, title: str, body: str, happened_at):
    return {
        "type": event_type,
        "title": title,
        "body": body,
        "happenedAt": _json_safe_value(happened_at),
    }


def require_admin(fn):
    @require_auth
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = g.user.get("id") if getattr(g, "user", None) else None
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT is_admin, role, name, email FROM users WHERE id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception:
            return jsonify({"success": False, "message": "Database unavailable"}), 503

        is_admin = bool(row.get("is_admin")) if row else False
        role = (row.get("role") or "").strip().lower() if row else ""
        if not row or (not is_admin and role != "admin"):
            return jsonify({"success": False, "message": "Admin access required"}), 403

        g.admin_user = {
            "id": user_id,
            "name": row.get("name"),
            "email": row.get("email"),
            "is_admin": is_admin,
            "role": "admin",
        }

        return fn(*args, **kwargs)

    return wrapper


@admin_bp.post('/login')
def admin_login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get('email') or '').strip()
    password = payload.get('password') or ''

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, email, password_hash, is_admin, role FROM users WHERE email = %s LIMIT 1", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database is not available right now."}), 503

    role = (user.get('role') or '').strip().lower() if user else ''
    if not user or (not user.get('is_admin') and role != 'admin') or not verify_password(password, user.get('password_hash')):
        return jsonify({"success": False, "message": "Invalid admin credentials"}), 401

    token = generate_token({"id": user['id'], "email": user['email'], "role": "admin"})
    return jsonify({"success": True, "message": "Admin login successful", "data": {"token": token}})


@admin_bp.get('/me')
@require_auth
@require_admin
def admin_me():
    return jsonify({"success": True, "data": g.admin_user})


@admin_bp.get('/dashboard')
@require_auth
@require_admin
def dashboard_summary():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM users")
        users = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM items")
        total_items = cursor.fetchone()['total']

        # Backward-compatible counting: old rows may still carry legacy statuses
        # while moderation uses is_approved as the source of truth.
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM items
            WHERE status = 'pending'
               OR (COALESCE(is_approved, 0) = 0 AND status NOT IN ('rejected', 'resolved'))
            """
        )
        pending_items = cursor.fetchone()['total']

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM items
            WHERE status = 'approved'
               OR (COALESCE(is_approved, 0) = 1 AND status NOT IN ('rejected', 'resolved'))
            """
        )
        approved_items = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM items WHERE status = 'rejected'")
        rejected_items = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM items WHERE status = 'resolved'")
        resolved_items = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM claims WHERE status = 'pending'")
        pending_claims = cursor.fetchone()['total']

        cursor.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS total
            FROM items
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 DAY)
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """
        )
        items_trend_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS total
            FROM claims
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 DAY)
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """
        )
        claims_trend_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT id, item_name, status, updated_at
            FROM items
            ORDER BY updated_at DESC
            LIMIT 8
            """
        )
        recent_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT c.id, c.status, c.updated_at, i.item_name
            FROM claims c
            LEFT JOIN items i ON i.id = c.item_id
            ORDER BY c.updated_at DESC
            LIMIT 8
            """
        )
        recent_claims = cursor.fetchall()

        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    days = [(datetime.utcnow().date() - timedelta(days=offset)) for offset in range(6, -1, -1)]
    day_keys = [day.isoformat() for day in days]
    items_by_day = {str(row.get("day")): int(row.get("total") or 0) for row in items_trend_rows}
    claims_by_day = {str(row.get("day")): int(row.get("total") or 0) for row in claims_trend_rows}

    trend = [
        {
            "day": key,
            "items": items_by_day.get(key, 0),
            "claims": claims_by_day.get(key, 0),
        }
        for key in day_keys
    ]

    events = []
    for row in recent_items:
        events.append(
            _format_dashboard_event(
                "item",
                f"Item #{row.get('id')} moderation update",
                f"{row.get('item_name') or 'Unnamed item'} is now {row.get('status') or 'pending'}.",
                row.get('updated_at'),
            )
        )

    for row in recent_claims:
        item_name = row.get('item_name') or f"Item #{row.get('id')}"
        events.append(
            _format_dashboard_event(
                "claim",
                f"Claim #{row.get('id')} status update",
                f"Claim for {item_name} is {row.get('status') or 'pending'}.",
                row.get('updated_at'),
            )
        )

    events.sort(key=lambda entry: str(entry.get("happenedAt") or ""), reverse=True)
    events = events[:8]

    return jsonify({
        "success": True,
        "data": {
            "totalUsers": users,
            "totalItems": total_items,
            "pendingItems": pending_items,
            "approvedItems": approved_items,
            "rejectedItems": rejected_items,
            "pendingClaims": pending_claims,
            "resolvedItems": resolved_items,
            "moderationTrend": trend,
            "recentActivity": events,
        },
    })


@admin_bp.get('/items')
@require_auth
@require_admin
def list_items():
    # pagination
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT SQL_CALC_FOUND_ROWS
                id, reporter_name, reporter_email, item_name, item_type, category,
                location_text, date_value, time_value, description_text, image_url,
                contact_method, phone, status, is_approved, posted_by_user_id,
                created_at, updated_at
            FROM items
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (per_page, offset),
        )
        items = [_serialize_item_row(row) for row in cursor.fetchall()]
        cursor.execute("SELECT FOUND_ROWS() AS total")
        total = cursor.fetchone()['total']
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "data": {"items": items, "total": total}})


@admin_bp.post('/items/<int:item_id>/approve')
@require_auth
@require_admin
def approve_item(item_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET is_approved = 1, status = 'approved' WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "Item approved"})


@admin_bp.post('/approve-item')
@require_auth
@require_admin
def approve_item_alias():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get('item_id')
    if not item_id:
        return jsonify({"success": False, "message": "item_id is required"}), 400
    return approve_item(int(item_id))


@admin_bp.post('/items/<int:item_id>/reject')
@require_auth
@require_admin
def reject_item(item_id):
    reason = (request.json or {}).get('reason')

    reporter = None
    try:
        reporter = _get_reporter_email_for_item(item_id)
    except Exception:
        reporter = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET is_approved = 0, status = 'rejected' WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    # Optionally notify reporter (best-effort)
    try:
        if reporter and reporter.get('reporter_email'):
            send_email(
                to_address=reporter['reporter_email'],
                subject='Your item post was removed',
                html_body=f"<p>Hello {reporter.get('reporter_name')},</p><p>Your post was removed by moderators. Reason: {reason or 'Violation of rules'}.</p>",
                text_body=f"Your post was removed by moderators. Reason: {reason or 'Violation of rules'}."
            )
    except Exception:
        pass

    return jsonify({"success": True, "message": "Item rejected"})


@admin_bp.post('/reject-item')
@require_auth
@require_admin
def reject_item_alias():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get('item_id')
    if not item_id:
        return jsonify({"success": False, "message": "item_id is required"}), 400
    return reject_item(int(item_id))


@admin_bp.delete('/delete-item')
@require_auth
@require_admin
def delete_item_alias():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get('item_id') or request.args.get('item_id')
    if not item_id:
        return jsonify({"success": False, "message": "item_id is required"}), 400
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = %s", (int(item_id),))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "Item deleted"})


@admin_bp.post('/items/<int:item_id>/resolve')
@require_auth
@require_admin
def resolve_item(item_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET is_approved = 1, status = 'resolved' WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "Item marked as resolved"})


@admin_bp.put('/items/<int:item_id>')
@require_auth
@require_admin
def edit_item(item_id):
    payload = request.get_json(silent=True) or {}
    fields = []
    values = []
    allowed = ['item_name', 'category', 'location_text', 'date_value', 'time_value', 'description_text']
    for key in allowed:
        if key in payload:
            fields.append(f"{key} = %s")
            values.append(payload[key])
    if not fields:
        return jsonify({"success": False, "message": "No editable fields provided"}), 400
    values.append(item_id)
    sql = f"UPDATE items SET {', '.join(fields)} WHERE id = %s"
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, tuple(values))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "Item updated"})


@admin_bp.get('/claims')
@require_auth
@require_admin
def list_claims():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT c.*, u.name as claimant_name, u.email as claimant_email FROM claims c LEFT JOIN users u ON u.id = c.claimant_user_id ORDER BY c.created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "data": rows})


@admin_bp.post('/claims/<int:claim_id>/approve')
@require_auth
@require_admin
def approve_claim(claim_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE claims SET status = 'approved' WHERE id = %s", (claim_id,))
        conn.commit()
        cursor.execute("SELECT claimant_user_id FROM claims WHERE id = %s LIMIT 1", (claim_id,))
        claimant = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    # notify user (best-effort)
    try:
        if claimant and claimant[0]:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT email, name FROM users WHERE id = %s LIMIT 1", (claimant[0],))
            u = cursor.fetchone()
            cursor.close()
            conn.close()
            if u and u.get('email'):
                send_email(u['email'], 'Claim approved', f'<p>Hello {u.get("name")},</p><p>Your claim has been approved.</p>', f'Your claim has been approved.')
    except Exception:
        pass

    return jsonify({"success": True, "message": "Claim approved"})


@admin_bp.post('/claims/<int:claim_id>/reject')
@require_auth
@require_admin
def reject_claim(claim_id):
    reason = (request.json or {}).get('reason')
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE claims SET status = 'rejected' WHERE id = %s", (claim_id,))
        conn.commit()
        cursor.execute("SELECT claimant_user_id FROM claims WHERE id = %s LIMIT 1", (claim_id,))
        claimant = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    try:
        if claimant and claimant[0]:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT email, name FROM users WHERE id = %s LIMIT 1", (claimant[0],))
            u = cursor.fetchone()
            cursor.close()
            conn.close()
            if u and u.get('email'):
                send_email(u['email'], 'Claim rejected', f'<p>Hello {u.get("name")},</p><p>Your claim was rejected. Reason: {reason or "Not approved"}.</p>', f'Your claim was rejected.')
    except Exception:
        pass

    return jsonify({"success": True, "message": "Claim rejected"})


@admin_bp.get('/users')
@require_auth
@require_admin
def list_users():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, student_id, department, profile_image_url, is_admin, role, is_banned FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "data": rows})


@admin_bp.post('/users/<int:user_id>/ban')
@require_auth
@require_admin
def ban_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "User banned"})


@admin_bp.post('/users/<int:user_id>/unban')
@require_auth
@require_admin
def unban_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "User unbanned"})


@admin_bp.delete('/users/<int:user_id>')
@require_auth
@require_admin
def delete_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "User deleted"})
