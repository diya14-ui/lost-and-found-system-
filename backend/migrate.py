from pathlib import Path
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

base_dir = Path(__file__).resolve().parent
schema_file = base_dir / "database" / "schema.sql"

with schema_file.open("r", encoding="utf-8") as f:
    raw_sql = f.read()

statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]

conn = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
)
cursor = conn.cursor()

for statement in statements:
    cursor.execute(statement)

conn.commit()
cursor.close()
conn.close()

print("Migration completed successfully.")
