"""Authentication status routes."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.calendar.client import has_valid_credentials
from app.calendar.sync import SyncState
from app.web import templates

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
async def auth_status():
    """
    Check if calendar credentials are configured.

    Returns JSON with authentication status and a message indicating
    whether credentials are configured or setup is required.
    """
    return {
        "authenticated": has_valid_credentials(),
        "message": (
            "Credentials configured"
            if has_valid_credentials()
            else "Run 'python scripts/get_token.py' to set up authentication"
        ),
    }


@router.get("/setup", response_class=HTMLResponse)
async def setup_instructions(request: Request):
    """
    Display setup instructions if not authenticated or if credentials are invalid.

    Shows step-by-step instructions for configuring Google OAuth credentials.
    If already authenticated and working, displays a confirmation message with a link
    to the events page.
    """
    # Check if there's a credential-related sync error
    sync_status = SyncState.get_sync_status()
    has_credential_error = bool(
        not sync_status["success"]
        and sync_status["error"]
        and "credential" in sync_status["error"].lower()
    )
    configured = has_valid_credentials() and not has_credential_error
    return templates.TemplateResponse(request, "setup.html", {"configured": configured})
