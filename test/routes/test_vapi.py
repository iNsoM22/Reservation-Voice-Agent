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
