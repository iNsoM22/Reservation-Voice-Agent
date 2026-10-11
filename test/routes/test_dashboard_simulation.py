from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import create_app
from test.routes.test_dashboard import login, make_client


def test_browser_voice_uses_saved_vapi_assistant_and_requires_login(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/dashboard/simulation").status_code == 303
        login(client)
        response = client.get("/dashboard/simulation")
        assert response.status_code == 200
        assert "Vapi browser voice" in response.text
        assert "vapi-widget" not in response.text

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'voice.db'}",
        api_key="api",
        vapi_webhook_token="vapi",
        admin_email="admin@example.com",
        admin_password="secret password",
        dashboard_session_secret="session-secret-for-dashboard-tests",
        vapi_public_key="public-test-key",
        vapi_assistant_id="assistant-test-id",
    )
    with TestClient(create_app(settings), follow_redirects=False) as client:
        login(client)
        page = client.get("/dashboard/simulation").text
        assert 'data-public-key="public-test-key"' in page
        assert 'data-assistant-id="assistant-test-id"' in page
        assert 'id="simulation-start-call"' in page
        assert 'id="simulation-end-call"' in page
        assert "vapi-widget" not in page
        assert "widget.umd.js" not in page
        assert 'id="simulation-phone"' in page
        assert "simulation-caller.js" in page
        assert 'id="simulation-voice-controls"' in page


def test_scripted_simulation_endpoints_are_removed(tmp_path):
    with make_client(tmp_path) as client:
        login(client)
        assert client.post("/dashboard/simulation/calls").status_code == 404
        assert client.get("/dashboard/simulation/current").status_code == 404
