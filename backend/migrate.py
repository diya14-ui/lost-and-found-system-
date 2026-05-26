from pathlib import Path
import sys
import mysql.connector
from dotenv import load_dotenv
import os

from py_backend.config import Config

load_dotenv(os.path.join(Path(__file__).resolve().parent, ".env"))

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", Config.DB_NAME)

base_dir = Path(__file__).resolve().parent
schema_file = base_dir / "database" / "schema.sql"

with schema_file.open("r", encoding="utf-8") as f:
    raw_sql = f.read()

statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    conn.autocommit = False
    cursor = conn.cursor()

    for statement in statements:
        cursor.execute(statement)

    conn.commit()
    print(f"Migration completed successfully for database '{DB_NAME}'.")
except mysql.connector.Error as error:
    try:
        conn.rollback()
    except Exception:
        pass
    print(f"Migration failed: {error}", file=sys.stderr)
    raise
finally:
    try:
        cursor.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
