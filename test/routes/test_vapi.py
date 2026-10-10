from test.routes.test_patients import make_client


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
                    "error": "Phone registration is not configured yet.",
                },
                {
                    "toolCallId": "call-2",
                    "error": "Phone registration is not configured yet.",
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
                    "error": "Phone registration is not configured yet.",
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
