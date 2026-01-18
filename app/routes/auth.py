"""Authentication status routes."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.calendar.client import has_valid_credentials

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
async def setup_instructions():
    """
    Display setup instructions if not authenticated.

    Shows step-by-step instructions for configuring Google OAuth credentials.
    If already authenticated, displays a confirmation message with a link
    to the events page.
    """
    if has_valid_credentials():
        return """
        <html>
        <head><title>Already Configured</title></head>
        <body>
            <h1>Credentials Already Configured</h1>
            <p>Google Calendar access is already set up.</p>
            <p><a href="/events/upcoming">Go to Events</a></p>
        </body>
        </html>
        """

    return """
    <html>
    <head>
        <title>Setup Required</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen p-8">
        <div class="max-w-2xl mx-auto bg-white rounded-lg shadow p-6">
            <h1 class="text-2xl font-bold text-gray-800 mb-4">Setup Required</h1>
            <p class="text-gray-600 mb-4">
                Google Calendar credentials need to be configured.
            </p>

            <h2 class="text-lg font-semibold text-gray-800 mt-6 mb-2">Steps:</h2>
            <ol class="list-decimal list-inside space-y-2 text-gray-700">
                <li>Create OAuth credentials in Google Cloud Console</li>
                <li>Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env</li>
                <li>Run: <code class="bg-gray-100 px-2 py-1 rounded">python scripts/get_token.py</code></li>
                <li>Copy the GOOGLE_REFRESH_TOKEN to your .env file</li>
                <li>Restart the application</li>
            </ol>

            <p class="text-gray-600 mt-6">
                See <a href="https://github.com/your-repo" class="text-blue-600">README.md</a> for detailed instructions.
            </p>
        </div>
    </body>
    </html>
    """
