from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class OAuthToken(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(default=1, index=True)
    access_token: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    expires_at: datetime
    scopes: str  # Comma-separated list of scopes
