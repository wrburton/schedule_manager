from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.event import Event


class Item(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    name: str
    is_checked: bool = Field(default=False)
    source: str = Field(default="parsed")  # "parsed" from description or "manual"

    # Relationship
    event: Optional["Event"] = Relationship(back_populates="items")
