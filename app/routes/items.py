"""Item routes for managing checklist items."""
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session

from app.calendar.client import has_valid_credentials
from app.calendar.sync import (
    delete_item_from_recurring_instances,
    push_item_to_recurring_instances,
    push_items_to_calendar,
    push_recurring_instances,
)
from app.core.database import get_session
from app.models import Event, Item

router = APIRouter(prefix="/events/{event_id}/items", tags=["items"])


def wants_json(request: Request) -> bool:
    """Check if the client prefers JSON response (AJAX request)."""
    accept = request.headers.get("accept", "")
    return "application/json" in accept


@router.post("")
async def create_item(
    event_id: UUID,
    name: str = Form(...),
    add_to_all: bool = Form(False),
    session: Session = Depends(get_session),
):
    """
    Add new item to event checklist.

    Creates a new checklist item with source="manual". If add_to_all is True
    and the event is part of a recurring series, the item is also added to
    all future instances and pushed to the master recurring event in Google Calendar.
    """
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.is_archived:
        raise HTTPException(status_code=400, detail="Cannot modify archived event")

    # Check credentials before attempting add_to_all with push
    if add_to_all and event.recurring_event_id and not has_valid_credentials():
        raise HTTPException(
            status_code=400,
            detail="Cannot add to all instances: Google Calendar credentials not configured",
        )

    item = Item(event_id=event_id, name=name.strip(), source="manual")
    session.add(item)
    session.commit()

    # If checkbox checked and this is a recurring event, push to master event
    if add_to_all and event.recurring_event_id:
        # Refresh event to ensure items relationship includes the new item
        session.refresh(event)
        push_item_to_recurring_instances(session, event, name.strip())

    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.post("/{item_id}/toggle")
async def toggle_item(
    event_id: UUID,
    item_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Toggle item checked state.

    Flips the is_checked boolean for the item. Returns JSON response with
    updated state when Accept: application/json header is present (for AJAX),
    otherwise redirects to the event detail page.
    """
    item = session.get(Item, item_id)
    if not item or item.event_id != event_id:
        raise HTTPException(status_code=404, detail="Item not found")

    event = session.get(Event, event_id)
    if event.is_archived:
        raise HTTPException(status_code=400, detail="Cannot modify archived event")

    item.is_checked = not item.is_checked
    session.add(item)
    session.commit()

    if wants_json(request):
        checked_count = sum(1 for i in event.items if i.is_checked)
        total_count = len(event.items)
        return JSONResponse({
            "success": True,
            "item_id": str(item_id),
            "is_checked": item.is_checked,
            "checked_count": checked_count,
            "total_count": total_count,
            "all_checked": checked_count == total_count,
        })

    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.post("/{item_id}/delete")
async def delete_item(
    event_id: UUID,
    item_id: UUID,
    delete_from_all: bool = Form(False),
    session: Session = Depends(get_session),
):
    """
    Delete item from checklist.

    Removes an item from the event. If delete_from_all is True and the event
    is part of a recurring series, the item is also removed from all future
    instances and the change is pushed to Google Calendar.
    """
    item = session.get(Item, item_id)
    if not item or item.event_id != event_id:
        raise HTTPException(status_code=404, detail="Item not found")

    event = session.get(Event, event_id)
    if event.is_archived:
        raise HTTPException(status_code=400, detail="Cannot modify archived event")

    # Check credentials before attempting delete_from_all with push
    if delete_from_all and event.recurring_event_id and not has_valid_credentials():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete from all instances: Google Calendar credentials not configured",
        )

    item_name = item.name  # Save before deletion

    session.delete(item)
    session.flush()

    # If requested and this is a recurring event, delete from all instances and push
    if delete_from_all and event.recurring_event_id:
        # Expire items relationship so push sees the updated list
        session.expire(event, ["items"])

        # Push source event to Google Calendar (prevent item returning on sync)
        new_desc = push_items_to_calendar(event)
        if new_desc is not None:
            event.description = new_desc

        session.commit()

        # Delete from other instances
        delete_item_from_recurring_instances(session, event, item_name)
    else:
        session.commit()

    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.post("/push")
async def push_items(
    event_id: UUID,
    session: Session = Depends(get_session),
):
    """
    Push item changes to Google Calendar.

    Syncs the current checklist items back to Google Calendar by updating
    the event description. For recurring events, pushes changes to all
    instances that have unpushed modifications. Returns 500 if all push
    attempts fail.
    """
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stats = push_recurring_instances(session, event)

    if stats["pushed"] == 0 and stats["failed"] > 0:
        raise HTTPException(status_code=500, detail="Failed to push items to calendar")

    return RedirectResponse(f"/events/{event_id}", status_code=303)
