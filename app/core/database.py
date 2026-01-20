"""Database configuration and session management for SQLite.

This module configures the SQLite database engine with settings optimized
for a web application: WAL mode for concurrent access and foreign key
enforcement for data integrity.

SQLite Configuration Choices:
    - **WAL (Write-Ahead Logging)**: Allows concurrent readers while writing.
      Without WAL, SQLite uses rollback journals which block all readers
      during writes. WAL is essential for web apps where the background
      sync job writes while users read event data.

    - **Foreign Keys**: SQLite has foreign key support but it's disabled by
      default for backwards compatibility. We enable it to ensure referential
      integrity (e.g., deleting an Event cascades to its Items).

    - **check_same_thread=False**: Required for FastAPI/async. SQLite's default
      prevents connections from being used across threads, but FastAPI's
      dependency injection may pass sessions between threads.
"""

from sqlalchemy import event as sa_event
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite requires this for use with FastAPI's async request handling.
# The default check_same_thread=True would raise errors when a connection
# created in one thread is used in another (common with async frameworks).
connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,  # Log SQL statements when DEBUG=true
)


@sa_event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configure SQLite pragmas on each new connection.

    These settings are connection-level, not database-level, so they must
    be set each time a new connection is established from the pool.
    """
    cursor = dbapi_connection.cursor()
    # WAL mode: enables concurrent reads during writes, crucial for web apps
    # where sync jobs write while users browse. Also improves crash recovery.
    cursor.execute("PRAGMA journal_mode=WAL")
    # Foreign keys: enforce referential integrity (e.g., Item.event_id must
    # reference a valid Event). Disabled by default in SQLite for legacy reasons.
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database session."""
    with Session(engine) as session:
        yield session
