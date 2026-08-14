"""
Database engine + session management.
"""
import logging
import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

logger = logging.getLogger("garage.db")

# pool_pre_ping avoids stale-connection errors on free-tier DB hosts that
# silently close idle connections.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if not settings.SQL_QUERY_LOG_ENABLED:
        return
    total_ms = (time.perf_counter() - getattr(context, "_query_start_time", time.perf_counter())) * 1000
    if total_ms >= settings.SQL_QUERY_TTL_MS:
        logger.warning(
            "Slow SQL query detected: %.2fms | %s",
            total_ms,
            statement,
        )


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
