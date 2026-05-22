from flask import Blueprint, jsonify, request, g
from py_backend.db import get_connection
from py_backend.middleware.auth import require_auth
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime

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


def _ensure_claims_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id INT PRIMARY KEY AUTO_INCREMENT,
            item_id INT NOT NULL,
            claimant_user_id INT NOT NULL,
            ownership_reason TEXT,
            contact_number VARCHAR(60),
            additional_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_files (
            id INT PRIMARY KEY AUTO_INCREMENT,
            claim_id INT NOT NULL,
            file_name VARCHAR(255),
            file_url VARCHAR(1024),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_claim_file_claim FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
        )
        """
    )


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
