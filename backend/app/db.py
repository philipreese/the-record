import logging
import os
import json
from pathlib import Path
from sqlalchemy import Boolean, Column, create_engine, DateTime, Integer, String, Index, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BACKEND_DIR, "history.db"))
JSON_PATH = os.environ.get("JSON_PATH", os.path.join(BACKEND_DIR, "merged_history.json"))

# Declarative base model
Base = declarative_base()

class CoverArtCache(Base):
    __tablename__ = "cover_art_cache"

    artist_folded = Column(String, primary_key=True)
    title_folded = Column(String, primary_key=True)
    url = Column(String, nullable=True)
    manual_override = Column(Boolean, nullable=False, default=False)


class AlbumCorrection(Base):
    __tablename__ = "album_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wrong_album = Column(Text, nullable=False, unique=True)
    correct_album = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ListenCorrection(Base):
    __tablename__ = "listen_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listen_id = Column(Integer, nullable=False)
    field = Column(Text, nullable=False)
    corrected_value = Column(Text, nullable=True)
    corrected_at = Column(DateTime, server_default=func.now())
    lb_synced = Column(Boolean, nullable=False, default=False)
    user_id = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("listen_id", "field", name="uq_listen_corrections_listen_field"),
        Index("idx_listen_corrections_listen_id", "listen_id"),
    )


class Listen(Base):
    __tablename__ = "listens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist = Column(String, nullable=False)
    title = Column(String, nullable=False)
    unix_ts = Column(Integer, nullable=False)
    source = Column(String, nullable=False)
    duration_secs = Column(Integer, nullable=True)
    album = Column(String, nullable=True)
    recording_mbid = Column(String, nullable=True)

    __table_args__ = (
        Index("idx_listens_unix_ts", "unix_ts"),
        Index("idx_listens_artist", "artist"),
        Index("idx_listens_dedup", "artist", "title", "unix_ts"),
        Index("idx_listens_recording_mbid", "recording_mbid"),
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
        else:
            # For PostgreSQL, set the session timezone to match TZ env var if present
            tz = os.environ.get("TZ")
            if tz:
                connect_args["options"] = f"-c timezone={tz}"
            # pool_pre_ping detects stale connections after Neon serverless suspend;
            # pool_recycle preemptively replaces connections older than 5 minutes.
            _engine = create_engine(
                expected_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_recycle=300,
            )
    return _engine

def get_session():
    global _SessionLocal
    eng = get_engine()
    if _SessionLocal is None or _SessionLocal.kw["bind"] is not eng:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _SessionLocal()

def get_db_session():
    """Yield a database session context for SQLAlchemy ORM operations."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()

def init_db() -> None:
    """Run all pending Alembic migrations to bring the schema to head."""
    from alembic.config import Config
    from alembic import command
    backend_dir = Path(__file__).parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    # Set absolute path so migrations resolve correctly regardless of CWD.
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(alembic_cfg, "head")

def bootstrap_db_from_json() -> bool:
    """Bootstrap the database from merged_history.json if the database is empty."""
    init_db()
    
    session = get_session()
    try:
        # Check if database is empty
        count = session.query(Listen).count()
        if count > 0:
            logger.info("Database already contains %d entries. Skipping bootstrap.", count)
            return False

        if not os.path.exists(JSON_PATH):
            logger.warning("merged_history.json not found at %r. Skipping bootstrap.", JSON_PATH)
            return False

        logger.info("Bootstrapping database from %s ...", JSON_PATH)
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
        logger.info("Successfully bootstrapped database with %d records.", new_count)
        return True
    except Exception as e:
        session.rollback()
        logger.error("Error bootstrapping database: %s", e)
        return False
    finally:
        session.close()
