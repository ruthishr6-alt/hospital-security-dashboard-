import sqlite3
import os
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

def ensure_schema(conn):
    """Ensures newly added columns exist in existing database without data loss."""
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(patients)")
        cols = [r[1] for r in cur.fetchall()]
        if 'phone_number' not in cols and len(cols) > 0:
            cur.execute("ALTER TABLE patients ADD COLUMN phone_number TEXT DEFAULT '+1 (555) 019-1001'")
            conn.commit()
        if 'user_id' not in cols and len(cols) > 0:
            cur.execute("ALTER TABLE patients ADD COLUMN user_id TEXT DEFAULT NULL")
            conn.commit()
        if 'email' not in cols and len(cols) > 0:
            cur.execute("ALTER TABLE patients ADD COLUMN email TEXT DEFAULT NULL")
            conn.commit()

        cur.execute("PRAGMA table_info(decoy_patients)")
        cols_dec = [r[1] for r in cur.fetchall()]
        if 'phone_number' not in cols_dec and len(cols_dec) > 0:
            cur.execute("ALTER TABLE decoy_patients ADD COLUMN phone_number TEXT DEFAULT '+1 (555) 019-9999'")
            conn.commit()
    except Exception:
        pass

def get_db():
    """Returns a thread-safe connection with row_factory set to sqlite3.Row."""
    try:
        if 'db' not in g:
            g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
            ensure_schema(g.db)
        return g.db
    except RuntimeError:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_schema(conn)
        return conn

def close_db(e=None):
    """Closes the current database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Executes a SELECT query and returns rows as dictionaries."""
    conn = get_db()
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (dict(rv[0]) if rv else None) if one else [dict(r) for r in rv]

def execute_db(query, args=()):
    """Executes an INSERT, UPDATE, or DELETE query and commits."""
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

def init_db():
    """Initializes tables using schema.sql."""
    conn = get_db()
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        print("Database initialized from schema.sql successfully.")
    else:
        print("schema.sql not found!")
