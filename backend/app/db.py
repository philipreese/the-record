import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Index
from sqlalchemy.orm import declarative_base, sessionmaker

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BACKEND_DIR, "history.db"))
JSON_PATH = os.environ.get("JSON_PATH", os.path.join(BACKEND_DIR, "merged_history.json"))

# Declarative base model
Base = declarative_base()

class Listen(Base):
    __tablename__ = "listens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist = Column(String, nullable=False)
    title = Column(String, nullable=False)
    unix_ts = Column(Integer, nullable=False)
    source = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_listens_unix_ts", "unix_ts"),
        Index("idx_listens_artist", "artist"),
    )

# Internal engine caching to support unit test overrides of DB_PATH
_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    expected_url = os.environ.get("DATABASE_URL")
    if expected_url:
        # Standardize PostgreSQL scheme to use psycopg (v3) dialect
        if expected_url.startswith("postgres://"):
            expected_url = expected_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif expected_url.startswith("postgresql://"):
            expected_url = expected_url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        db_abs_path = os.path.abspath(DB_PATH).replace("\\", "/")
        expected_url = f"sqlite:///{db_abs_path}"
        
    if _engine is None or str(_engine.url) != expected_url:
        connect_args = {}
        if expected_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(expected_url, connect_args=connect_args)
    return _engine

def get_session():
    global _SessionLocal
    eng = get_engine()
    if _SessionLocal is None or _SessionLocal.kw["bind"] is not eng:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _SessionLocal()

def get_db_connection():
    """
    Return a raw connection from the engine to maintain backward-compatibility
    for codebase areas that directly interact with connection/cursor API.
    """
    return get_engine().raw_connection()

def get_db_session():
    """Yield a database session context for SQLAlchemy ORM operations."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()

def init_db() -> None:
    """Initialize database schema, tables, and indices."""
    Base.metadata.create_all(get_engine())

def bootstrap_db_from_json() -> bool:
    """Bootstrap the database from merged_history.json if the database is empty."""
    init_db()
    
    session = get_session()
    try:
        # Check if database is empty
        count = session.query(Listen).count()
        if count > 0:
            print(f"Database already contains {count:,} entries. Skipping bootstrap.")
            return False

        if not os.path.exists(JSON_PATH):
            print(f"merged_history.json not found at '{JSON_PATH}'. Skipping bootstrap.")
            return False
            
        print(f"Bootstrapping database from {JSON_PATH}...")
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
            
        # Bulk insert
        listens_to_insert = [
            Listen(
                artist=item["artist"],
                title=item["title"],
                unix_ts=item["unix_ts"],
                source=item.get("source", "unknown")
            )
            for item in history
        ]
        session.bulk_save_objects(listens_to_insert)
        session.commit()
        
        new_count = session.query(Listen).count()
        print(f"Successfully bootstrapped database with {new_count:,} records.")
        return True
    except Exception as e:
        session.rollback()
        print(f"Error bootstrapping database: {e}")
        return False
    finally:
        session.close()
