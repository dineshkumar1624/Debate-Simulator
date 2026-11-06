from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
connect_args = {}
if db_url.startswith("postgresql") or db_url.startswith("postgres"):
    # PostgreSQL is authoritative: must fail fast with actionable error, never silently fall back
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            pass
        logger.info("Successfully established connection to authoritative PostgreSQL database.")
    except Exception as e:
        logger.error(f"FATAL: Configured PostgreSQL database at {db_url} is unreachable: {e}")
        raise RuntimeError(f"Configured PostgreSQL database is unreachable: {e}. Silent SQLite fallback is strictly prohibited.") from e
elif db_url.startswith("sqlite"):
    # SQLite is allowed only in explicit local development or testing configurations
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
    logger.info("Initialized SQLite database engine (local development / testing environment).")
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
