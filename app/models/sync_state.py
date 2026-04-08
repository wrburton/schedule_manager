"""Persistent storage for Google Calendar sync state.

Stores the sync token and last sync status per calendar so they survive
application restarts. Without persistence, every restart forces a full
30-day API fetch instead of the far cheaper incremental sync.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class SyncStateRecord(SQLModel, table=True):
    """One row per calendar ID, upserted after every sync attempt.

    Attributes:
        calendar_id: Google Calendar ID (primary key).
        sync_token: Google's nextSyncToken for incremental sync; None when
            a full sync is needed (e.g. first run, or after a 410 expiry).
        last_sync_time: UTC timestamp of the last sync attempt.
        last_sync_success: Whether the last sync succeeded.
        last_sync_error: Error message from the last failure, if any.
    """

    __tablename__ = "sync_state"

    calendar_id: str = Field(primary_key=True)
    sync_token: str | None = Field(default=None)
    last_sync_time: datetime | None = Field(default=None)
    last_sync_success: bool = Field(default=True)
    last_sync_error: str | None = Field(default=None)
