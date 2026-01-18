"""Tests for database models."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models import Attendee, ChecklistConfirmation, Event, Item


class TestEventModel:
    """Tests for the Event model."""

    def test_create_event(self, session: Session):
        """Test creating a basic event."""
        event = Event(
            google_event_id="google_123",
            title="Test Meeting",
            description="Meeting description",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(event)
        session.commit()

        retrieved = session.exec(
            select(Event).where(Event.google_event_id == "google_123")
        ).first()

        assert retrieved is not None
        assert retrieved.title == "Test Meeting"
        assert retrieved.is_archived is False
        assert retrieved.user_id == 1

    def test_event_unique_google_id(self, session: Session):
        """Test that google_event_id must be unique."""
        event1 = Event(
            google_event_id="duplicate_id",
            title="First Event",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(event1)
        session.commit()

        event2 = Event(
            google_event_id="duplicate_id",
            title="Second Event",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(event2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()

    def test_event_with_recurring_id(self, session: Session):
        """Test event with recurring_event_id."""
        event = Event(
            google_event_id="instance_123",
            recurring_event_id="master_abc",
            title="Recurring Instance",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(event)
        session.commit()

        retrieved = session.get(Event, event.id)
        assert retrieved.recurring_event_id == "master_abc"


class TestItemModel:
    """Tests for the Item model."""

    def test_create_item(self, sample_event: Event, session: Session):
        """Test creating an item linked to an event."""
        item = Item(
            event_id=sample_event.id,
            name="Test Item",
            source="manual",
        )
        session.add(item)
        session.commit()

        retrieved = session.get(Item, item.id)
        assert retrieved is not None
        assert retrieved.name == "Test Item"
        assert retrieved.is_checked is False
        assert retrieved.source == "manual"

    def test_item_event_relationship(self, event_with_items: Event, session: Session):
        """Test that items are properly linked to events."""
        session.refresh(event_with_items)
        assert len(event_with_items.items) == 3
        item_names = [item.name for item in event_with_items.items]
        assert "Laptop" in item_names
        assert "Charger" in item_names
        assert "Notes" in item_names

    def test_item_checked_state(self, sample_event: Event, session: Session):
        """Test toggling item checked state."""
        item = Item(event_id=sample_event.id, name="Toggle Item")
        session.add(item)
        session.commit()

        assert item.is_checked is False

        item.is_checked = True
        session.add(item)
        session.commit()

        retrieved = session.get(Item, item.id)
        assert retrieved.is_checked is True


class TestAttendeeModel:
    """Tests for the Attendee model."""

    def test_create_attendee(self, sample_event: Event, session: Session):
        """Test creating an attendee."""
        attendee = Attendee(
            event_id=sample_event.id,
            email="test@example.com",
            display_name="Test User",
            response_status="accepted",
        )
        session.add(attendee)
        session.commit()

        retrieved = session.get(Attendee, attendee.id)
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.response_status == "accepted"

    def test_attendee_event_relationship(self, sample_event: Event, session: Session):
        """Test attendee-event relationship."""
        attendee = Attendee(
            event_id=sample_event.id,
            email="attendee@example.com",
        )
        session.add(attendee)
        session.commit()
        session.refresh(sample_event)

        assert len(sample_event.attendees) == 1
        assert sample_event.attendees[0].email == "attendee@example.com"


class TestConfirmationModel:
    """Tests for the ChecklistConfirmation model."""

    def test_create_confirmation(self, sample_event: Event, session: Session):
        """Test creating a confirmation record."""
        confirmation = ChecklistConfirmation(event_id=sample_event.id)
        session.add(confirmation)
        session.commit()

        retrieved = session.get(ChecklistConfirmation, confirmation.id)
        assert retrieved is not None
        assert retrieved.event_id == sample_event.id
        assert retrieved.confirmed_at is not None

    def test_confirmation_event_relationship(
        self, sample_event: Event, session: Session
    ):
        """Test confirmation-event relationship."""
        confirmation = ChecklistConfirmation(event_id=sample_event.id)
        session.add(confirmation)
        session.commit()
        session.refresh(sample_event)

        assert len(sample_event.confirmations) == 1
