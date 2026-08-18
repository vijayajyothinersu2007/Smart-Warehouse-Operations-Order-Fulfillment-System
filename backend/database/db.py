import sqlite3
import os
from contextlib import contextmanager
from backend.config import DATABASE_PATH

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query_db(query, args=(), one=False):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        if one:
            return dict(rv[0]) if rv else None
        return [dict(r) for r in rv]

def execute_db(query, args=()):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        return cur.lastrowid

def init_db(schema_path=None):
    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    with get_db() as conn:
        conn.executescript(schema_sql)
