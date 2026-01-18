"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or .env file."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "Calendar Checklist"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Server
    host: str = "0.0.0.0"  # Bind to all interfaces for external access
    port: int = 8000
    allowed_origins: str = "*"  # Comma-separated origins, or "*" for all

    # Database
    database_url: str = "sqlite:///./calendar_checklist.db"

    # Google Calendar API
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""  # Obtained via scripts/get_token.py
    google_calendar_id: str = "primary"

    # Sync settings
    sync_interval_minutes: int = 5


settings = Settings()
