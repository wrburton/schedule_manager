#!/usr/bin/env python3
"""
One-off script to push modified item lists to master recurring events.

This script compares local event items against the master recurring event
in Google Calendar and pushes any differences.

Usage:
    python scripts/push_to_master_events.py [--dry-run]

Options:
    --dry-run    Show what would be pushed without making changes
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

from googleapiclient.errors import HttpError
from sqlmodel import Session, select

from app.calendar.client import get_calendar_service, has_valid_credentials
from app.calendar.parser import parse_items_from_description
from app.calendar.sync import push_items_to_master_event
from app.core.config import settings
from app.core.database import engine
from app.models import Event


def fetch_master_event(service, calendar_id: str, recurring_event_id: str) -> dict | None:
    """Fetch the master recurring event from Google Calendar."""
    try:
        return service.events().get(
            calendarId=calendar_id,
            eventId=recurring_event_id,
        ).execute()
    except HttpError as e:
        print(f"  Warning: Could not fetch master event: {e}")
        return None


def main(dry_run: bool = False):
    """Compare local events against master events and push differences."""
    if not has_valid_credentials():
        print("Error: No valid Google Calendar credentials found.")
        print("Please run the app and complete OAuth setup first.")
        sys.exit(1)

    service = get_calendar_service()
    calendar_id = settings.google_calendar_id

    with Session(engine) as session:
        # Find non-archived recurring events
        now = datetime.utcnow()
        statement = (
            select(Event)
            .where(Event.is_archived == False)  # noqa: E712
            .where(Event.recurring_event_id.isnot(None))
            .where(Event.start_time >= now - timedelta(hours=2))
            .order_by(Event.start_time)
        )
        events = session.exec(statement).all()

        if not events:
            print("No recurring events found.")
            return

        # Group events by recurring_event_id
        events_by_master = {}
        for event in events:
            if event.recurring_event_id not in events_by_master:
                events_by_master[event.recurring_event_id] = []
            events_by_master[event.recurring_event_id].append(event)

        print(f"Found {len(events_by_master)} recurring event series to check:\n")

        # Compare each master event with local instances
        masters_to_push = {}

        for recurring_id, instances in events_by_master.items():
            # Get representative info
            title = instances[0].title
            print(f"Checking: {title}")
            print(f"  Master ID: {recurring_id}")
            print(f"  Local instances: {len(instances)}")

            # Fetch master event from Google Calendar
            master_event = fetch_master_event(service, calendar_id, recurring_id)
            if not master_event:
                continue

            # Parse items from master event description
            master_description = master_event.get("description", "")
            master_items = set(parse_items_from_description(master_description))
            print(f"  Master items: {sorted(master_items) if master_items else '(none)'}")

            # Get local items (use the instance with the most items)
            best_instance = max(instances, key=lambda e: len(e.items))
            local_items = {item.name for item in best_instance.items}
            print(f"  Local items:  {sorted(local_items) if local_items else '(none)'}")

            # Compare
            if local_items == master_items:
                print("  Status: In sync")
            else:
                added = local_items - master_items
                removed = master_items - local_items

                if added:
                    print(f"  + Added locally: {sorted(added)}")
                if removed:
                    print(f"  - Removed locally: {sorted(removed)}")

                masters_to_push[recurring_id] = {
                    "title": title,
                    "item_names": list(local_items),
                    "master_items": list(master_items),
                    "source_event": best_instance,
                }

            print()

        if not masters_to_push:
            print("All recurring events are in sync with their masters.")
            return

        print(f"\n=== {len(masters_to_push)} series need updating ===\n")

        for _recurring_id, data in masters_to_push.items():
            print(f"{data['title']}:")
            print(f"  Current master: {data['master_items']}")
            print(f"  Will become:    {data['item_names']}")
            print()

        if dry_run:
            print("--- DRY RUN: No changes made ---")
            return

        # Confirm before pushing
        response = input(f"Push changes to {len(masters_to_push)} master event(s)? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

        # Push to master recurring events
        success_count = 0
        fail_count = 0

        for recurring_id, data in masters_to_push.items():
            print(f"Pushing to '{data['title']}'...", end=" ")
            result = push_items_to_master_event(recurring_id, data["item_names"])
            if result is not None:
                print("OK")
                success_count += 1

                # Update local description for the source event
                source_event = data["source_event"]
                source_event.description = result
                session.add(source_event)
            else:
                print("FAILED")
                fail_count += 1

        session.commit()

        print(f"\nComplete: {success_count} succeeded, {fail_count} failed")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
