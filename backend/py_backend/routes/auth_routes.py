from flask import Blueprint, jsonify, request
import mysql.connector
from py_backend.db import get_connection
from py_backend.utils.security import hash_password, verify_password, generate_token
from werkzeug.utils import secure_filename
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from py_backend.utils.email import send_email

auth_bp = Blueprint("auth", __name__)

PROFILE_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "profiles")
ALLOWED_PROFILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "jfif", "avif"}


def _is_allowed_profile_image(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_PROFILE_EXTENSIONS


def _save_profile_image(image_file):
    if not image_file or not image_file.filename:
        return None

    if not _is_allowed_profile_image(image_file.filename):
        return None

    os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)
    cleaned_name = secure_filename(image_file.filename)
    extension = cleaned_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    absolute_path = os.path.join(PROFILE_UPLOAD_DIR, unique_name)
    image_file.save(absolute_path)
    return f"/uploads/profiles/{unique_name}"


def _ensure_password_reset_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            token_hash CHAR(64) NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            used_at DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_password_reset_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_reset_url(token: str) -> str:
    return f"forgot-password.html?token={token}"


@auth_bp.post("/signup")
def signup():
    payload = request.get_json(silent=True) if request.is_json else {}
    form = request.form

    def get_field(field_name):
        value = form.get(field_name)
        if value is None:
            value = payload.get(field_name)
        return (value or "").strip()

    name = get_field("name")
    email = get_field("email")
    student_id = get_field("studentId")
    department = get_field("department")
    password = get_field("password")
    profile_photo = request.files.get("profilePhoto")

    if not name or not email or not student_id or not department or not password:
        return jsonify({"success": False, "message": "All required fields must be provided"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE email = %s OR student_id = %s LIMIT 1",
            (email, student_id),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "User already exists with this email or student ID"}), 409

        password_hash = hash_password(password)
        profile_image_url = _save_profile_image(profile_photo)
        if profile_photo and profile_photo.filename and not profile_image_url:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Invalid profile photo format. Allowed: png, jpg, jpeg, gif, webp, bmp, jfif, avif"}), 400

        cursor.execute(
            "INSERT INTO users (name, email, student_id, department, password_hash, profile_image_url, is_admin, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (name, email, student_id, department, password_hash, profile_image_url, 0, "student"),
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    token = generate_token({"id": user_id, "email": email})
    return jsonify(
        {
            "success": True,
            "message": "Signup successful",
            "data": {
                "token": token,
                "user": {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "studentId": student_id,
                    "department": department,
                    "profileImageUrl": profile_image_url,
                    "is_admin": False,
                    "role": "student",
                },
            },
        }
    ), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    password = payload.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email, student_id, department, profile_image_url, password_hash, is_admin, role FROM users WHERE email = %s LIMIT 1",
            (email,),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    role = user.get("role") or ("admin" if bool(user.get("is_admin")) else "student")
    token = generate_token({"id": user["id"], "email": user["email"], "role": role})
    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "data": {
                "token": token,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "studentId": user["student_id"],
                    "department": user["department"],
                    "profileImageUrl": user.get("profile_image_url"),
                    "is_admin": bool(user.get("is_admin")),
                    "role": role,
                },
            },
        }
    )


@auth_bp.post("/password-reset/request")
def request_password_reset():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        _ensure_password_reset_table(cursor)

        cursor.execute("SELECT id, name FROM users WHERE email = %s LIMIT 1", (email,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify(
                {
                    "success": True,
                    "message": "If that email exists, a reset link has been created.",
                    "data": {"resetUrl": None},
                }
            )

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_reset_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user["id"],))
        cursor.execute(
            "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (user["id"], token_hash, expires_at),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    # Try sending email if SMTP is configured; otherwise return the reset URL in the response
    reset_url = _build_reset_url(raw_token)
    email_subject = "Campus Lost & Found — Password reset"
    reset_link_absolute = reset_url
    try:
        # If Config.SMTP_HOST is set, send email (send_email returns False if not configured)
        sent = send_email(
            to_address=email,
            subject=email_subject,
            html_body=f"<p>Hello {user['name']},</p><p>Click the link below to reset your password (expires in 30 minutes):</p><p><a href=\"{reset_link_absolute}\">Reset password</a></p>",
            text_body=f"Hello {user['name']},\n\nOpen this link to reset your password: {reset_link_absolute}\n\nThis link expires in 30 minutes."
        )
    except Exception:
        sent = False

    if sent:
        return jsonify({"success": True, "message": "If that email exists, a reset link has been sent."})

    return jsonify(
        {
            "success": True,
            "message": "Password reset link created.",
            "data": {
                "resetUrl": reset_url,
                "expiresInMinutes": 30,
            },
        }
    )


@auth_bp.post("/password-reset/complete")
def complete_password_reset():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    new_password = (payload.get("newPassword") or "").strip()

    if not token or not new_password:
        return jsonify({"success": False, "message": "Reset token and new password are required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        _ensure_password_reset_table(cursor)

        token_hash = _hash_reset_token(token)
        cursor.execute(
            """
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used_at, u.name
            FROM password_reset_tokens prt
            INNER JOIN users u ON u.id = prt.user_id
            WHERE prt.token_hash = %s
            LIMIT 1
            """,
            (token_hash,),
        )
        reset_row = cursor.fetchone()

        if not reset_row:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Invalid reset link"}), 400

        if reset_row["used_at"] is not None or reset_row["expires_at"] < datetime.utcnow():
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Reset link has expired. Please request a new one."}), 400

        new_password_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, reset_row["user_id"]))
        cursor.execute("UPDATE password_reset_tokens SET used_at = %s WHERE id = %s", (datetime.utcnow(), reset_row["id"]))
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error:
        return jsonify({"success": False, "message": "Database is not available right now. Please try again."}), 503

    return jsonify(
        {
            "success": True,
            "message": "Password has been updated successfully",
            "data": {
                "name": reset_row["name"],
            },
        }
    )
