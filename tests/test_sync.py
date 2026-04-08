"""Tests for sync utilities: _parse_datetime and SyncState persistence."""

from datetime import UTC, datetime, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.calendar.sync import SyncState, _parse_datetime
from app.models.sync_state import SyncStateRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def reset_sync_state():
    """Reset SyncState class variables between tests to prevent bleed."""
    SyncState._tokens = {}
    SyncState._last_sync_time = None
    SyncState._last_sync_success = True
    SyncState._last_sync_error = None
    yield
    SyncState._tokens = {}
    SyncState._last_sync_time = None
    SyncState._last_sync_success = True
    SyncState._last_sync_error = None


# ---------------------------------------------------------------------------
# Fix #1: _parse_datetime returns timezone-aware datetimes
# ---------------------------------------------------------------------------


class TestParseDatetime:
    def test_datetime_with_z_suffix(self):
        result = _parse_datetime({"dateTime": "2024-03-15T10:00:00Z"})
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_datetime_with_offset(self):
        result = _parse_datetime({"dateTime": "2024-03-15T10:00:00+05:30"})
        assert result.tzinfo is not None

    def test_all_day_event_is_aware(self):
        """All-day events must return a UTC-aware datetime, not a naive one."""
        result = _parse_datetime({"date": "2024-03-15"})
        assert result.tzinfo is not None, "All-day event datetime must be timezone-aware"
        assert result.tzinfo == UTC

    def test_all_day_event_is_midnight(self):
        result = _parse_datetime({"date": "2024-03-15"})
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_all_day_comparable_with_utc_now(self):
        """All-day datetime must be comparable to datetime.now(UTC) without TypeError."""
        result = _parse_datetime({"date": "2024-03-15"})
        now = datetime.now(UTC)
        # Should not raise TypeError
        assert (result < now) or (result >= now)


# ---------------------------------------------------------------------------
# Fix #4: SyncState.load and SyncState._persist
# ---------------------------------------------------------------------------


class TestSyncStatePersistence:
    def test_persist_creates_row(self, session: Session):
        SyncState._tokens["primary"] = "token-abc"
        SyncState._last_sync_time = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)
        SyncState._last_sync_success = True

        SyncState._persist(session, "primary")
        session.commit()

        record = session.get(SyncStateRecord, "primary")
        assert record is not None
        assert record.sync_token == "token-abc"
        assert record.last_sync_success is True

    def test_persist_updates_existing_row(self, session: Session):
        SyncState._tokens["primary"] = "token-v1"
        SyncState._persist(session, "primary")
        session.commit()

        SyncState._tokens["primary"] = "token-v2"
        SyncState._persist(session, "primary")
        session.commit()

        record = session.get(SyncStateRecord, "primary")
        assert record.sync_token == "token-v2"

    def test_persist_clears_token_when_none(self, session: Session):
        # First persist with a token
        SyncState._tokens["primary"] = "some-token"
        SyncState._persist(session, "primary")
        session.commit()

        # Clear token and persist again
        SyncState._tokens.pop("primary", None)
        SyncState._persist(session, "primary")
        session.commit()

        record = session.get(SyncStateRecord, "primary")
        assert record.sync_token is None

    def test_persist_stores_failure(self, session: Session):
        SyncState._last_sync_success = False
        SyncState._last_sync_error = "HTTP 500"
        SyncState._last_sync_time = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)

        SyncState._persist(session, "primary")
        session.commit()

        record = session.get(SyncStateRecord, "primary")
        assert record.last_sync_success is False
        assert record.last_sync_error == "HTTP 500"

    def test_load_restores_token(self, session: Session):
        record = SyncStateRecord(
            calendar_id="work",
            sync_token="restored-token",
            last_sync_success=True,
        )
        session.add(record)
        session.commit()

        SyncState.load(session)

        assert SyncState.get_token("work") == "restored-token"

    def test_load_restores_status(self, session: Session):
        ts = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)
        record = SyncStateRecord(
            calendar_id="primary",
            sync_token=None,
            last_sync_time=ts,
            last_sync_success=False,
            last_sync_error="Something broke",
        )
        session.add(record)
        session.commit()

        SyncState.load(session)

        status = SyncState.get_sync_status()
        assert status["success"] is False
        assert status["error"] == "Something broke"
        assert status["last_sync_time"] == ts

    def test_load_is_noop_when_no_rows(self, session: Session):
        """load() must not raise when the table is empty (first run)."""
        SyncState.load(session)  # should not raise
        assert SyncState.get_token("primary") is None

    def test_round_trip_survives_restart(self, session: Session):
        """Simulate persist → clear memory → load to verify full round-trip."""
        SyncState._tokens["primary"] = "round-trip-token"
        SyncState._last_sync_success = True
        SyncState._persist(session, "primary")
        session.commit()

        # Simulate restart: wipe in-memory state
        SyncState._tokens = {}
        SyncState._last_sync_time = None

        SyncState.load(session)
        assert SyncState.get_token("primary") == "round-trip-token"
