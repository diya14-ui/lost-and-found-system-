from flask import Blueprint, jsonify, request, g
from py_backend.db import get_connection
from py_backend.middleware.auth import require_auth
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid
import json
from datetime import datetime
# SMTP/email removed — in-app DB notifications are used instead

claim_bp = Blueprint("claims", __name__)

CLAIM_PROOFS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "claims")
ALLOWED_PROOF_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}


def _is_allowed_proof_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_PROOF_EXTENSIONS


def _save_proof_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    if not _is_allowed_proof_file(file_storage.filename):
        return None

    os.makedirs(CLAIM_PROOFS_DIR, exist_ok=True)
    safe_name = secure_filename(file_storage.filename)
    extension = safe_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    absolute_path = os.path.join(CLAIM_PROOFS_DIR, unique_name)
    file_storage.save(absolute_path)
    return f"/uploads/claims/{unique_name}"


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    row = cursor.fetchone()
    return bool(row and row[0] > 0)


def _constraint_exists(cursor, table_name: str, constraint_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = %s
        """,
        (table_name, constraint_name),
    )
    row = cursor.fetchone()
    return bool(row and row[0] > 0)


def _table_engine(cursor, table_name: str) -> str | None:
    cursor.execute(
        """
        SELECT ENGINE
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        LIMIT 1
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _ensure_innodb(cursor, table_name: str):
    if _table_engine(cursor, table_name) != "InnoDB":
        cursor.execute(f"ALTER TABLE {table_name} ENGINE=InnoDB")


def _ensure_claims_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id INT PRIMARY KEY AUTO_INCREMENT,
            item_id INT NOT NULL,
            claimant_user_id INT DEFAULT NULL,
            ownership_reason TEXT NOT NULL,
            contact_number VARCHAR(30) NOT NULL,
            additional_info TEXT,
            status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_claims_item
                FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_claims_user
                FOREIGN KEY (claimant_user_id) REFERENCES users(id)
                ON DELETE SET NULL
        )
        """
    )

    _ensure_innodb(cursor, "users")
    _ensure_innodb(cursor, "items")
    _ensure_innodb(cursor, "claims")

    if not _column_exists(cursor, "claims", "status"):
        cursor.execute("ALTER TABLE claims ADD COLUMN status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending' AFTER additional_info")

    if not _column_exists(cursor, "claims", "updated_at"):
        cursor.execute("ALTER TABLE claims ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at")

    if _column_exists(cursor, "claims", "claimant_user_id"):
        cursor.execute("ALTER TABLE claims MODIFY COLUMN claimant_user_id INT DEFAULT NULL")
    if _column_exists(cursor, "claims", "ownership_reason"):
        cursor.execute("ALTER TABLE claims MODIFY COLUMN ownership_reason TEXT NOT NULL")
    if _column_exists(cursor, "claims", "contact_number"):
        cursor.execute("ALTER TABLE claims MODIFY COLUMN contact_number VARCHAR(30) NOT NULL")

    if not _constraint_exists(cursor, "claims", "fk_claims_item"):
        cursor.execute("ALTER TABLE claims ADD CONSTRAINT fk_claims_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE")

    if not _constraint_exists(cursor, "claims", "fk_claims_user"):
        cursor.execute("ALTER TABLE claims ADD CONSTRAINT fk_claims_user FOREIGN KEY (claimant_user_id) REFERENCES users(id) ON DELETE SET NULL")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_files (
            id INT PRIMARY KEY AUTO_INCREMENT,
            claim_id INT NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_url VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_claim_files_claim FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
        )
        """
    )

    _ensure_innodb(cursor, "claim_files")

    if not _constraint_exists(cursor, "claim_files", "fk_claim_files_claim"):
        cursor.execute("ALTER TABLE claim_files ADD CONSTRAINT fk_claim_files_claim FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE")


def _append_local_claim_fallback(payload: dict):
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "pending_claims.json")
        entries = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []

        payload_copy = dict(payload)
        payload_copy["ts"] = datetime.utcnow().isoformat() + "Z"
        entries.insert(0, payload_copy)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

        return file_path, len(entries)
    except Exception:
        return None, 0


def _ensure_notifications_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            metadata TEXT,
            is_read TINYINT(1) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
        """
    )


def _json_safe_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _serialize_claim_row(row):
    return {key: _json_safe_value(value) for key, value in row.items()}


def _require_claim_admin(fn):
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


def _update_claim_status(claim_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE claims SET status = %s WHERE id = %s", (status, claim_id))
    cursor.execute("SELECT item_id FROM claims WHERE id = %s LIMIT 1", (claim_id,))
    claim_row = cursor.fetchone()

    if status == "approved" and claim_row and claim_row.get("item_id"):
        cursor.execute("UPDATE items SET status = 'resolved', is_approved = 1 WHERE id = %s", (claim_row["item_id"],))

    conn.commit()
    cursor.close()
    conn.close()
    return claim_row


@claim_bp.post("")
@require_auth
def create_claim():
    form = request.form
    item_id = form.get("itemId")
    ownership_reason = form.get("ownershipReason", "").strip()
    contact_number = form.get("contactNumber", "").strip()
    additional_info = form.get("additionalInfo", "").strip() or None

    if not item_id or not ownership_reason or not contact_number:
        return jsonify({"success": False, "message": "Missing required claim fields"}), 400

    claimant_user_id = g.user.get("id")
    # Save proof files to uploads directory first (so we keep files even if DB is down)
    saved_files = []
    files = request.files.getlist("proofFiles")
    for file in files:
        stored_file_url = _save_proof_file(file)
        if not stored_file_url:
            continue
        saved_files.append({"file_name": file.filename, "file_url": stored_file_url})

    # Try to persist claim and files to DB; if DB unavailable, save to local JSON fallback
    try:
        conn = get_connection()
        cursor = conn.cursor()
        _ensure_claims_tables(cursor)

        cursor.execute(
            """
            INSERT INTO claims (item_id, claimant_user_id, ownership_reason, contact_number, additional_info)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (item_id, claimant_user_id, ownership_reason, contact_number, additional_info),
        )
        conn.commit()
        claim_id = cursor.lastrowid

        for sf in saved_files:
            cursor.execute(
                "INSERT INTO claim_files (claim_id, file_name, file_url) VALUES (%s, %s, %s)",
                (claim_id, sf["file_name"], sf["file_url"]) if isinstance(sf, tuple) else (claim_id, sf["file_name"], sf["file_url"]),
            )

        conn.commit()
        cursor.close()
        conn.close()

        # Best-effort: create in-app notifications for reporter and claimant (DB-backed)
        try:
            connn = get_connection()
            cur = connn.cursor()
            _ensure_notifications_table(cur)
            connn.commit()

            # fetch reporter details (including reporter user id)
            cur.execute("SELECT posted_by_user_id, reporter_name, reporter_email, item_name FROM items WHERE id = %s LIMIT 1", (item_id,))
            item_row = cur.fetchone()
            reporter_user_id = None
            reporter_name = None
            if item_row:
                # cursor without dictionary=True returns tuple; map accordingly
                # posted_by_user_id is first column
                reporter_user_id = item_row[0]
                reporter_name = item_row[1] if len(item_row) > 1 else None

            # Insert notification for reporter (if we know their user id)
            metadata = json.dumps({"claim_id": claim_id, "item_id": item_id})
            if reporter_user_id:
                title = "New claim submitted for your item"
                body = f"A user has submitted a claim for your item (ID: {claim_id})."
                cur.execute("INSERT INTO notifications (user_id, title, body, metadata) VALUES (%s, %s, %s, %s)", (reporter_user_id, title, body, metadata))

            # Insert notification for claimant (confirmation)
            if claimant_user_id:
                title = "Your claim was submitted"
                body = f"Your claim (ID: {claim_id}) has been received. The reporter will be notified."
                cur.execute("INSERT INTO notifications (user_id, title, body, metadata) VALUES (%s, %s, %s, %s)", (claimant_user_id, title, body, metadata))

            connn.commit()
            cur.close()
            connn.close()
        except Exception:
            # ignore notification errors — do not block claim creation
            try:
                cur.close()
            except Exception:
                pass
            try:
                connn.close()
            except Exception:
                pass

        return jsonify({"success": True, "message": "Claim submitted", "data": {"id": claim_id}}), 201
    except Exception:
        # DB unavailable — append claim to local fallback JSON and return info
        fallback_payload = {
            "item_id": item_id,
            "claimant_user_id": claimant_user_id,
            "ownership_reason": ownership_reason,
            "contact_number": contact_number,
            "additional_info": additional_info,
            "files": saved_files,
        }
        file_path, count = _append_local_claim_fallback(fallback_payload)
        if file_path:
            return jsonify({"success": True, "message": "Claim saved locally (fallback)", "data": {"localFile": file_path, "localCount": count}}), 200
        return jsonify({"success": False, "message": "Unable to save claim right now"}), 503


@claim_bp.get("")
@_require_claim_admin
def list_claims():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.*, u.name AS claimant_name, u.email AS claimant_email, i.item_name, i.item_type
            FROM claims c
            LEFT JOIN users u ON u.id = c.claimant_user_id
            LEFT JOIN items i ON i.id = c.item_id
            ORDER BY c.created_at DESC
            """
        )
        rows = [_serialize_claim_row(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "data": rows})


@claim_bp.post("/<int:claim_id>/approve")
@_require_claim_admin
def approve_claim(claim_id):
    try:
        _update_claim_status(claim_id, "approved")
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "Claim approved"})


@claim_bp.post("/<int:claim_id>/reject")
@_require_claim_admin
def reject_claim(claim_id):
    try:
        _update_claim_status(claim_id, "rejected")
    except Exception:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    return jsonify({"success": True, "message": "Claim rejected"})
