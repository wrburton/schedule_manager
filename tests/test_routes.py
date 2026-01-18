"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import ChecklistConfirmation, Event, Item


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test the health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestEventsRoutes:
    """Tests for event-related routes."""

    def test_upcoming_events_page(self, client: TestClient, sample_event: Event):
        """Test the upcoming events page loads."""
        response = client.get("/events/upcoming")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_archive_page(self, client: TestClient, archived_event: Event):
        """Test the archive page loads."""
        response = client.get("/events/archive")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_event_detail_page(self, client: TestClient, sample_event: Event):
        """Test the event detail page loads."""
        response = client.get(f"/events/{sample_event.id}")
        assert response.status_code == 200
        assert sample_event.title in response.text

    def test_event_detail_not_found(self, client: TestClient):
        """Test 404 for non-existent event."""
        from uuid import uuid4

        fake_id = uuid4()
        response = client.get(f"/events/{fake_id}")
        assert response.status_code == 404

    def test_archive_event(
        self, client: TestClient, sample_event: Event, session: Session
    ):
        """Test archiving an event."""
        response = client.post(
            f"/events/{sample_event.id}/archive", follow_redirects=False
        )
        assert response.status_code == 303

        session.refresh(sample_event)
        assert sample_event.is_archived is True

    def test_unarchive_event(
        self, client: TestClient, archived_event: Event, session: Session
    ):
        """Test unarchiving an event."""
        response = client.post(
            f"/events/{archived_event.id}/unarchive", follow_redirects=False
        )
        assert response.status_code == 303

        session.refresh(archived_event)
        assert archived_event.is_archived is False

    def test_confirm_event_all_checked(
        self, client: TestClient, event_with_items: Event, session: Session
    ):
        """Test confirming an event when all items are checked."""
        # First, check all items
        for item in event_with_items.items:
            item.is_checked = True
            session.add(item)
        session.commit()

        response = client.post(
            f"/events/{event_with_items.id}/confirm", follow_redirects=False
        )
        assert response.status_code == 303

        # Verify confirmation was created
        session.refresh(event_with_items)
        assert len(event_with_items.confirmations) == 1

    def test_confirm_event_unchecked_items(
        self, client: TestClient, event_with_items: Event
    ):
        """Test that confirming fails when items are unchecked."""
        response = client.post(
            f"/events/{event_with_items.id}/confirm", follow_redirects=False
        )
        assert response.status_code == 400

    def test_confirm_archived_event(self, client: TestClient, archived_event: Event):
        """Test that confirming an archived event fails."""
        response = client.post(
            f"/events/{archived_event.id}/confirm", follow_redirects=False
        )
        assert response.status_code == 400


class TestItemsRoutes:
    """Tests for item-related routes."""

    def test_create_item(
        self, client: TestClient, sample_event: Event, session: Session
    ):
        """Test creating a new item."""
        response = client.post(
            f"/events/{sample_event.id}/items",
            data={"name": "New Item"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        session.refresh(sample_event)
        item_names = [item.name for item in sample_event.items]
        assert "New Item" in item_names

    def test_create_item_on_archived_event(
        self, client: TestClient, archived_event: Event
    ):
        """Test that creating items on archived events fails."""
        response = client.post(
            f"/events/{archived_event.id}/items",
            data={"name": "Should Fail"},
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_toggle_item_redirect(
        self, client: TestClient, event_with_items: Event, session: Session
    ):
        """Test toggling an item returns redirect for non-AJAX requests."""
        item = event_with_items.items[0]
        initial_state = item.is_checked

        response = client.post(
            f"/events/{event_with_items.id}/items/{item.id}/toggle",
            follow_redirects=False,
        )
        assert response.status_code == 303

        session.refresh(item)
        assert item.is_checked != initial_state

    def test_toggle_item_json(
        self, client: TestClient, event_with_items: Event, session: Session
    ):
        """Test toggling an item returns JSON for AJAX requests."""
        item = event_with_items.items[0]
        initial_state = item.is_checked

        response = client.post(
            f"/events/{event_with_items.id}/items/{item.id}/toggle",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["is_checked"] != initial_state
        assert "checked_count" in data
        assert "total_count" in data
        assert "all_checked" in data

    def test_toggle_item_on_archived_event(
        self, client: TestClient, archived_event: Event, session: Session
    ):
        """Test that toggling items on archived events fails."""
        # Create an item on the archived event
        item = Item(event_id=archived_event.id, name="Test Item")
        session.add(item)
        session.commit()

        response = client.post(
            f"/events/{archived_event.id}/items/{item.id}/toggle",
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_delete_item(
        self, client: TestClient, event_with_items: Event, session: Session
    ):
        """Test deleting an item."""
        item = event_with_items.items[0]
        item_id = item.id
        item_name = item.name

        response = client.post(
            f"/events/{event_with_items.id}/items/{item_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

        session.refresh(event_with_items)
        item_names = [i.name for i in event_with_items.items]
        assert item_name not in item_names

    def test_delete_item_on_archived_event(
        self, client: TestClient, archived_event: Event, session: Session
    ):
        """Test that deleting items on archived events fails."""
        item = Item(event_id=archived_event.id, name="Test Item")
        session.add(item)
        session.commit()

        response = client.post(
            f"/events/{archived_event.id}/items/{item.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_toggle_nonexistent_item(
        self, client: TestClient, sample_event: Event
    ):
        """Test toggling a non-existent item returns 404."""
        from uuid import uuid4

        fake_item_id = uuid4()
        response = client.post(
            f"/events/{sample_event.id}/items/{fake_item_id}/toggle",
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestRootRedirect:
    """Tests for the root endpoint."""

    def test_root_redirects_to_upcoming(self, client: TestClient):
        """Test that root redirects to upcoming events."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/events/upcoming" in response.headers["location"]
