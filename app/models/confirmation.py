"""Confirmation model for audit trail of completed checklists.

This module defines the ChecklistConfirmation model which creates an
immutable record when a user confirms that all checklist items for an
event have been completed. This provides an audit trail for verification.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.event import Event


class ChecklistConfirmation(SQLModel, table=True):
    """A record of checklist completion confirmation.

    When a user marks all items as checked and clicks "Confirm Ready",
    a confirmation record is created. This serves as an audit trail
    proving that preparation was verified at a specific time.

    Multiple confirmations can exist for the same event (e.g., if items
    are unchecked and re-confirmed later).

    Attributes:
        id: Unique identifier (UUID).
        event_id: Foreign key to the confirmed Event.
        confirmed_at: Timestamp when the confirmation was recorded.
        confirmed_by: User ID who confirmed (for future multi-user support).
        event: Reference to the parent Event object.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id")
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_by: int = Field(default=1)  # user_id

    # Relationship
    event: Optional["Event"] = Relationship(back_populates="confirmations")
