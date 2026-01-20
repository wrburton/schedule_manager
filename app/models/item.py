"""Checklist item model for event preparation tracking.

This module defines the Item model which represents individual checklist
items that users need to complete before an event. Items can be parsed
from event descriptions or added manually by users.
"""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.event import Event


class Item(SQLModel, table=True):
    """A checklist item associated with an event.

    Items represent things a user needs to prepare, bring, or complete
    before an event. They can be checked off to track progress toward
    event readiness.

    Attributes:
        id: Unique identifier (UUID).
        event_id: Foreign key to the parent Event.
        name: Display text for the checklist item.
        is_checked: Whether the item has been marked complete.
        source: Origin of the item - either "parsed" (extracted from
            the event description during sync) or "manual" (added by
            user through the UI). Manual items are preserved during
            sync even if not in the description.
        event: Reference to the parent Event object.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    name: str
    is_checked: bool = Field(default=False)
    source: str = Field(default="parsed")  # "parsed" from description or "manual"

    # Relationship
    event: Optional["Event"] = Relationship(back_populates="items")
