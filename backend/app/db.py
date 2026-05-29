import os
import sqlite3
import json

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BACKEND_DIR, "history.db"))
JSON_PATH = os.environ.get("JSON_PATH", os.path.join(BACKEND_DIR, "merged_history.json"))

def get_db_connection() -> sqlite3.Connection:
    """Establish and return an SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize the database schema and build indices."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create listens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist TEXT NOT NULL,
            title TEXT NOT NULL,
            unix_ts INTEGER NOT NULL,
            source TEXT NOT NULL
        )
    """)
    
    # Create indices for fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_unix_ts ON listens(unix_ts)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_artist ON listens(artist)")
    
    conn.commit()
    conn.close()

def bootstrap_db_from_json() -> bool:
    """Bootstrap the SQLite database from merged_history.json if the database is empty."""
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if database is empty
    cursor.execute("SELECT COUNT(*) FROM listens")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Database already contains {count:,} entries. Skipping bootstrap.")
        conn.close()
        return False

    if not os.path.exists(JSON_PATH):
        print(f"merged_history.json not found at '{JSON_PATH}'. Skipping bootstrap.")
        conn.close()
        return False
        
    print(f"Bootstrapping database from {JSON_PATH}...")
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
            
        # Bulk insert
        cursor.executemany(
            "INSERT INTO listens (artist, title, unix_ts, source) VALUES (?, ?, ?, ?)",
            [(item["artist"], item["title"], item["unix_ts"], item.get("source", "unknown")) for item in history]
        )
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM listens")
        new_count = cursor.fetchone()[0]
        print(f"Successfully bootstrapped SQLite database with {new_count:,} records.")
        conn.close()
        return True
    except Exception as e:
        print(f"Error bootstrapping database: {e}")
        conn.close()
        return False
