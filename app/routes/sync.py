"""Sync routes for triggering and monitoring calendar sync."""
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.calendar.client import has_valid_credentials
from app.calendar.sync import SyncState, sync_calendar
from app.core.config import settings
from app.core.database import get_session

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/now")
async def trigger_sync(session: Session = Depends(get_session)):
    """
    Manually trigger calendar sync.

    Performs an immediate sync with Google Calendar, fetching any new or
    updated events. Redirects to the auth setup page if credentials are
    not configured, otherwise redirects to the upcoming events page.
    """
    if not has_valid_credentials():
        SyncState.record_sync_failure("No valid credentials")
        return RedirectResponse("/auth/setup", status_code=303)

    try:
        sync_calendar(session)
    except Exception:
        # Failure already recorded in sync_calendar, just redirect to show the banner
        pass

    # Redirect back to upcoming events after sync (banner will show if sync failed)
    return RedirectResponse("/events/upcoming", status_code=303)


@router.get("/status")
async def sync_status():
    """
    Get current sync status.

    Returns JSON with authentication status, sync token presence,
    sync interval configuration, and the calendar ID being synced.
    """
    has_sync_token = SyncState.get_token(settings.google_calendar_id) is not None
    has_auth = has_valid_credentials()
    status = SyncState.get_sync_status()

    return {
        "authenticated": has_auth,
        "has_sync_token": has_sync_token,
        "sync_interval_minutes": settings.sync_interval_minutes,
        "calendar_id": settings.google_calendar_id,
        "last_sync_time": status["last_sync_time"].isoformat() if status["last_sync_time"] else None,
        "last_sync_success": status["success"],
        "last_sync_error": status["error"],
    }
