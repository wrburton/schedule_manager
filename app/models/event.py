from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.attendee import Attendee
    from app.models.confirmation import ChecklistConfirmation
    from app.models.item import Item


class Event(SQLModel, table=True):
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
