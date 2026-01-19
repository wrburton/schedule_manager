"""Event routes for displaying and managing events."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.calendar.client import has_valid_credentials
from app.calendar.sync import has_unpushed_changes
from app.core.database import get_session
from app.models import ChecklistConfirmation, Event

router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/upcoming", response_class=HTMLResponse)
async def upcoming_events(request: Request, session: Session = Depends(get_session)):
    """
    Display upcoming events with checklists.

    Shows events in two sections:
    - Soon: Events ending within 2 hours ago to midnight ending the 2nd day (large cards with full checklists)
    - Later: Events from end of 2nd day to 2 weeks ahead (compact list view)

    Events that finished more than 2 hours ago are not shown.
    """
    has_auth = has_valid_credentials()

    now = datetime.now(UTC)
    two_hours_ago = now - timedelta(hours=2)
    # Midnight boundaries for today, tomorrow, and day after
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=UTC)
    start_of_tomorrow = start_of_today + timedelta(days=1)
    start_of_day_after = start_of_today + timedelta(days=2)
    in_2_weeks = now + timedelta(weeks=2)

    # Today's events (finished within last 2 hours or not yet finished, starting today)
    today_statement = (
        select(Event)
        .where(Event.is_archived == False)  # noqa: E712
        .where(Event.end_time >= two_hours_ago)
        .where(Event.start_time < start_of_tomorrow)
        .order_by(Event.start_time)
    )
    today_events = session.exec(today_statement).all()

    # Tomorrow's events
    tomorrow_statement = (
        select(Event)
        .where(Event.is_archived == False)  # noqa: E712
        .where(Event.start_time >= start_of_tomorrow)
        .where(Event.start_time < start_of_day_after)
        .order_by(Event.start_time)
    )
    tomorrow_events = session.exec(tomorrow_statement).all()

    # Events from day after tomorrow to 2 weeks (compact list)
    later_statement = (
        select(Event)
        .where(Event.is_archived == False)  # noqa: E712
        .where(Event.start_time >= start_of_day_after)
        .where(Event.start_time < in_2_weeks)
        .order_by(Event.start_time)
    )
    later_events = session.exec(later_statement).all()

    # Build dict of event_id -> has_unpushed_changes for template
    unpushed_status = {}
    for event in today_events + tomorrow_events + later_events:
        unpushed_status[str(event.id)] = has_unpushed_changes(event)

    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "later_events": later_events,
            "has_auth": has_auth,
            "unpushed_status": unpushed_status,
            "today": now.date(),
        },
    )


@router.get("/archive", response_class=HTMLResponse)
async def archived_events(request: Request, session: Session = Depends(get_session)):
    """
    Display archived events.

    Shows all events that have been archived, sorted by start time (most recent first).
    Archived events are read-only and preserved for historical reference.
    """
    statement = (
        select(Event)
        .where(Event.is_archived == True)  # noqa: E712
        .order_by(Event.start_time.desc())
    )
    events = session.exec(statement).all()

    return templates.TemplateResponse(
        "archive.html",
        {"request": request, "events": events},
    )


@router.get("/{event_id}", response_class=HTMLResponse)
async def event_detail(
    event_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Display single event detail.

    Shows the full event with all checklist items, attendees, and confirmation status.
    Includes options to toggle items, add new items, confirm readiness, and archive.
    """
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return templates.TemplateResponse(
        "event_detail.html",
        {
            "request": request,
            "event": event,
            "has_unpushed": has_unpushed_changes(event),
            "today": datetime.now(UTC).date(),
        },
    )


@router.post("/{event_id}/confirm")
async def confirm_event(event_id: UUID, session: Session = Depends(get_session)):
    """
    Confirm event checklist is complete.

    Creates a confirmation record with a timestamp. Requires all checklist items
    to be checked before confirmation is allowed. Returns 400 if any items are
    unchecked or if the event is archived.
    """
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.is_archived:
        raise HTTPException(status_code=400, detail="Cannot confirm archived event")

    # Check all items are checked
    unchecked = [item for item in event.items if not item.is_checked]
    if unchecked:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm: {len(unchecked)} items unchecked",
        )

    # Create confirmation
    confirmation = ChecklistConfirmation(event_id=event.id)
    session.add(confirmation)
    session.commit()

    return RedirectResponse(f"/events/{event_id}", status_code=303)


@router.post("/{event_id}/archive")
async def archive_event(event_id: UUID, session: Session = Depends(get_session)):
    """
    Archive event (move to read-only).

    Archived events cannot be modified and are excluded from sync updates.
    They are preserved for historical reference and audit purposes.
    """
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.is_archived = True
    session.add(event)
    session.commit()

    return RedirectResponse("/events/archive", status_code=303)


@router.post("/{event_id}/unarchive")
async def unarchive_event(event_id: UUID, session: Session = Depends(get_session)):
    """
    Unarchive event.

    Restores an archived event to active status, allowing modifications
    and re-enabling sync updates from Google Calendar.
    """
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.is_archived = False
    session.add(event)
    session.commit()

    return RedirectResponse(f"/events/{event_id}", status_code=303)
