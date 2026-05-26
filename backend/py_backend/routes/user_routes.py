from flask import Blueprint, jsonify, g, request
from py_backend.db import get_connection
from py_backend.middleware.auth import require_auth
from datetime import datetime


def _json_safe(val):
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            return str(val)
    return val

user_bp = Blueprint("users", __name__)


@user_bp.get("/me")
@require_auth
def get_current_user():
    user_id = g.user.get("id")
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email, student_id, department, profile_image_url, is_admin, created_at FROM users WHERE id = %s LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    if not row:
        return jsonify({"success": False, "message": "User not found"}), 404

    return jsonify({"success": True, "data": row})


@user_bp.get("/me/stats")
@require_auth
def get_stats():
    user_id = g.user.get("id")
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM items WHERE posted_by_user_id = %s AND item_type = 'lost'", (user_id,))
        lost_count = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM items WHERE posted_by_user_id = %s AND item_type = 'found'", (user_id,))
        found_count = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM claims WHERE claimant_user_id = %s AND status = 'pending'", (user_id,))
        pending_count = cursor.fetchone()["total"]

        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    return jsonify(
        {
            "success": True,
            "data": {
                "lostItemsFiled": lost_count,
                "foundItemsUploaded": found_count,
                "pendingClaims": pending_count,
            },
        }
    )


@user_bp.get('/me/items')
@require_auth
def get_my_items():
    user_id = g.user.get('id')
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except Exception:
        limit = 50
        offset = 0

    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, item_name, item_type, category, location_text, date_value, image_url, status, created_at
            FROM items WHERE posted_by_user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    for r in rows:
        if 'created_at' in r:
            r['created_at'] = _json_safe(r['created_at'])

    return jsonify({"success": True, "data": rows})


@user_bp.get('/me/claims')
@require_auth
def get_my_claims():
    user_id = g.user.get('id')
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.id, c.item_id, c.ownership_reason, c.contact_number, c.additional_info, c.status, c.created_at, c.updated_at,
                   i.item_name, i.item_type
            FROM claims c
            LEFT JOIN items i ON i.id = c.item_id
            WHERE c.claimant_user_id = %s
            ORDER BY c.created_at DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    for r in rows:
        if 'created_at' in r:
            r['created_at'] = _json_safe(r['created_at'])
        if 'updated_at' in r:
            r['updated_at'] = _json_safe(r['updated_at'])

    return jsonify({"success": True, "data": rows})


@user_bp.get('/me/notifications')
@require_auth
def get_my_notifications():
    user_id = g.user.get('id')
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
    except Exception:
        limit = 100
        offset = 0

    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, title, body, metadata, is_read, created_at FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (user_id, limit, offset),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        # If notifications table doesn't exist or DB error, return empty list gracefully
        return jsonify({"success": True, "data": []})

    for r in rows:
        if 'created_at' in r:
            r['created_at'] = _json_safe(r['created_at'])
    return jsonify({"success": True, "data": rows})

