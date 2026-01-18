from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.event import Event


class Attendee(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    email: str
    display_name: str | None = None
    response_status: str = Field(default="needsAction")

    # Relationship
    event: Optional["Event"] = Relationship(back_populates="attendees")
