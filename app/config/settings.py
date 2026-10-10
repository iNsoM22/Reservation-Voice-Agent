"""Environment-backed application settings."""

from dataclasses import dataclass
from pathlib import Path

from starlette.config import Config


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_key: str
    vapi_webhook_token: str
    admin_email: str = ""
    admin_password: str = ""
    dashboard_session_secret: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        config = Config(".env" if Path(".env").is_file() else None)
        return cls(
            database_url=config("DATABASE_URL", default="sqlite:///./patients.db"),
            api_key=config("API_KEY", default=""),
            vapi_webhook_token=config("VAPI_WEBHOOK_TOKEN", default=""),
            admin_email=config("ADMIN_EMAIL", default=""),
            admin_password=config("ADMIN_PASSWORD", default=""),
            dashboard_session_secret=config("DASHBOARD_SESSION_SECRET", default=""),
        )
