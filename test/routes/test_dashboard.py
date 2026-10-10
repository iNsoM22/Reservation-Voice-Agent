from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.models.patient import Patient
from test.routes.test_patients import PATIENT


def make_client(tmp_path):
    from app.config.settings import Settings
    from app.main import create_app

    return TestClient(
        create_app(
            Settings(
                database_url=f"sqlite:///{tmp_path / 'dashboard.db'}",
                api_key="api",
                vapi_webhook_token="vapi",
                admin_email="admin@example.com",
                admin_password="secret password",
                dashboard_session_secret="session-secret-for-dashboard-tests",
            )
        ),
        follow_redirects=False,
    )


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


def test_dashboard_requires_login_and_lists_latest_patient_first(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/dashboard/patients")
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard/login"

        login(client)
        for first_name in ("Ada", "Grace", "Katherine"):
            client.post(
                "/patients",
                json={**PATIENT, "first_name": first_name},
                headers={"X-API-Key": "api"},
            )

        page = client.get("/dashboard/patients?page=1")
        assert page.status_code == 200
        assert page.text.index("Katherine Doe") < page.text.index("Grace Doe")
        assert page.text.index("Grace Doe") < page.text.index("Ada Doe")
        assert "Calls" in page.text and "Simulation" in page.text
        assert 'aria-current="page"' in page.text
        assert '<th scope="col">Patient</th>' in page.text
        assert '<caption class="sr-only">Registered patients</caption>' in page.text


def test_dashboard_paginates_and_patient_detail_hides_deleted(tmp_path):
    with make_client(tmp_path) as client:
        login(client)
        identifiers = []
        for index in range(11):
            created = client.post(
                "/patients",
                json={**PATIENT, "first_name": f"Patient{chr(65 + index)}"},
                headers={"X-API-Key": "api"},
            )
            identifiers.append(created.json()["data"]["patient_id"])
        with client.app.state.engine.begin() as connection:
            for index, identifier in enumerate(identifiers):
                connection.execute(
                    update(Patient)
                    .where(Patient.patient_id == UUID(identifier))
                    .values(
                        created_at=datetime(2026, 1, 1, tzinfo=UTC)
                        + timedelta(days=index)
                    )
                )
        first = client.get("/dashboard/patients?page=1")
        second = client.get("/dashboard/patients?page=2")
        assert "PatientK Doe" in first.text
        assert "PatientA Doe" not in first.text
        assert "PatientA Doe" in second.text
        assert 'aria-label="Previous page"' in second.text
        assert 'class="page-button disabled" href=' not in first.text
        assert 'class="page-button disabled" href=' not in second.text
        patient_id = first.text.split('href="/dashboard/patients/')[1].split('"')[0]
        detail = client.get(f"/dashboard/patients/{patient_id}")
        assert detail.status_code == 200
        assert "4155550100" in detail.text
        client.delete(f"/patients/{patient_id}", headers={"X-API-Key": "api"})
        assert client.get(f"/dashboard/patients/{patient_id}").status_code == 404
        assert client.get("/dashboard/patients?page=0").status_code == 422
