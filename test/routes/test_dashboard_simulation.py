from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.services.call_logs import CallLogService
from test.routes.test_dashboard import login, make_client


def send_turn(client, call_id, text, sequence, headers):
    return client.post(
        f"/dashboard/simulation/calls/{call_id}/turn",
        json={"text": text, "sequence": sequence},
        headers=headers,
    )


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
        assert created.json()["sequence"] == 0
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
        response = send_turn(
            client, call_id, "A1", state["sequence"], {"X-CSRF-Token": csrf}
        )
        assert response.status_code == 200
        assert "letters" in response.json()["assistant"].lower()
        for answer in answers:
            response = send_turn(
                client,
                call_id,
                answer,
                response.json()["sequence"],
                {"X-CSRF-Token": csrf},
            )
        assert "confirm" in response.json()["assistant"].lower()
        assert response.json()["patient_id"] is None
        response = send_turn(
            client, call_id, "yes", response.json()["sequence"], {"X-CSRF-Token": csrf}
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
        repeated = send_turn(
            client,
            call_id,
            "yes",
            response.json()["sequence"] - 1,
            {"X-CSRF-Token": csrf},
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
        state = client.post("/dashboard/simulation/calls", headers=headers).json()
        call_id, sequence = state["call_id"], state["sequence"]
        for answer in answers:
            response = send_turn(client, call_id, answer, sequence, headers)
            sequence = response.json()["sequence"]
        correction = send_turn(client, call_id, "phone number: 555", sequence, headers)
        sequence = correction.json()["sequence"]
        assert "isn't valid" in correction.json()["assistant"]
        assert correction.json()["patient_id"] is None
        correction = send_turn(
            client, call_id, "phone number: (415) 555-0199", sequence, headers
        )
        sequence = correction.json()["sequence"]
        assert "4155550199" in correction.json()["assistant"]
        saved = send_turn(client, call_id, "yes", sequence, headers)
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
        state = first_client.post("/dashboard/simulation/calls", headers=headers).json()
        call_id = state["call_id"]
        response = send_turn(
            first_client, call_id, answers[0], state["sequence"], headers
        )
        cookies = dict(first_client.cookies)

    with make_client(tmp_path) as restarted_client:
        restarted_client.cookies.update(cookies)
        csrf = restarted_client.cookies["dashboard_csrf"]
        headers = {"X-CSRF-Token": csrf}
        current = restarted_client.get("/dashboard/simulation/current")
        assert current.json()["call_id"] == call_id
        sequence = current.json()["sequence"]
        for answer in answers[1:]:
            response = send_turn(restarted_client, call_id, answer, sequence, headers)
            sequence = response.json()["sequence"]
        assert "confirm" in response.json()["assistant"].lower()
        saved = send_turn(restarted_client, call_id, "yes", sequence, headers)
        assert saved.json()["patient_id"]


def test_simulation_retry_and_stale_tab_return_current_turn_without_appending(tmp_path):
    with make_client(tmp_path) as client:
        login(client)
        headers = {"X-CSRF-Token": client.cookies["dashboard_csrf"]}
        state = client.post("/dashboard/simulation/calls", headers=headers).json()
        call_id = state["call_id"]
        first = send_turn(client, call_id, "Ada", 0, headers).json()
        retry = send_turn(client, call_id, "different stale text", 0, headers).json()
        assert retry["assistant"] == first["assistant"]
        assert retry["sequence"] == first["sequence"]
        stale = send_turn(client, call_id, "ignored", 0, headers).json()
        assert stale["assistant"] == first["assistant"]
        assert stale["sequence"] == first["sequence"]
        with Session(client.app.state.engine) as session:
            call = CallLogService(session).get(call_id)
            assert sum(message.get("role") == "user" for message in call.messages) == 1


def test_simulation_concurrent_same_sequence_claims_only_one_turn(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from app.services.simulation import SimulationService

    with make_client(tmp_path) as client:
        login(client)
        headers = {"X-CSRF-Token": client.cookies["dashboard_csrf"]}
        state = client.post("/dashboard/simulation/calls", headers=headers).json()
        user_id = UUID(state["call_id"].split(":")[1])
        service = SimulationService(client.app.state.engine, user_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda text: service.turn(state["call_id"], text, 0),
                    ("Ada", "Grace"),
                )
            )
        assert results[0]["assistant"] == results[1]["assistant"]
        assert results[0]["sequence"] == results[1]["sequence"]
        assert results[0]["sequence"] == 1
        with Session(client.app.state.engine) as session:
            call = CallLogService(session).get(state["call_id"])
            assert sum(message.get("role") == "user" for message in call.messages) == 1


def test_simulation_confirmation_rolls_back_patient_when_call_completion_fails(
    tmp_path, monkeypatch
):
    from app.services.call_logs import CallLogService

    original = CallLogService.log_simulation

    def fail_completion(self, *args, **kwargs):
        if kwargs.get("status") == "ended":
            raise RuntimeError("call completion failed")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CallLogService, "log_simulation", fail_completion)
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
        headers = {"X-CSRF-Token": client.cookies["dashboard_csrf"]}
        state = client.post("/dashboard/simulation/calls", headers=headers).json()
        sequence, call_id = state["sequence"], state["call_id"]
        for answer in answers:
            result = send_turn(client, call_id, answer, sequence, headers)
            sequence = result.json()["sequence"]
        with pytest.raises(RuntimeError, match="call completion failed"):
            send_turn(client, call_id, "yes", sequence, headers)
        with Session(client.app.state.engine) as session:
            from sqlalchemy import select

            from app.models.patient import Patient

            assert session.scalar(select(Patient)) is None
            call = CallLogService(session).get(call_id)
            assert call.status == "in_progress"
