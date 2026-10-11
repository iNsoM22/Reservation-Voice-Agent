from sqlalchemy import create_engine

from app.config.settings import Settings
from app.main import create_app


def test_heroku_postgres_url_uses_psycopg(monkeypatch):
    seen = []

    def capture_engine(url, **kwargs):
        seen.append(url)
        return create_engine("sqlite:///:memory:")

    monkeypatch.setattr("app.main.create_engine", capture_engine)
    create_app(
        Settings(
            database_url="postgres://user:password@db.example/patients",
            api_key="test",
            vapi_webhook_token="test",
        )
    )
    assert seen == ["postgresql+psycopg://user:password@db.example/patients"]
