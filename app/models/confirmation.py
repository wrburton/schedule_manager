from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.event import Event


class ChecklistConfirmation(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_by: int = Field(default=1)  # user_id

    # Relationship
    event: Optional["Event"] = Relationship(back_populates="confirmations")
