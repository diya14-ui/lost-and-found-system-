from flask import Blueprint, jsonify, request
import mysql.connector
from py_backend.db import get_connection
import os
import json
from datetime import datetime

contact_bp = Blueprint("contact", __name__)


def _ensure_contacts_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) DEFAULT NULL,
            email VARCHAR(255) DEFAULT NULL,
            subject VARCHAR(255) DEFAULT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _append_local_fallback(payload: dict):
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "pending_contacts.json")
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


@contact_bp.post("")
def create_contact():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip() or None
    email = (payload.get("email") or "").strip() or None
    subject = (payload.get("subject") or "").strip() or None
    message = (payload.get("message") or "").strip() or None

    if not subject or not message:
        return jsonify({"success": False, "message": "Subject and message are required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        _ensure_contacts_table(cursor)
        cursor.execute(
            "INSERT INTO contacts (name, email, subject, message) VALUES (%s, %s, %s, %s)",
            (name, email, subject, message),
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Message saved", "data": {"id": new_id}}), 201
    except mysql.connector.Error:
        # Database unavailable — fallback to a local JSON file and return that path in the response
        file_path, count = _append_local_fallback({"name": name, "email": email, "subject": subject, "message": message})
        if file_path:
            return jsonify({"success": True, "message": "Message saved locally (fallback)", "data": {"localFile": file_path, "localCount": count}}), 200
        return jsonify({"success": False, "message": "Unable to save message right now"}), 503
