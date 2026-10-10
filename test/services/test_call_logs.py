from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.patient import Base
from app.services.call_logs import CallLogService


def test_simulation_log_upserts_conversation_by_call_id(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'calls.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = CallLogService(session)
        first = service.log_simulation(
            "sim-1",
            "Caller: My name is Jane.",
            [{"role": "user", "message": "My name is Jane."}],
        )
        second = service.log_simulation(
            "sim-1",
            "Caller: I am Jane Doe.",
            [{"role": "user", "message": "I am Jane Doe."}],
        )
        rows, total = service.list_page(1, 20)
        assert first.call_log_id == second.call_log_id
        assert (total, len(rows)) == (1, 1)
        assert rows[0].source == "simulation"
        assert rows[0].transcript == "Caller: I am Jane Doe."
        assert rows[0].messages == [{"role": "user", "message": "I am Jane Doe."}]
        assert service.get("sim-1").call_id == "sim-1"


def test_call_report_upsert_preserves_vapi_conversation(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'calls.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = CallLogService(session)
        report = {
            "call": {"id": "vapi-1", "startedAt": "2026-10-11T10:00:00Z"},
            "endedReason": "customer-ended-call",
            "artifact": {
                "transcript": "Assistant: Hello\nUser: My name is Jane.",
                "messages": [{"role": "assistant", "message": "Hello"}],
            },
        }
        log = service.record_vapi_report(report)
        assert log.source == "vapi"
        assert log.transcript.endswith("My name is Jane.")
        assert log.messages[0]["message"] == "Hello"
        assert log.patient_id is None
        assert service.record_vapi_report(report).call_log_id == log.call_log_id
        assert service.list_page(1, 20)[1] == 1
