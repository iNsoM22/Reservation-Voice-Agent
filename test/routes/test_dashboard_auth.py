from fastapi import Request
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import create_app
from app.routes.dashboard_auth import require_dashboard_user


def client(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'auth.db'}",
            api_key="api",
            vapi_webhook_token="vapi",
            admin_email="admin@example.com",
            admin_password="secret password",
            dashboard_session_secret="long-random-secret-for-test-only",
        )
    )

    @app.get("/dashboard/private")
    def private(request: Request):
        return {"email": require_dashboard_user(request).email}

    return TestClient(app, follow_redirects=False)


def test_login_requires_csrf_and_sets_httponly_session(tmp_path):
    with client(tmp_path) as browser:
        unauthenticated = browser.get("/dashboard/private")
        assert unauthenticated.status_code == 303
        assert unauthenticated.headers["location"] == "/dashboard/login"
        login_page = browser.get("/dashboard/login")
        assert login_page.status_code == 200
        token = login_page.cookies["dashboard_csrf"]
        assert (
            browser.post(
                "/dashboard/login",
                data={"email": "admin@example.com", "password": "secret password"},
            ).status_code
            == 403
        )
        assert (
            browser.post(
                "/dashboard/login",
                data={
                    "email": "admin@example.com",
                    "password": "wrong",
                    "csrf_token": token,
                },
            ).status_code
            == 401
        )
        result = browser.post(
            "/dashboard/login",
            data={
                "email": "admin@example.com",
                "password": "secret password",
                "csrf_token": token,
            },
        )
        assert result.status_code == 303
        assert result.headers["location"] == "/dashboard"
        assert "httponly" in result.headers["set-cookie"].lower()
        assert browser.get("/dashboard/private").json() == {
            "email": "admin@example.com"
        }


def test_logout_requires_csrf_and_invalidates_session(tmp_path):
    with client(tmp_path) as browser:
        token = browser.get("/dashboard/login").cookies["dashboard_csrf"]
        browser.post(
            "/dashboard/login",
            data={
                "email": "admin@example.com",
                "password": "secret password",
                "csrf_token": token,
            },
        )
        assert browser.post("/dashboard/logout").status_code == 403
        assert (
            browser.post("/dashboard/logout", data={"csrf_token": token}).status_code
            == 303
        )
        assert "dashboard_session" not in browser.cookies
