"""Attendee model for tracking event participants.

This module defines the Attendee model which represents people invited
to calendar events. Attendee information is synced from Google Calendar
and displayed in the event detail view.
"""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.event import Event


class Attendee(SQLModel, table=True):
    """A person invited to an event.

    Attendees are synced from Google Calendar and represent the people
    who have been invited to participate in an event. Their response
    status indicates whether they have accepted, declined, or not yet
    responded to the invitation.

    Attributes:
        id: Unique identifier (UUID).
        event_id: Foreign key to the parent Event.
        email: Email address of the attendee.
        display_name: Human-readable name, if available.
        response_status: Invitation response status from Google Calendar.
            One of: "accepted", "declined", "tentative", or "needsAction"
            (not yet responded).
        event: Reference to the parent Event object.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    email: str
    display_name: str | None = None
    response_status: str = Field(default="needsAction")

    # Relationship
    event: Optional["Event"] = Relationship(back_populates="attendees")
