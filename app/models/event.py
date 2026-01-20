"""Event model for calendar events synced from Google Calendar.

This module defines the Event model which represents a calendar event
with its associated checklist items, attendees, and confirmation records.
Events are the central entity that users interact with to prepare for
upcoming appointments and meetings.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.attendee import Attendee
    from app.models.confirmation import ChecklistConfirmation
    from app.models.item import Item


class Event(SQLModel, table=True):
    """A calendar event synced from Google Calendar.

    Events are synced periodically from Google Calendar and stored locally
    with associated checklist items. Users can check off items, confirm
    readiness, and archive events for record-keeping.

    Attributes:
        id: Unique identifier (UUID).
        google_event_id: The event ID from Google Calendar (unique).
        recurring_event_id: For recurring events, the ID of the master event.
            Used to link instances of the same recurring series.
        title: Event title/summary.
        description: Event description, may contain checklist items.
        start_time: When the event starts.
        end_time: When the event ends.
        last_synced: Timestamp of last sync from Google Calendar.
        is_archived: If True, event is read-only and preserved for reference.
        user_id: Owner of this event (for future multi-user support).
        items: Checklist items associated with this event.
        attendees: People invited to this event.
        confirmations: Records of when the checklist was confirmed complete.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    google_event_id: str = Field(index=True, unique=True)
    recurring_event_id: str | None = Field(default=None, index=True)
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    last_synced: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_archived: bool = Field(default=False)
    user_id: int = Field(default=1)  # Single user for now, ready for multi-user

    # Relationships
    items: list["Item"] = Relationship(back_populates="event")
    attendees: list["Attendee"] = Relationship(back_populates="event")
    confirmations: list["ChecklistConfirmation"] = Relationship(back_populates="event")
