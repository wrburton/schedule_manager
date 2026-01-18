"""Background job scheduler for calendar syncing."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session

from app.calendar.sync import sync_calendar
from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def sync_job():
    """Background sync job."""
    try:
        with Session(engine) as session:
            stats = sync_calendar(session)
            logger.info(f"Background sync completed: {stats}")
    except Exception as e:
        logger.error(f"Background sync failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        sync_job,
        trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
        id="calendar_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started, syncing every {settings.sync_interval_minutes} minutes"
    )


def shutdown_scheduler():
    """Graceful shutdown."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
