from flask import Blueprint, jsonify, request, g
from py_backend.db import get_connection
from py_backend.middleware.auth import require_auth
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


@item_bp.get("")
def get_items():
    item_type = request.args.get("type")
    search = request.args.get("search")
    category = request.args.get("category")
    location = request.args.get("location")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

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

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, tuple(values))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    serialized_rows = [_serialize_item_row(row) for row in rows]
    return jsonify({"success": True, "data": serialized_rows})


@item_bp.get("/<int:item_id>")
def get_item_by_id(item_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, reporter_name, reporter_email, item_name, item_type, category, location_text, date_value,
               time_value, description_text, image_url, contact_method, phone, status, created_at
        FROM items
        WHERE id = %s
        LIMIT 1
        """,
        (item_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

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

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO items
        (reporter_name, reporter_email, item_name, item_type, category, location_text, date_value, time_value,
         description_text, image_url, contact_method, phone, posted_by_user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Item report created", "data": {"id": new_id}}), 201
