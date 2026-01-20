"""Calendar synchronization service."""
import logging
from datetime import UTC, datetime, timedelta

from googleapiclient.errors import HttpError
from sqlmodel import Session, select

from app.calendar.client import get_calendar_service, has_valid_credentials
from app.calendar.parser import format_items_to_description, parse_items_from_description
from app.core.config import settings
from app.models import Attendee, Event, Item

logger = logging.getLogger(__name__)


class SyncState:
    """In-memory storage for Google Calendar sync tokens and status.

    Google Calendar API uses sync tokens for incremental synchronization.
    After a full sync, the API returns a nextSyncToken. On subsequent
    syncs, providing this token returns only events that changed since
    the last sync, dramatically reducing API calls and data transfer.

    This class stores tokens in memory (lost on restart). When a token
    is missing or expired (HTTP 410), a full sync is performed and a
    new token is obtained.

    Attributes:
        _tokens: Dictionary mapping calendar IDs to their sync tokens.
        _last_sync_time: Timestamp of the last sync attempt.
        _last_sync_success: Whether the last sync succeeded.
        _last_sync_error: Error message from the last failed sync, if any.
    """

    _tokens: dict[str, str] = {}
    _last_sync_time: datetime | None = None
    _last_sync_success: bool = True
    _last_sync_error: str | None = None

    @classmethod
    def get_token(cls, calendar_id: str) -> str | None:
        return cls._tokens.get(calendar_id)

    @classmethod
    def set_token(cls, calendar_id: str, token: str) -> None:
        cls._tokens[calendar_id] = token

    @classmethod
    def clear_token(cls, calendar_id: str) -> None:
        cls._tokens.pop(calendar_id, None)

    @classmethod
    def record_sync_success(cls) -> None:
        """Record a successful sync."""
        cls._last_sync_time = datetime.now(UTC)
        cls._last_sync_success = True
        cls._last_sync_error = None

    @classmethod
    def record_sync_failure(cls, error: str) -> None:
        """Record a failed sync with error message."""
        cls._last_sync_time = datetime.now(UTC)
        cls._last_sync_success = False
        cls._last_sync_error = error

    @classmethod
    def get_sync_status(cls) -> dict:
        """Get the current sync status."""
        return {
            "last_sync_time": cls._last_sync_time,
            "success": cls._last_sync_success,
            "error": cls._last_sync_error,
        }


def sync_calendar(session: Session) -> dict:
    """
    Sync events from Google Calendar.

    Returns dict with sync statistics.
    """
    if not has_valid_credentials():
        logger.warning("No valid credentials, skipping sync")
        SyncState.record_sync_failure("No valid credentials")
        return {"error": "No valid credentials", "created": 0, "updated": 0, "deleted": 0}

    calendar_id = settings.google_calendar_id
    sync_token = SyncState.get_token(calendar_id)

    stats = {"created": 0, "updated": 0, "deleted": 0}
    is_full_sync = not sync_token
    seen_google_ids = set()  # Track events returned by API during full sync

    try:
        service = get_calendar_service()
        if sync_token:
            # Incremental sync
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    syncToken=sync_token,
                    singleEvents=True,
                )
                .execute()
            )
        else:
            # Full sync - get events from 2 hours ago to 30 days ahead
            # Note: Google API timeMin filters by start time; display uses end_time + 2 hours
            time_min = (datetime.now(UTC) - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
            time_max = (datetime.now(UTC) + timedelta(days=30)).isoformat().replace("+00:00", "Z")

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

        # Process events
        for google_event in events_result.get("items", []):
            if google_event.get("status") == "cancelled":
                # Handle deletion
                deleted = _handle_deleted_event(session, google_event["id"])
                if deleted:
                    stats["deleted"] += 1
            else:
                if is_full_sync:
                    seen_google_ids.add(google_event["id"])
                created = _upsert_event(session, google_event)
                if created:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

        # Handle pagination for large result sets.
        # Google Calendar API returns max ~250 events per page. When there are more,
        # it includes a nextPageToken. We must fetch all pages to ensure we don't
        # miss events during sync.
        #
        # Note: The event processing logic is duplicated here rather than extracted
        # to a helper function because:
        # 1. It keeps the sync flow linear and easy to follow
        # 2. The processing is simple (just upsert/delete calls)
        # 3. A helper would need many parameters (session, stats, is_full_sync, seen_google_ids)
        while "nextPageToken" in events_result:
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    pageToken=events_result["nextPageToken"],
                    singleEvents=True,
                )
                .execute()
            )

            for google_event in events_result.get("items", []):
                if google_event.get("status") == "cancelled":
                    deleted = _handle_deleted_event(session, google_event["id"])
                    if deleted:
                        stats["deleted"] += 1
                else:
                    if is_full_sync:
                        seen_google_ids.add(google_event["id"])
                    created = _upsert_event(session, google_event)
                    if created:
                        stats["created"] += 1
                    else:
                        stats["updated"] += 1

        # During full sync, delete local events that no longer exist in Google Calendar
        if is_full_sync:
            orphan_count = _cleanup_orphaned_events(session, seen_google_ids)
            stats["deleted"] += orphan_count

        # Store new sync token
        new_token = events_result.get("nextSyncToken")
        if new_token:
            SyncState.set_token(calendar_id, new_token)

        session.commit()
        SyncState.record_sync_success()

    except HttpError as e:
        if e.resp.status == 410:
            # Sync token expired, do full sync
            logger.info("Sync token expired, performing full sync")
            SyncState.clear_token(calendar_id)
            return sync_calendar(session)
        logger.error(f"Sync failed: {e}")
        SyncState.record_sync_failure(str(e))
        raise
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        SyncState.record_sync_failure(str(e))
        raise

    logger.info(f"Sync completed: {stats}")
    return stats


def _parse_datetime(dt_dict: dict) -> datetime:
    """Parse datetime from Google Calendar format."""
    dt_str = dt_dict.get("dateTime") or dt_dict.get("date")
    if "T" in dt_str:
        # DateTime with timezone
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    else:
        # All-day event (date only)
        return datetime.strptime(dt_str, "%Y-%m-%d")


def _cleanup_orphaned_instance(
    session: Session,
    recurring_event_id: str,
    new_start_time: datetime,
    new_google_id: str,
) -> bool:
    """
    Clean up orphaned recurring event instances when a new exception is created.

    **The Problem:**
    When a user reschedules a single instance of a recurring event in Google
    Calendar (e.g., moves "Weekly Meeting" from Monday 10am to Monday 2pm),
    Google creates a NEW event ID for the exception. The original instance
    is marked as "cancelled" in Google's system.

    During *incremental* sync, we see the cancellation and delete the old
    instance. But during *full* sync (which happens on first run or when
    the sync token expires), cancelled events are NOT returned by the API.
    This leaves the old instance orphaned in our database.

    **The Solution:**
    When processing an event that belongs to a recurring series, look for
    other instances of the SAME series on the SAME calendar day with a
    DIFFERENT Google ID. If found, those are orphans that should be deleted.

    **Why same-day matching works:**
    - A recurring event can only have one instance per scheduled occurrence
    - If we see two instances of "Weekly Team Sync" on the same Monday,
      one of them must be an orphan from a rescheduled event

    Returns True if an orphan was deleted.
    """
    # Define the calendar day boundaries for the new event.
    # We search within this day because recurring series typically have
    # at most one instance per day (the original scheduled occurrence).
    day_start = new_start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    # Query for potential orphans: same recurring series, same day, different ID
    statement = (
        select(Event)
        .where(Event.recurring_event_id == recurring_event_id)  # Same series
        .where(Event.google_event_id != new_google_id)  # Different instance
        .where(Event.start_time >= day_start)  # On the same
        .where(Event.start_time < day_end)  # calendar day
        .where(Event.is_archived == False)  # Don't touch archived events
    )
    orphans = session.exec(statement).all()

    for orphan in orphans:
        logger.info(
            f"Removing orphaned recurring instance: {orphan.title} at {orphan.start_time} "
            f"(replaced by new instance at {new_start_time})"
        )
        # Must manually delete related records due to SQLite foreign key handling.
        # SQLModel relationships don't auto-cascade deletes in all cases.
        for item in orphan.items:
            session.delete(item)
        for attendee in orphan.attendees:
            session.delete(attendee)
        for confirmation in orphan.confirmations:
            session.delete(confirmation)
        session.delete(orphan)

    return len(orphans) > 0


def _upsert_event(session: Session, google_event: dict) -> bool:
    """Create or update an event from Google Calendar data.

    This function implements the core sync conflict resolution rules:

    **Source of Truth Rules:**
    - Google Calendar is authoritative for event metadata (title, times, description)
    - Local database is authoritative for checklist state (is_checked)
    - Archived events are never modified

    **Conflict Resolution:**
    - Time change detected → Reset all checklist items to unchecked
      (Rationale: A rescheduled event may require re-preparation)
    - Description change → Items re-parsed, new items added, missing items deleted
      (Existing items preserve their checked state)

    Returns:
        True if a new event was created, False if existing event was updated.
    """
    google_id = google_event["id"]

    statement = select(Event).where(Event.google_event_id == google_id)
    existing = session.exec(statement).first()

    start_time = _parse_datetime(google_event["start"])
    end_time = _parse_datetime(google_event["end"])

    if existing:
        # === CONFLICT RESOLUTION: Time Change Detection ===
        # Compare stored times with incoming times to detect rescheduling.
        # This is a key business rule: if an event is moved to a different time,
        # we assume the user needs to re-verify their preparation checklist.
        time_changed = existing.start_time != start_time or existing.end_time != end_time

        # Update all Google-authoritative fields
        existing.title = google_event.get("summary", "Untitled")
        existing.description = google_event.get("description")
        existing.start_time = start_time
        existing.end_time = end_time
        existing.recurring_event_id = google_event.get("recurringEventId")
        existing.last_synced = datetime.now(UTC)

        # === CONFLICT RESOLUTION: Checklist Reset on Time Change ===
        # Only reset if the event hasn't been archived (archived = frozen state).
        # This ensures users re-check items when meetings are rescheduled.
        if time_changed and not existing.is_archived:
            logger.info(f"Event time changed, resetting checklist for {existing.title}")
            for item in existing.items:
                item.is_checked = False

        # Handle orphaned recurring instances (see _cleanup_orphaned_instance docstring)
        recurring_event_id = google_event.get("recurringEventId")
        if recurring_event_id:
            _cleanup_orphaned_instance(session, recurring_event_id, start_time, google_id)

        # Sync items and attendees from the updated description
        _sync_items(session, existing, google_event.get("description"))
        _sync_attendees(session, existing, google_event.get("attendees", []))

        session.add(existing)
        return False
    else:
        # === NEW EVENT CREATION ===
        recurring_event_id = google_event.get("recurringEventId")

        # For recurring events: check if this new event ID replaces an existing
        # instance on the same day (happens when Google creates a new ID for
        # rescheduled recurring instances)
        if recurring_event_id:
            _cleanup_orphaned_instance(session, recurring_event_id, start_time, google_id)

        event = Event(
            google_event_id=google_id,
            recurring_event_id=recurring_event_id,
            title=google_event.get("summary", "Untitled"),
            description=google_event.get("description"),
            start_time=start_time,
            end_time=end_time,
        )
        session.add(event)
        session.flush()  # Get event.id

        _sync_items(session, event, google_event.get("description"))
        _sync_attendees(session, event, google_event.get("attendees", []))

        return True


def _sync_items(session: Session, event: Event, description: str | None) -> None:
    """Synchronize checklist items from an event's description.

    Parses the event description for checklist items and reconciles them
    with existing items in the database. This implements the sync conflict
    resolution rules:

    - New items in description: Added to database with source="parsed"
    - Items removed from description: Deleted from database
    - Existing items: Preserved with their current is_checked state
    - Archived events: Skipped entirely (no modifications)

    Note: This function deletes ALL items not in the parsed description,
    including manual items. The sync service treats the description as
    the source of truth for item lists.

    Args:
        session: Database session for persistence.
        event: The event to sync items for.
        description: Event description text to parse, may be None.
    """
    if event.is_archived:
        return  # Don't modify archived events

    parsed_items = parse_items_from_description(description)
    parsed_set = set(parsed_items)

    # Get all existing items by name
    existing_items = {item.name: item for item in event.items}

    # Add new items from description
    for name in parsed_set:
        if name not in existing_items:
            item = Item(event_id=event.id, name=name, source="parsed")
            session.add(item)

    # Remove items no longer in description (both parsed and manual)
    for name, item in existing_items.items():
        if name not in parsed_set:
            session.delete(item)


def _sync_attendees(session: Session, event: Event, attendees: list) -> None:
    """Synchronize attendees from Google Calendar event data.

    Replaces all existing attendees with the current list from Google.
    Unlike items, attendees have no local state to preserve, so a full
    replacement is simpler and ensures consistency with Google Calendar.

    Args:
        session: Database session for persistence.
        event: The event to sync attendees for.
        attendees: List of attendee dicts from Google Calendar API,
            each containing 'email', optional 'displayName', and
            'responseStatus' fields.
    """
    # Clear existing and recreate
    for attendee in event.attendees:
        session.delete(attendee)

    for att in attendees:
        attendee = Attendee(
            event_id=event.id,
            email=att.get("email", ""),
            display_name=att.get("displayName"),
            response_status=att.get("responseStatus", "needsAction"),
        )
        session.add(attendee)


def _cleanup_orphaned_events(session: Session, seen_google_ids: set) -> int:
    """
    Remove local events that no longer exist in Google Calendar.

    Called during full sync to detect and remove events that were deleted
    from Google Calendar while the app was not running (sync token lost).

    Args:
        session: Database session
        seen_google_ids: Set of google_event_ids returned by the API

    Returns:
        Number of events deleted
    """
    # Find non-archived events within the sync window that weren't returned by API
    # Use end_time to match display logic (events shown until 2 hours after they finish)
    time_min = datetime.now(UTC) - timedelta(hours=2)
    time_max = datetime.now(UTC) + timedelta(days=30)

    statement = (
        select(Event)
        .where(Event.is_archived == False)
        .where(Event.end_time >= time_min)
        .where(Event.start_time < time_max)
    )
    local_events = session.exec(statement).all()

    deleted_count = 0
    for event in local_events:
        if event.google_event_id not in seen_google_ids:
            logger.info(f"Removing orphaned event (deleted from Google): {event.title}")
            # Delete related records
            for item in event.items:
                session.delete(item)
            for attendee in event.attendees:
                session.delete(attendee)
            for confirmation in event.confirmations:
                session.delete(confirmation)
            session.delete(event)
            deleted_count += 1

    return deleted_count


def _handle_deleted_event(session: Session, google_id: str) -> bool:
    """Handle event deletion from Google. Returns True if deleted."""
    statement = select(Event).where(Event.google_event_id == google_id)
    event = session.exec(statement).first()

    if event and not event.is_archived:
        # Delete non-archived events
        for item in event.items:
            session.delete(item)
        for attendee in event.attendees:
            session.delete(attendee)
        for confirmation in event.confirmations:
            session.delete(confirmation)
        session.delete(event)
        return True
    return False


def has_unpushed_changes(event: Event) -> bool:
    """
    Check if local items differ from what's stored in Google Calendar.

    Compares current item names with items parsed from the event description
    (which represents the last synced state from Google Calendar).
    """
    local_names = {item.name for item in event.items}
    parsed_names = set(parse_items_from_description(event.description))
    return local_names != parsed_names


def push_items_to_calendar(event: Event) -> str | None:
    """
    Push item changes back to Google Calendar.

    Updates the event description with current items.

    Returns:
        The new description string on success, None on failure.
    """
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id

    try:
        # Get current event from Google
        google_event = (
            service.events()
            .get(calendarId=calendar_id, eventId=event.google_event_id)
            .execute()
        )

        # Format items into description
        item_names = [item.name for item in event.items]
        new_description = format_items_to_description(
            item_names, google_event.get("description", "")
        )

        # Update
        google_event["description"] = new_description
        service.events().update(
            calendarId=calendar_id,
            eventId=event.google_event_id,
            body=google_event,
        ).execute()

        logger.info(f"Pushed items to calendar for event: {event.title}")
        return new_description

    except HttpError as e:
        logger.error(f"Failed to push items to calendar: {e}")
        return None


def push_items_to_master_event(recurring_event_id: str, item_names: list[str]) -> str | None:
    """
    Push item changes to the master recurring event in Google Calendar.

    Updating the master event's description propagates to all future instances
    that don't have their own custom description (exceptions).

    Args:
        recurring_event_id: The ID of the master recurring event
        item_names: List of item names to include in the description

    Returns:
        The new description string on success, None on failure.
    """
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id

    try:
        # Fetch the master recurring event
        master_event = (
            service.events()
            .get(calendarId=calendar_id, eventId=recurring_event_id)
            .execute()
        )

        # Format items into description
        new_description = format_items_to_description(
            item_names, master_event.get("description", "")
        )

        # Update the master event
        master_event["description"] = new_description
        service.events().update(
            calendarId=calendar_id,
            eventId=recurring_event_id,
            body=master_event,
        ).execute()

        logger.info(f"Pushed items to master recurring event: {recurring_event_id}")
        return new_description

    except HttpError as e:
        logger.error(f"Failed to push items to master recurring event: {e}")
        return None


def push_item_to_recurring_instances(
    session: Session,
    source_event: Event,
    item_name: str,
) -> dict:
    """
    Add an item to all future instances of a recurring event.

    Updates the master recurring event in Google Calendar so the item
    propagates to all future instances (including those beyond the sync window).
    Also adds the item to local DB instances within the sync window.

    Args:
        session: Database session
        source_event: The event the item was originally added to
        item_name: Name of the item to add

    Returns:
        dict with keys: added, skipped, master_pushed
    """
    if not source_event.recurring_event_id:
        return {"added": 0, "skipped": 0, "master_pushed": False}

    stats = {"added": 0, "skipped": 0, "master_pushed": False}

    # Push to master recurring event (affects all future instances in Google Calendar)
    # Use the source event's items as the definitive list
    item_names = [item.name for item in source_event.items]
    result = push_items_to_master_event(source_event.recurring_event_id, item_names)
    stats["master_pushed"] = result is not None

    if not stats["master_pushed"]:
        logger.warning("Failed to push to master event, falling back to instance-only update")

    # Also add to local DB instances within the sync window
    now = datetime.now(UTC)
    statement = (
        select(Event)
        .where(Event.recurring_event_id == source_event.recurring_event_id)
        .where(Event.start_time > now)
        .where(Event.id != source_event.id)
        .where(Event.is_archived == False)
    )
    instances = session.exec(statement).all()

    # Filter out confirmed events
    instances = [e for e in instances if not e.confirmations]

    for event in instances:
        # Check for duplicate item name (case-insensitive)
        existing_names = {item.name.lower() for item in event.items}
        if item_name.lower() in existing_names:
            stats["skipped"] += 1
            continue

        # Add item to database
        new_item = Item(event_id=event.id, name=item_name, source="parsed")
        session.add(new_item)
        stats["added"] += 1

    session.commit()
    logger.info(f"Added item to recurring instances: {stats}")
    return stats


def delete_item_from_recurring_instances(
    session: Session,
    source_event: Event,
    item_name: str,
) -> dict:
    """
    Delete an item from all future instances of a recurring event.

    Updates the master recurring event in Google Calendar so the deletion
    propagates to all future instances (including those beyond the sync window).
    Also deletes from local DB instances within the sync window.

    Args:
        session: Database session
        source_event: The event the item was originally deleted from
        item_name: Name of the item to delete

    Returns:
        dict with keys: deleted, skipped, master_pushed
    """
    if not source_event.recurring_event_id:
        return {"deleted": 0, "skipped": 0, "master_pushed": False}

    stats = {"deleted": 0, "skipped": 0, "master_pushed": False}

    # Push to master recurring event (affects all future instances in Google Calendar)
    # Use the source event's items as the definitive list (item already deleted from source)
    item_names = [item.name for item in source_event.items]
    result = push_items_to_master_event(source_event.recurring_event_id, item_names)
    stats["master_pushed"] = result is not None

    if not stats["master_pushed"]:
        logger.warning("Failed to push to master event, falling back to instance-only update")

    # Also delete from local DB instances within the sync window
    now = datetime.now(UTC)
    statement = (
        select(Event)
        .where(Event.recurring_event_id == source_event.recurring_event_id)
        .where(Event.start_time > now)
        .where(Event.id != source_event.id)
        .where(Event.is_archived == False)
    )
    instances = session.exec(statement).all()

    # Filter out confirmed events
    instances = [e for e in instances if not e.confirmations]

    item_name_lower = item_name.lower()

    for event in instances:
        # Find item by name (case-insensitive)
        matching_item = None
        for item in event.items:
            if item.name.lower() == item_name_lower:
                matching_item = item
                break

        if not matching_item:
            stats["skipped"] += 1
            continue

        # Delete the item from local DB
        session.delete(matching_item)
        stats["deleted"] += 1

    session.commit()
    logger.info(f"Deleted item from recurring instances: {stats}")
    return stats


def push_recurring_instances(session: Session, source_event: Event) -> dict:
    """
    Push all recurring instances that have unpushed changes to Google Calendar.

    Also updates local event descriptions to match what was pushed, so the
    "unpushed changes" indicator updates immediately without requiring a sync.

    Args:
        session: Database session
        source_event: The event that triggered the push

    Returns:
        dict with keys: pushed, skipped, failed
    """
    stats = {"pushed": 0, "skipped": 0, "failed": 0}

    # Push the source event first if it has changes
    if has_unpushed_changes(source_event):
        new_desc = push_items_to_calendar(source_event)
        if new_desc is not None:
            source_event.description = new_desc
            session.add(source_event)
            stats["pushed"] += 1
        else:
            stats["failed"] += 1
    else:
        stats["skipped"] += 1

    # If not a recurring event, we're done
    if not source_event.recurring_event_id:
        session.commit()
        return stats

    # Find all other instances with the same recurring_event_id
    statement = (
        select(Event)
        .where(Event.recurring_event_id == source_event.recurring_event_id)
        .where(Event.id != source_event.id)
        .where(Event.is_archived == False)
    )
    instances = session.exec(statement).all()

    # Push only those with unpushed changes
    for event in instances:
        if not has_unpushed_changes(event):
            stats["skipped"] += 1
            continue

        new_desc = push_items_to_calendar(event)
        if new_desc is not None:
            event.description = new_desc
            session.add(event)
            stats["pushed"] += 1
        else:
            stats["failed"] += 1

    session.commit()
    logger.info(f"Push recurring instances: {stats}")
    return stats
