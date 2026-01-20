"""OAuth token model for Google API authentication.

This module defines the OAuthToken model which stores OAuth2 credentials
for accessing the Google Calendar API. Tokens are obtained through the
one-time setup script and used for ongoing API authentication.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class OAuthToken(SQLModel, table=True):
    """Stored OAuth2 credentials for Google Calendar API access.

    This model persists OAuth tokens obtained through the authorization
    flow. The refresh token is long-lived and used to obtain new access
    tokens when they expire.

    Note: In the current implementation, tokens are primarily managed
    through environment variables. This model supports future database-
    backed token storage for multi-user scenarios.

    Attributes:
        id: Unique identifier (UUID).
        user_id: User this token belongs to (for multi-user support).
        access_token: Short-lived token for API requests.
        refresh_token: Long-lived token used to obtain new access tokens.
        token_uri: Google's token endpoint URL.
        expires_at: When the access token expires.
        scopes: Comma-separated list of authorized OAuth scopes.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(default=1, index=True)
    access_token: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    expires_at: datetime
    scopes: str  # Comma-separated list of scopes
