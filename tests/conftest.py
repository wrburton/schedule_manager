"""Shared test fixtures."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.main import app
from app.models import Event, Item


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite database for testing."""
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
    """Create a new database session for each test."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with the test database session."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="sample_event")
def sample_event_fixture(session: Session) -> Event:
    """Create a sample event for testing."""
    event = Event(
        id=uuid4(),
        google_event_id="test_google_id_123",
        title="Test Event",
        description="Items:\n- Item 1\n- Item 2",
        start_time=datetime.now(UTC) + timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=2),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@pytest.fixture(name="event_with_items")
def event_with_items_fixture(session: Session) -> Event:
    """Create an event with checklist items."""
    event = Event(
        id=uuid4(),
        google_event_id="test_google_id_456",
        title="Event With Items",
        description="Test event",
        start_time=datetime.now(UTC) + timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=2),
    )
    session.add(event)
    session.flush()

    items = [
        Item(event_id=event.id, name="Laptop", is_checked=False),
        Item(event_id=event.id, name="Charger", is_checked=False),
        Item(event_id=event.id, name="Notes", is_checked=True),
    ]
    for item in items:
        session.add(item)

    session.commit()
    session.refresh(event)
    return event


@pytest.fixture(name="archived_event")
def archived_event_fixture(session: Session) -> Event:
    """Create an archived event for testing."""
    event = Event(
        id=uuid4(),
        google_event_id="test_google_id_archived",
        title="Archived Event",
        description="This event is archived",
        start_time=datetime.now(UTC) - timedelta(days=7),
        end_time=datetime.now(UTC) - timedelta(days=7) + timedelta(hours=1),
        is_archived=True,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
