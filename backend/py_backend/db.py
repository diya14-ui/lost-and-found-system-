import mysql.connector
from mysql.connector import pooling
from py_backend.config import Config

pool = None


def _get_pool():
    global pool
    if pool is None:
        # Keep pool smaller by default and reset session to avoid stale state
        pool = pooling.MySQLConnectionPool(
            pool_name="lf_pool",
            pool_size=getattr(Config, 'DB_POOL_SIZE', 5),
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connection_timeout=getattr(Config, 'DB_CONN_TIMEOUT', 10),
        )
    return pool

def get_connection():
    try:
        return _get_pool().get_connection()
    except mysql.connector.Error:
        # Try to recreate the pool once if obtaining a connection fails
        global pool
        pool = None
        return _get_pool().get_connection()

def test_connection():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    cursor.close()
    conn.close()
