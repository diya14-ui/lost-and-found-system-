import mysql.connector

from py_backend.db import get_connection


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


def _column_type(cursor, table_name: str, column_name: str):
        cursor.execute(
                """
                SELECT COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
                    AND COLUMN_NAME = %s
                LIMIT 1
                """,
                (table_name, column_name),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def ensure_admin_columns():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not _column_exists(cursor, "users", "is_admin"):
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER profile_image_url")

        if not _column_exists(cursor, "users", "role"):
            cursor.execute("ALTER TABLE users ADD COLUMN role ENUM('student','admin') NOT NULL DEFAULT 'student' AFTER is_admin")
            cursor.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")

        if not _column_exists(cursor, "items", "is_approved"):
            cursor.execute("ALTER TABLE items ADD COLUMN is_approved TINYINT(1) NOT NULL DEFAULT 0 AFTER posted_by_user_id")
        if not _column_exists(cursor, "users", "is_banned"):
            cursor.execute("ALTER TABLE users ADD COLUMN is_banned TINYINT(1) NOT NULL DEFAULT 0 AFTER is_admin")

        status_column_type = _column_type(cursor, "items", "status")
        if status_column_type and ("approved" not in status_column_type or "rejected" not in status_column_type):
            cursor.execute(
                "ALTER TABLE items MODIFY COLUMN status ENUM('pending','approved','rejected','resolved') NOT NULL DEFAULT 'pending'"
            )

        # Keep role and legacy is_admin in sync.
        cursor.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1 AND role <> 'admin'")
        cursor.execute("UPDATE users SET is_admin = 1 WHERE role = 'admin' AND is_admin = 0")

        # Normalize moderation status for existing item rows.
        cursor.execute("UPDATE items SET status = 'pending' WHERE status = 'open'")
        cursor.execute("UPDATE items SET status = 'approved' WHERE COALESCE(is_approved, 1) = 1 AND status NOT IN ('resolved', 'rejected')")
        cursor.execute("UPDATE items SET status = 'pending' WHERE COALESCE(is_approved, 0) = 0 AND status NOT IN ('resolved', 'rejected')")

        # Keep is_approved aligned with moderation status semantics.
        cursor.execute("UPDATE items SET is_approved = 0 WHERE status IN ('pending', 'rejected')")
        cursor.execute("UPDATE items SET is_approved = 1 WHERE status IN ('approved', 'resolved')")

        conn.commit()
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
