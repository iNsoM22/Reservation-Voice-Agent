from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.call_log import CallLog
from test.routes.test_patients import make_client

PATIENT = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "01/02/1990",
    "sex": "Female",
    "phone_number": "4155550100",
    "address_line_1": "1 Main St",
    "city": "Oakland",
    "state": "CA",
    "zip_code": "94607",
}


def registration_event(*, confirmed=True, patient=None, call_id="vapi-register-1"):
    messages = [
        {
            "role": "assistant",
            "message": "I have Jane Doe, born 01/02/1990, Female, phone 4155550100, at 1 Main St, Oakland CA 94607. Is all of that correct?",
        },
        {
            "role": "user",
            "message": "Yes, that is correct." if confirmed else "No, change my name.",
        },
    ]
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": call_id},
            "artifact": {"messages": messages},
            "toolCallList": [
                {
                    "id": "tool-1",
                    "function": {
                        "name": "register_patient",
                        "arguments": patient or PATIENT,
                    },
                }
            ],
        }
    }


def lookup_event(number, *, last_name="Doe", date_of_birth="01/02/1990"):
    return {
        "message": {
            "type": "tool-calls",
            "call": {
                "id": "lookup-call",
                "type": "inboundPhoneCall",
                "customer": {"number": number},
            },
            "toolCallList": [
                {
                    "id": "lookup-tool",
                    "function": {
                        "name": "lookup_patient",
                        "arguments": {
                            "last_name": last_name,
                            "date_of_birth": date_of_birth,
                        },
                    },
                }
            ],
        }
    }


def test_browser_voice_registration_uses_vapi_webhook_and_call_log(tmp_path):
    with make_client(tmp_path) as client:
        event = registration_event(call_id="web-voice-1")
        event["message"]["call"]["type"] = "webCall"
        result = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert result.status_code == 200
        assert "Registration complete" in result.json()["results"][0]["result"]
        with Session(client.app.state.engine) as session:
            log = session.query(CallLog).filter_by(call_id="web-voice-1").one()
            assert log.patient_id is not None
            assert log.source == "vapi"


def test_lookup_uses_verified_call_number_and_never_crosses_to_another_patient(
    tmp_path,
):
    with make_client(tmp_path) as client:
        headers = {"X-API-Key": "test-api-key"}
        client.post("/patients", json=PATIENT, headers=headers)
        client.post(
            "/patients",
            json={**PATIENT, "first_name": "Mary", "phone_number": "2125550100"},
            headers=headers,
        )
        auth = {"Authorization": "Bearer test-vapi-token"}
        own = client.post(
            "/calls/vapi", json=lookup_event("+14155550100"), headers=auth
        )
        assert own.status_code == 200
        assert "Jane" in own.json()["results"][0]["result"]
        other = client.post(
            "/calls/vapi", json=lookup_event("+12125550100"), headers=auth
        )
        assert "Jane" not in str(other.json())
        assert "Mary" in other.json()["results"][0]["result"]
        missing_number = client.post(
            "/calls/vapi", json=lookup_event(None), headers=auth
        )
        assert "error" in missing_number.json()["results"][0]
        wrong_dob = client.post(
            "/calls/vapi",
            json=lookup_event("+14155550100", date_of_birth="02/01/1990"),
            headers=auth,
        )
        assert "Jane" not in str(wrong_dob.json())
        forged = lookup_event("+12125550100")
        forged["message"]["toolCallList"][0]["function"]["arguments"][
            "phone_number"
        ] = "4155550100"
        response = client.post("/calls/vapi", json=forged, headers=auth)
        assert "error" in response.json()["results"][0]
        assert "Jane" not in str(response.json())


def test_lookup_rejects_non_inbound_call_even_with_matching_number(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/patients", json=PATIENT, headers={"X-API-Key": "test-api-key"})
        event = lookup_event("+14155550100")
        event["message"]["call"]["type"] = "webCall"
        response = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert "error" in response.json()["results"][0]
        assert "Jane" not in str(response.json())


def test_confirmed_call_saves_once_and_report_keeps_patient_link(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"Authorization": "Bearer test-vapi-token"}
        event = registration_event()
        first = client.post("/calls/vapi", json=event, headers=headers)
        second = client.post("/calls/vapi", json=event, headers=headers)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert "result" in first.json()["results"][0]
        patients = client.get(
            "/patients", headers={"X-API-Key": "test-api-key"}
        ).json()["data"]
        assert len(patients) == 1
        report = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "vapi-register-1"},
                "artifact": {},
            }
        }
        assert (
            client.post("/calls/vapi", json=report, headers=headers).status_code == 200
        )
        with Session(client.app.state.engine) as session:
            call = session.query(CallLog).one()
            assert str(call.patient_id) == patients[0]["patient_id"]
            assert "Jane Doe" in call.transcript
            assert len(call.messages) == 2


def test_late_registration_link_keeps_existing_full_call_report(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"Authorization": "Bearer test-vapi-token"}
        report = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "vapi-register-1"},
                "artifact": {
                    "transcript": "Full final conversation",
                    "messages": [
                        {"role": "assistant", "message": "Full final conversation"}
                    ],
                },
            }
        }
        assert (
            client.post("/calls/vapi", json=report, headers=headers).status_code == 200
        )
        assert (
            "result"
            in client.post(
                "/calls/vapi", json=registration_event(), headers=headers
            ).json()["results"][0]
        )
        with Session(client.app.state.engine) as session:
            call = session.query(CallLog).one()
            assert call.transcript == "Full final conversation"
            assert call.messages == [
                {"role": "assistant", "message": "Full final conversation"}
            ]
            assert call.patient_id is not None


def test_voice_registration_survives_app_restart(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=registration_event(),
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert "result" in response.json()["results"][0]
    with make_client(tmp_path) as restarted:
        patients = restarted.get(
            "/patients", headers={"X-API-Key": "test-api-key"}
        ).json()["data"]
        assert len(patients) == 1
        assert patients[0]["first_name"] == "Jane"


def test_unconfirmed_or_invalid_call_does_not_save(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"Authorization": "Bearer test-vapi-token"}
        for event in (
            registration_event(confirmed=False),
            registration_event(patient={**PATIENT, "phone_number": "123"}),
            registration_event(patient={**PATIENT, "last_name": "Smith"}),
        ):
            response = client.post("/calls/vapi", json=event, headers=headers)
            assert "error" in response.json()["results"][0]
        assert (
            client.get("/patients", headers={"X-API-Key": "test-api-key"}).json()[
                "data"
            ]
            == []
        )


def test_readback_does_not_accept_fields_hidden_inside_other_words(tmp_path):
    event = registration_event(patient={**PATIENT, "first_name": "Al", "state": "LA"})
    readback = event["message"]["artifact"]["messages"][0]
    readback["message"] = readback["message"].replace("Jane", "").replace(" CA ", " ")
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert "error" in response.json()["results"][0]


def test_readback_does_not_accept_male_when_female_was_spoken(tmp_path):
    event = registration_event(patient={**PATIENT, "sex": "Male"})
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert "error" in response.json()["results"][0]


def test_second_registration_on_same_call_cannot_create_another_patient(tmp_path):
    with make_client(tmp_path) as client:
        headers = {"Authorization": "Bearer test-vapi-token"}
        assert (
            "result"
            in client.post(
                "/calls/vapi", json=registration_event(), headers=headers
            ).json()["results"][0]
        )
        changed = registration_event(patient={**PATIENT, "last_name": "Smith"})
        changed["message"]["artifact"]["messages"][-2]["message"] = changed["message"][
            "artifact"
        ]["messages"][-2]["message"].replace("Doe", "Smith")
        assert (
            "error"
            in client.post("/calls/vapi", json=changed, headers=headers).json()[
                "results"
            ][0]
        )
        assert (
            len(
                client.get("/patients", headers={"X-API-Key": "test-api-key"}).json()[
                    "data"
                ]
            )
            == 1
        )


def test_database_failure_returns_speakable_tool_error_without_write(
    tmp_path, monkeypatch
):
    from app.services.patients import PatientService

    def fail_create(self, data, *, commit=True):
        raise OperationalError("insert", {}, RuntimeError("database offline"))

    monkeypatch.setattr(PatientService, "create", fail_create)
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=registration_event(),
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 200
        assert "try again later" in response.json()["results"][0]["error"]
        assert (
            client.get("/patients", headers={"X-API-Key": "test-api-key"}).json()[
                "data"
            ]
            == []
        )


def test_lookup_database_failure_returns_tool_error(tmp_path, monkeypatch):
    from app.services.patients import PatientService

    def fail_list(self, **filters):
        raise OperationalError("select", {}, RuntimeError("database offline"))

    monkeypatch.setattr(PatientService, "list", fail_list)
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=lookup_event("+14155550100"),
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 200
        assert "error" in response.json()["results"][0]


def test_call_webhook_requires_token_and_returns_tool_errors_without_writes(tmp_path):
    body = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "register_patient", "arguments": {}},
                },
                {
                    "id": "call-2",
                    "type": "function",
                    "function": {"name": "register_patient", "arguments": {}},
                },
            ],
        }
    }
    with make_client(tmp_path) as client:
        assert client.post("/calls/vapi", json=body).status_code == 401
        response = client.post(
            "/calls/vapi",
            json=body,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "results": [
                {
                    "toolCallId": "call-1",
                    "error": "Call ID is missing. Please try again.",
                },
                {
                    "toolCallId": "call-2",
                    "error": "Call ID is missing. Please try again.",
                },
            ]
        }
        assert (
            client.get("/patients", headers={"X-API-Key": "test-api-key"}).json()[
                "data"
            ]
            == []
        )


def test_call_webhook_acknowledges_informational_event(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json={"message": {"type": "status-update", "status": "ended"}},
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 200
        assert response.json() == {}


def test_call_webhook_rejects_unknown_tool_without_registration(tmp_path):
    event = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call-unknown",
                    "type": "function",
                    "function": {"name": "delete_patient", "arguments": {}},
                }
            ],
        }
    }
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "results": [
                {
                    "toolCallId": "call-unknown",
                    "error": "Unsupported tool: delete_patient",
                }
            ]
        }


def test_call_webhook_accepts_simplified_vapi_tool_shape(tmp_path):
    event = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {"id": "call-simple", "name": "register_patient", "parameters": {}}
            ],
        }
    }
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "results": [
                {
                    "toolCallId": "call-simple",
                    "error": "Call ID is missing. Please try again.",
                }
            ]
        }


def test_call_webhook_authenticates_before_parsing_malformed_json(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            content="{",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_authenticated_end_of_call_report_is_saved_idempotently(tmp_path):
    event = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "id": "vapi-report-1",
                "startedAt": "2026-10-11T10:00:00Z",
                "endedAt": "2026-10-11T10:01:00Z",
                "customer": {"number": "+14155550100"},
            },
            "endedReason": "customer-ended-call",
            "artifact": {
                "transcript": "Assistant: Hello\nUser: My name is Jane.",
                "messages": [{"role": "assistant", "message": "Hello"}],
            },
        }
    }
    with make_client(tmp_path) as client:
        headers = {"Authorization": "Bearer test-vapi-token"}
        assert client.post("/calls/vapi", json=event).status_code == 401
        assert client.post("/calls/vapi", json=event, headers=headers).json() == {}
        assert client.post("/calls/vapi", json=event, headers=headers).json() == {}
        # Access the durable rows through the logged in dashboard below once registered.
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from app.models.call_log import CallLog

        with Session(client.app.state.engine) as session:
            rows = list(session.scalars(select(CallLog)))
        assert len(rows) == 1
        assert rows[0].transcript.endswith("My name is Jane.")
        assert rows[0].messages[0]["message"] == "Hello"
        assert rows[0].patient_id is None


def test_end_of_call_report_rejects_oversized_transcript(tmp_path):
    event = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "vapi-large"},
            "artifact": {"transcript": "x" * 200_001},
        }
    }
    with make_client(tmp_path) as client:
        response = client.post(
            "/calls/vapi",
            json=event,
            headers={"Authorization": "Bearer test-vapi-token"},
        )
        assert response.status_code == 422
