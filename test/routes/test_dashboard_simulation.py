from sqlalchemy.orm import Session

from app.services.call_logs import CallLogService
from test.routes.test_dashboard import login, make_client


def test_simulation_is_authenticated_and_csrf_protected(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/dashboard/simulation").status_code == 303
        login(client)
        assert client.get("/dashboard/simulation").status_code == 200
        assert client.post("/dashboard/simulation/calls").status_code == 403
        token = client.cookies["dashboard_csrf"]
        created = client.post(
            "/dashboard/simulation/calls", headers={"X-CSRF-Token": token}
        )
        assert created.status_code == 200
        assert "first name" in created.json()["assistant"].lower()
        current = client.get("/dashboard/simulation/current")
        assert current.json()["call_id"] == created.json()["call_id"]


def test_simulation_validates_gathers_confirms_and_saves_once(tmp_path):
    answers = [
        "Ada",
        "Lovelace",
        "January 1, 1990",
        "female",
        "555",
        "4155550100",
        "1 Main St",
        "Oakland",
        "CA",
        "94607",
    ]
    with make_client(tmp_path) as client:
        login(client)
        csrf = client.cookies["dashboard_csrf"]
        state = client.post(
            "/dashboard/simulation/calls", headers={"X-CSRF-Token": csrf}
        ).json()
        assert state["assistant"].lower().find("first name") >= 0
        call_id = state["call_id"]
        response = client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "A1"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 200
        assert "letters" in response.json()["assistant"].lower()
        for answer in answers:
            response = client.post(
                f"/dashboard/simulation/calls/{call_id}/turn",
                json={"text": answer},
                headers={"X-CSRF-Token": csrf},
            )
        assert "confirm" in response.json()["assistant"].lower()
        assert response.json()["patient_id"] is None
        response = client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "yes"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.json()["patient_id"]
        patient_id = response.json()["patient_id"]
        call_id_log = None
        with Session(client.app.state.engine) as session:
            log = CallLogService(session).get(call_id)
            call_id_log = log.call_log_id
            assert log.source == "simulation"
            assert log.patient_id is not None
            assert "Caller: yes" in log.transcript
            assert log.started_at and log.ended_at
        repeated = client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "yes"},
            headers={"X-CSRF-Token": csrf},
        )
        assert repeated.json()["patient_id"] == patient_id
        assert client.get(f"/dashboard/calls/{call_id_log}").status_code == 200
        assert client.get("/dashboard/patients").status_code == 200


def test_simulation_correction_revalidates_before_save(tmp_path):
    answers = [
        "Ada",
        "Lovelace",
        "01/01/1990",
        "Female",
        "4155550100",
        "1 Main St",
        "Oakland",
        "CA",
        "94607",
    ]
    with make_client(tmp_path) as client:
        login(client)
        csrf = client.cookies["dashboard_csrf"]
        headers = {"X-CSRF-Token": csrf}
        call_id = client.post("/dashboard/simulation/calls", headers=headers).json()[
            "call_id"
        ]
        for answer in answers:
            client.post(
                f"/dashboard/simulation/calls/{call_id}/turn",
                json={"text": answer},
                headers=headers,
            )
        correction = client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "phone number: 555"},
            headers=headers,
        )
        assert "isn't valid" in correction.json()["assistant"]
        assert correction.json()["patient_id"] is None
        correction = client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "phone number: (415) 555-0199"},
            headers=headers,
        )
        assert "4155550199" in correction.json()["assistant"]
        saved = client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "yes"},
            headers=headers,
        )
        assert saved.json()["patient_id"]


def test_simulation_intake_state_survives_app_restart(tmp_path):
    answers = [
        "Ada",
        "Lovelace",
        "01/01/1990",
        "Female",
        "4155550100",
        "1 Main St",
        "Oakland",
        "CA",
        "94607",
    ]
    with make_client(tmp_path) as first_client:
        login(first_client)
        csrf = first_client.cookies["dashboard_csrf"]
        headers = {"X-CSRF-Token": csrf}
        call_id = first_client.post(
            "/dashboard/simulation/calls", headers=headers
        ).json()["call_id"]
        first_client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": answers[0]},
            headers=headers,
        )
        cookies = dict(first_client.cookies)

    with make_client(tmp_path) as restarted_client:
        restarted_client.cookies.update(cookies)
        csrf = restarted_client.cookies["dashboard_csrf"]
        headers = {"X-CSRF-Token": csrf}
        current = restarted_client.get("/dashboard/simulation/current")
        assert current.json()["call_id"] == call_id
        for answer in answers[1:]:
            response = restarted_client.post(
                f"/dashboard/simulation/calls/{call_id}/turn",
                json={"text": answer},
                headers=headers,
            )
        assert "confirm" in response.json()["assistant"].lower()
        saved = restarted_client.post(
            f"/dashboard/simulation/calls/{call_id}/turn",
            json={"text": "yes"},
            headers=headers,
        )
        assert saved.json()["patient_id"]
