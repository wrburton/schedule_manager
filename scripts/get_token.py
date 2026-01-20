#!/usr/bin/env python3
"""
One-time script to obtain Google OAuth refresh token.

Run this script locally once to get a refresh token, then add it to your .env file.

Usage:
    python scripts/get_token.py

Requirements:
    - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env
    - Or pass them as arguments: python scripts/get_token.py --client-id=XXX --client-secret=YYY
"""
import argparse
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def main():
    parser = argparse.ArgumentParser(description="Get Google OAuth refresh token")
    parser.add_argument("--client-id", help="Google OAuth Client ID")
    parser.add_argument("--client-secret", help="Google OAuth Client Secret")
    args = parser.parse_args()

    # Try to load from .env if not provided as arguments
    client_id = args.client_id
    client_secret = args.client_secret

    if not client_id or not client_secret:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
            client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        except ImportError:
            pass

    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required.")
        print()
        print("Either:")
        print("  1. Set them in .env file, or")
        print("  2. Pass them as arguments:")
        print("     python scripts/get_token.py --client-id=XXX --client-secret=YYY")
        sys.exit(1)

    # Create OAuth flow for installed/desktop app (no redirect URI needed)
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    # Allow HTTP for localhost (required for manual copy-paste flow)
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    print("=" * 60)
    print("Google Calendar OAuth Setup")
    print("=" * 60)
    print()
    print("Copy the URL below and open it in a browser (on any machine).")
    print("After authorizing, you'll be redirected to a localhost URL.")
    print("Copy the FULL redirect URL and paste it back here.")
    print()

    # Set redirect URI for manual copy-paste flow
    flow.redirect_uri = "http://localhost:8080/"

    # Generate authorization URL
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    print("Open this URL in a browser:")
    print()
    print(auth_url)
    print()

    # Get the full redirect URL from user
    redirect_response = input("Paste the full redirect URL here: ").strip()

    # Exchange the authorization response for credentials
    flow.fetch_token(authorization_response=redirect_response)
    credentials = flow.credentials

    print()
    print("=" * 60)
    print("SUCCESS! Add the following to your .env file:")
    print("=" * 60)
    print()
    print(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
