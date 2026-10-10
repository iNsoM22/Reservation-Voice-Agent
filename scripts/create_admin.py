"""Create the configured admin once: uv run python -m scripts.create_admin."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.models.patient import Base
from app.models.user import User  # noqa: F401 - registers table
from app.services.auth import bootstrap_admin


def main() -> None:
    settings = Settings.from_env()
    if not settings.admin_email or not settings.admin_password:
        raise SystemExit("Set ADMIN_EMAIL and ADMIN_PASSWORD first")
    engine = create_engine(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            created = bootstrap_admin(
                session, settings.admin_email, settings.admin_password
            )
        print("Admin created" if created else "Admin already exists")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
