import mysql.connector
from mysql.connector import pooling
from py_backend.config import Config

pool = None


def _get_pool():
    global pool
    if pool is None:
        pool = pooling.MySQLConnectionPool(
            pool_name="lf_pool",
            pool_size=10,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
        )
    return pool

def get_connection():
    return _get_pool().get_connection()

def test_connection():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    cursor.close()
    conn.close()
