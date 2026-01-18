"""Google Calendar API client using pre-authorized credentials."""
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

# Scopes for Google Calendar API
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

# Cached credentials and service
_credentials: Credentials | None = None
_service = None


def get_credentials() -> Credentials | None:
    """Get credentials using pre-authorized refresh token from environment."""
    global _credentials

    if not settings.google_refresh_token:
        logger.warning("No GOOGLE_REFRESH_TOKEN configured")
        return None

    if _credentials and not _credentials.expired:
        return _credentials

    # Create credentials from refresh token
    _credentials = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    # Refresh to get access token
    if _credentials.expired or not _credentials.token:
        try:
            _credentials.refresh(Request())
            logger.info("Refreshed Google API credentials")
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            _credentials = None
            return None

    return _credentials


def get_calendar_service():
    """Build authenticated Calendar API service."""
    global _service

    creds = get_credentials()
    if not creds:
        raise ValueError(
            "No valid credentials. Run 'python scripts/get_token.py' to set up authentication."
        )

    # Reuse service if credentials haven't changed
    if _service and not creds.expired:
        return _service

    _service = build("calendar", "v3", credentials=creds)
    return _service


def has_valid_credentials() -> bool:
    """Check if valid credentials are configured."""
    return bool(settings.google_refresh_token)
