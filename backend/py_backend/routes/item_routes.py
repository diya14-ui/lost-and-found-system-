from flask import Blueprint, jsonify, request, g
from py_backend.db import get_connection
from py_backend.middleware.auth import require_auth
from py_backend.utils.security import decode_token
import jwt
import mysql.connector
from functools import wraps
from datetime import timedelta
import os
import uuid
from werkzeug.utils import secure_filename

item_bp = Blueprint("items", __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "jfif", "avif"}


def _is_allowed_image(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def _save_uploaded_image(image_file):
    if not image_file or not image_file.filename:
        return None

    if not _is_allowed_image(image_file.filename):
        return None

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    cleaned_name = secure_filename(image_file.filename)
    extension = cleaned_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    absolute_path = os.path.join(UPLOAD_DIR, unique_name)
    image_file.save(absolute_path)

    return f"/uploads/{unique_name}"


def _serialize_item_row(row):
    """Convert MySQL date/time objects to JSON-safe strings."""
    if not row:
        return row

    serialized = dict(row)

    for field, value in serialized.items():
        if hasattr(value, "isoformat"):
            serialized[field] = value.isoformat()
            continue

        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            serialized[field] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    image_url = serialized.get("image_url")
    if image_url and isinstance(image_url, str):
        if not image_url.startswith("http") and not image_url.startswith("/uploads/"):
            serialized["image_url"] = f"/uploads/{image_url.lstrip('/')}"

    return serialized


def _is_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _get_current_user_id_if_available():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        return None

    return decoded.get("id")


def _require_item_admin(fn):
    @require_auth
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = g.user.get("id") if getattr(g, "user", None) else None
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT is_admin, role FROM users WHERE id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception:
            return jsonify({"success": False, "message": "Database unavailable"}), 503

        is_admin = bool(row.get("is_admin")) if row else False
        role = (row.get("role") or "").strip().lower() if row else ""
        if not row or (not is_admin and role != "admin"):
            return jsonify({"success": False, "message": "Admin access required"}), 403

        return fn(*args, **kwargs)

    return wrapper


def _db_unavailable_response():
    return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503


@item_bp.get("")
def get_items():
    item_type = request.args.get("type")
    search = request.args.get("search")
    category = request.args.get("category")
    location = request.args.get("location")
    mine = _is_truthy(request.args.get("mine"))
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "limit and offset must be numbers"}), 400

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conditions = []
    values = []

    if item_type:
        conditions.append("item_type = %s")
        values.append(item_type)

    if search:
        conditions.append("(item_name LIKE %s OR description_text LIKE %s)")
        values.extend([f"%{search}%", f"%{search}%"])

    if category:
        conditions.append("category = %s")
        values.append(category)

    if location:
        conditions.append("location_text LIKE %s")
        values.append(f"%{location}%")

    if mine:
        user_id = _get_current_user_id_if_available()
        if not user_id:
            return jsonify({"success": False, "message": "Authorization token required for my items"}), 401
        conditions.append("posted_by_user_id = %s")
        values.append(user_id)

    if not mine:
        conditions.append("COALESCE(is_approved, 0) = 1")
        conditions.append("status IN ('approved', 'resolved')")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT id, reporter_name, reporter_email, item_name, item_type, category, location_text, date_value,
             time_value, description_text, image_url, contact_method, phone, status, created_at
        FROM items
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    values.extend([limit, offset])

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, tuple(values))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return _db_unavailable_response()
    except Exception:
        return _db_unavailable_response()

    serialized_rows = [_serialize_item_row(row) for row in rows]
    return jsonify({"success": True, "data": serialized_rows})


@item_bp.get("/<int:item_id>")
def get_item_by_id(item_id: int):
    mine = _is_truthy(request.args.get("mine"))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        user_id = None
        mine_clause = ""
        if mine:
            user_id = _get_current_user_id_if_available()
            if not user_id:
                return jsonify({"success": False, "message": "Authorization token required for my items"}), 401
            mine_clause = "AND posted_by_user_id = %s"
        cursor.execute(
            """
            SELECT id, reporter_name, reporter_email, item_name, item_type, category, location_text, date_value,
                   time_value, description_text, image_url, contact_method, phone, status, created_at
            FROM items
              WHERE id = %s
                  {mine_clause}
                  {visibility_clause}
            LIMIT 1
            """.format(
                mine_clause=mine_clause,
                visibility_clause="" if mine else "AND COALESCE(is_approved, 0) = 1 AND status IN ('approved', 'resolved')",
            ),
            (item_id, *([user_id] if mine else [])),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return _db_unavailable_response()
    except Exception:
        return _db_unavailable_response()

    if not row:
        return jsonify({"success": False, "message": "Item not found"}), 404

    return jsonify({"success": True, "data": _serialize_item_row(row)})


@item_bp.post("")
@require_auth
def create_item():
    form = request.form

    reporter_name = form.get("reporterName", "").strip()
    reporter_email = form.get("reporterEmail", "").strip()
    item_name = form.get("itemName", "").strip()
    item_type = form.get("itemType", "").strip()
    # Validate item_type server-side to avoid relying solely on DB ENUM rejection
    allowed_item_types = {"lost", "found"}
    if not item_type or item_type.lower() not in allowed_item_types:
        return jsonify({"success": False, "message": "Invalid itemType. Allowed: lost, found"}), 400
    item_type = item_type.lower()
    category = form.get("category", "").strip() or None
    location = form.get("location", "").strip()
    date_value = form.get("date", "").strip()
    time_value = form.get("time", "").strip() or None
    description = form.get("description", "").strip()
    contact_method = form.get("contactMethod", "email").strip() or "email"
    phone = form.get("phone", "").strip() or None

    if not reporter_name or not reporter_email or not item_name or not item_type or not location or not date_value or not description:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    image_file = request.files.get("photo")
    image_url = _save_uploaded_image(image_file)

    if image_file and image_file.filename and not image_url:
        return jsonify({"success": False, "message": "Invalid image format. Allowed: png, jpg, jpeg, gif, webp, bmp, jfif, avif"}), 400

    posted_by_user_id = g.user.get("id")

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO items
            (reporter_name, reporter_email, item_name, item_type, category, location_text, date_value, time_value,
             description_text, image_url, contact_method, phone, posted_by_user_id, status, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                reporter_name,
                reporter_email,
                item_name,
                item_type,
                category,
                location,
                date_value,
                time_value,
                description,
                image_url,
                contact_method,
                phone,
                posted_by_user_id,
                "pending",
                0,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return _db_unavailable_response()
    except Exception:
        return _db_unavailable_response()

    return jsonify({"success": True, "message": "Item report created", "data": {"id": new_id}}), 201


@item_bp.post("/<int:item_id>/resolve")
@_require_item_admin
def resolve_item(item_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET status = 'resolved', is_approved = 1 WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return _db_unavailable_response()
    except Exception:
        return _db_unavailable_response()

    return jsonify({"success": True, "message": "Item marked as resolved"})


@item_bp.put("/<int:item_id>")
@_require_item_admin
def edit_item(item_id: int):
    payload = request.get_json(silent=True) or {}
    allowed = ["item_name", "category", "location_text", "date_value", "time_value", "description_text", "item_type"]
    fields = []
    values = []

    for key in allowed:
        if key in payload:
            fields.append(f"{key} = %s")
            values.append(payload[key])

    if not fields:
        return jsonify({"success": False, "message": "No editable fields provided"}), 400

    values.append(item_id)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE items SET {', '.join(fields)} WHERE id = %s", tuple(values))
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return _db_unavailable_response()
    except Exception:
        return _db_unavailable_response()

    return jsonify({"success": True, "message": "Item updated"})


@item_bp.delete("/<int:item_id>")
@_require_item_admin
def delete_item(item_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return _db_unavailable_response()
    except Exception:
        return _db_unavailable_response()

    return jsonify({"success": True, "message": "Item deleted"})
