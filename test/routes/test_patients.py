from fastapi.testclient import TestClient
from sqlalchemy import text

PATIENT = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "04/12/1990",
    "sex": "Female",
    "phone_number": "415-555-0100",
    "address_line_1": "1 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94105",
}


def make_client(tmp_path):
    from app.config.settings import Settings
    from app.main import create_app

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'patients.db'}",
        api_key="test-api-key",
        vapi_webhook_token="test-vapi-token",
    )
    return TestClient(create_app(settings))


def test_crud_routes_share_persistent_service_and_envelope(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"X-API-Key": "test-api-key"}
        created = client.post("/patients", json=PATIENT, headers=headers)
        assert created.status_code == 201
        body = created.json()
        assert body["error"] is None
        assert body["data"]["date_of_birth"] == "04/12/1990"
        identifier = body["data"]["patient_id"]

        found = client.get(f"/patients/{identifier}", headers=headers)
        assert found.status_code == 200
        assert found.json()["data"]["first_name"] == "Jane"
        listed = client.get("/patients?last_name=Doe", headers=headers)
        assert len(listed.json()["data"]) == 1

        updated = client.put(
            f"/patients/{identifier}", json={"city": "Oakland"}, headers=headers
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["city"] == "Oakland"
        assert updated.json()["data"]["first_name"] == "Jane"

        deleted = client.delete(f"/patients/{identifier}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json()["data"]["deleted_at"] is not None
        assert client.get(f"/patients/{identifier}", headers=headers).status_code == 404
        assert client.get("/patients", headers=headers).json()["data"] == []

    with make_client(tmp_path) as client:
        assert client.get("/patients", headers=headers).json()["data"] == []


def test_patient_routes_require_api_key(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/patients")
        assert response.status_code == 401
        assert response.json()["data"] is None
        assert response.json()["error"]["code"] == "unauthorized"


def test_invalid_body_and_filter_return_consistent_errors(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"X-API-Key": "test-api-key"}
        invalid = client.post(
            "/patients", json={**PATIENT, "phone_number": "123"}, headers=headers
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["details"][0]["field"] == "phone_number"
        bad_filter = client.get("/patients?date_of_birth=2020-01-01", headers=headers)
        assert bad_filter.status_code == 400
        assert bad_filter.json()["error"]["code"] == "invalid_filter"


def test_missing_patient_and_empty_update(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"X-API-Key": "test-api-key"}
        identifier = "e11a4be2-8436-4e28-ab93-697b2b0fe0f9"
        assert client.get(f"/patients/{identifier}", headers=headers).status_code == 404
        assert (
            client.put(f"/patients/{identifier}", json={}, headers=headers).status_code
            == 400
        )


def test_database_failure_returns_generic_500_envelope_without_logging_patient_values(
    tmp_path, caplog
):
    with make_client(tmp_path) as client:
        with client.app.state.engine.begin() as connection:
            connection.execute(text("DROP TABLE patients"))

        response = client.get(
            "/patients?last_name=PrivateName",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 500
        assert response.json() == {
            "data": None,
            "error": {
                "code": "database_error",
                "message": "The database is temporarily unavailable",
            },
        }
        assert "PrivateName" not in caplog.text


def test_unknown_route_uses_error_envelope(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/does-not-exist")
        assert response.status_code == 404
        assert response.json() == {
            "data": None,
            "error": {"code": "not_found", "message": "Not found"},
        }
