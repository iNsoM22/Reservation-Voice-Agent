from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.routes.dashboard_calls import router as call_logs_router
from app.services.call_logs import CallLogService


def make_client(tmp_path):
    from app.config.settings import Settings
    from app.main import create_app

    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'calls-dashboard.db'}",
            api_key="api",
            vapi_webhook_token="vapi",
            admin_email="admin@example.com",
            admin_password="secret password",
            dashboard_session_secret="dashboard-session-secret",
        )
    )
    if not any(
        getattr(route, "path", None) == "/dashboard/calls" for route in app.routes
    ):
        app.include_router(call_logs_router)
    return TestClient(app, follow_redirects=False)


def login(client):
    token = client.get("/dashboard/login").cookies["dashboard_csrf"]
    return client.post(
        "/dashboard/login",
        data={
            "email": "admin@example.com",
            "password": "secret password",
            "csrf_token": token,
        },
    )


def test_call_log_pages_require_login_and_show_conversation(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/dashboard/calls").status_code == 303
        login(client)
        with Session(client.app.state.engine) as session:
            row = CallLogService(session).log_simulation(
                "sim-html",
                "Caller: <script>alert('x')</script>",
                [{"role": "user", "message": "<script>alert('x')</script>"}],
            )
            identifier = row.call_log_id
        listing = client.get("/dashboard/calls")
        assert listing.status_code == 200
        assert "Call logs" in listing.text
        assert 'href="/dashboard/calls" aria-label="Calls"' in listing.text
        assert (
            'class="nav-link active" href="/dashboard/calls" aria-label="Calls" aria-current="page"'
            in listing.text
        )
        assert '<caption class="sr-only">Recorded calls</caption>' in listing.text
        assert '<th scope="col">Conversation</th>' in listing.text
        assert "sim-html" not in listing.text
        detail = client.get(f"/dashboard/calls/{identifier}")
        assert detail.status_code == 200
        assert 'class="details"' in detail.text
        assert 'class="transcript"' in detail.text
        assert "Caller: &lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;" in detail.text
        assert "Conversation messages" in detail.text


def test_call_log_pages_20_per_page_newest_first(tmp_path):
    with make_client(tmp_path) as client:
        login(client)
        with Session(client.app.state.engine) as session:
            service = CallLogService(session)
            for index in range(21):
                service.log_simulation(
                    f"sim-{index:02}",
                    f"Conversation {index:02}",
                    [],
                    started_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
                )
        first = client.get("/dashboard/calls?page=1")
        second = client.get("/dashboard/calls?page=2")
        assert first.text.index("Conversation 20") < first.text.index("Conversation 19")
        assert "Conversation 00" not in first.text
        assert "Conversation 00" in second.text
        assert client.get("/dashboard/calls?page=0").status_code == 422
        assert client.get("/dashboard/calls?page=1").status_code == 200
