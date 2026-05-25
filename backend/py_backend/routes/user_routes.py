from flask import Blueprint, jsonify, g
from py_backend.db import get_connection
from py_backend.middleware.auth import require_auth

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

