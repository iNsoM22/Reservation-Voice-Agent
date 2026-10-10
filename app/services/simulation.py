"""Persistent patient intake simulation workflow."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy import text as sql_text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.call_log import CallLog
from app.services.call_logs import CallLogService
from app.services.patients import PatientService
from app.validations.patient import PatientCreate

FIELDS = (
    ("first_name", "first name"),
    ("last_name", "last name"),
    ("date_of_birth", "date of birth (MM/DD/YYYY)"),
    ("sex", "sex (Male, Female, Other, or Decline to Answer)"),
    ("phone_number", "10-digit U.S. phone number"),
    ("address_line_1", "street address"),
    ("city", "city"),
    ("state", "two-letter state abbreviation"),
    ("zip_code", "ZIP code"),
)
FIELD_LABELS = dict(FIELDS)


class SimulationNotFound(LookupError):
    """Raised when a call is missing or belongs to another administrator."""


class SimulationService:
    def __init__(self, engine: Engine, user_id: UUID):
        self.engine = engine
        self.user_id = user_id

    def start(self) -> dict[str, Any]:
        call_id = f"sim:{self.user_id}:{uuid4()}"
        now = datetime.now(UTC)
        state = {
            "owner": str(self.user_id),
            "values": {},
            "stage": "intake",
            "sequence": 0,
        }
        messages = [
            {"role": "system", "state": state},
            {"role": "assistant", "message": _prompt(0)},
        ]
        with Session(self.engine) as session:
            CallLogService(session).log_simulation(
                call_id,
                _transcript(messages),
                messages,
                status="in_progress",
                started_at=now,
            )
        return {
            "call_id": call_id,
            "assistant": messages[-1]["message"],
            "patient_id": None,
            "sequence": 0,
        }

    def current(self) -> dict[str, Any]:
        with Session(self.engine) as session:
            call = session.scalar(
                select(CallLog)
                .where(
                    CallLog.call_id.like(f"sim:{self.user_id}:%"),
                    CallLog.source == "simulation",
                    CallLog.status == "in_progress",
                )
                .order_by(CallLog.started_at.desc())
            )
            if call is None:
                return {"call_id": None}
            return {
                "call_id": call.call_id,
                "messages": [
                    item
                    for item in call.messages
                    if item.get("role") in {"user", "assistant"}
                ],
                "sequence": call.messages[0]["state"].get("sequence", 0),
            }

    def turn(self, call_id: str, text: str, sequence: int) -> dict[str, Any]:
        with Session(self.engine) as session:
            if self.engine.dialect.name == "sqlite":
                session.execute(sql_text("BEGIN IMMEDIATE"))
            logs = CallLogService(session)
            call = logs.get(call_id)
            if call is None or not call_id.startswith(f"sim:{self.user_id}:"):
                raise SimulationNotFound
            messages = list(call.messages)
            state = dict(messages[0]["state"])
            if state.get("owner") != str(self.user_id):
                raise SimulationNotFound
            current_sequence = state.get("sequence", 0)
            if state["stage"] == "complete":
                return _turn_result(call, current_sequence)
            if sequence != current_sequence:
                return _turn_result(call, current_sequence)
            utterance = text.strip()
            messages.append({"role": "user", "message": utterance})
            state["sequence"] = current_sequence + 1
            messages[0]["state"] = state
            claim = session.execute(
                update(CallLog)
                .where(
                    CallLog.call_id == call_id,
                    CallLog.status == "in_progress",
                    CallLog.transcript == call.transcript,
                )
                .values(transcript=_transcript(messages))
            )
            if claim.rowcount != 1:
                session.rollback()
                latest = logs.get(call_id)
                if latest is None:
                    raise SimulationNotFound
                return _turn_result(
                    latest, latest.messages[0]["state"].get("sequence", 0)
                )
            if state["stage"] == "confirm":
                return self._confirmation(
                    utterance, call_id, call.started_at, state, messages, logs, session
                )
            return self._intake(
                utterance, call_id, call.started_at, state, messages, logs
            )

    def _confirmation(
        self, utterance, call_id, started_at, state, messages, logs, session
    ):
        try:
            answer, patient_id = _confirm(utterance, state, session)
        except Exception:
            session.rollback()
            raise
        messages.append({"role": "assistant", "message": answer})
        messages[0]["state"] = state
        logs.log_simulation(
            call_id,
            _transcript(messages),
            messages,
            patient_id=patient_id,
            status="ended" if patient_id else "in_progress",
            started_at=started_at,
            ended_at=datetime.now(UTC) if patient_id else None,
        )
        return {
            "assistant": answer,
            "patient_id": str(patient_id) if patient_id else None,
            "sequence": state["sequence"],
        }

    def _intake(self, utterance, call_id, started_at, state, messages, logs):
        index = len(state["values"])
        field = FIELDS[index][0]
        try:
            validated = _validate_field(field, utterance, state["values"])
        except ValidationError as exc:
            answer = f"That {FIELD_LABELS[field]} isn't valid. {exc.errors()[0]['msg']}. Please try again."
        except ValueError as exc:
            answer = f"That {FIELD_LABELS[field]} isn't valid. {exc}. Please try again."
        else:
            state["values"][field] = validated
            if len(state["values"]) == len(FIELDS):
                state["stage"] = "confirm"
                answer = _readback(state["values"])
            else:
                answer = _prompt(len(state["values"]))
        messages[0]["state"] = state
        messages.append({"role": "assistant", "message": answer})
        logs.log_simulation(
            call_id,
            _transcript(messages),
            messages,
            status="in_progress",
            started_at=started_at,
        )
        return {
            "assistant": answer,
            "patient_id": None,
            "sequence": state["sequence"],
        }


def _prompt(index: int) -> str:
    return f"What is your {FIELDS[index][1]}?"


def _readback(values: dict[str, Any]) -> str:
    details = "; ".join(f"{label}: {values[key]}" for key, label in FIELDS)
    return f"Please review your details: {details}. Say yes to confirm, or correct a field using ‘field: value’."


def _validate_field(field: str, value: str, existing: dict[str, Any]) -> Any:
    candidate = {
        "first_name": "Sample",
        "last_name": "Patient",
        "date_of_birth": "01/01/1990",
        "sex": "Other",
        "phone_number": "4155550100",
        "address_line_1": "1 Main St",
        "city": "Oakland",
        "state": "CA",
        "zip_code": "94607",
    }
    candidate.update(existing)
    candidate[field] = _normalize_spoken(field, value)
    validated = getattr(PatientCreate.model_validate(candidate), field)
    return (
        validated.strftime("%m/%d/%Y") if field == "date_of_birth" else str(validated)
    )


def _normalize_spoken(field: str, value: str) -> str:
    if field == "sex":
        choices = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
            "decline": "Decline to Answer",
            "decline to answer": "Decline to Answer",
        }
        return choices.get(value.strip().casefold(), value)
    if field == "date_of_birth":
        for pattern in ("%B %d %Y", "%B %d, %Y", "%b %d %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(value.strip(), pattern).strftime("%m/%d/%Y")
            except ValueError:
                pass
    return value


def _is_confirmation(text: str) -> bool:
    return text.casefold() in {
        "yes",
        "yes, confirm",
        "confirm",
        "correct",
        "that's correct",
        "that is correct",
    }


def _confirm(text: str, state: dict[str, Any], session: Session):
    if _is_confirmation(text):
        patient = PatientService(session).create(
            PatientCreate.model_validate(state["values"]), commit=False
        )
        state["stage"] = "complete"
        return f"You're all set, {patient.first_name}.", patient.patient_id
    if text.casefold() in {"no", "change", "correction"}:
        return (
            "Tell me the field and its new value, for example: phone number: 4155550100.",
            None,
        )
    if ":" in text:
        label, value = (part.strip() for part in text.split(":", 1))
        normalized = label.casefold().replace(" ", "_")
        aliases = {
            "dob": "date_of_birth",
            "phone": "phone_number",
            "phone_number": "phone_number",
        }
        field = aliases.get(normalized, normalized)
        if field not in FIELD_LABELS:
            field = next(
                (key for key, name in FIELDS if label.casefold() == name), None
            )
        if field:
            try:
                state["values"][field] = _validate_field(field, value, state["values"])
            except (ValidationError, ValueError):
                return (
                    f"That {FIELD_LABELS[field]} isn't valid. Please provide it again in the format requested.",
                    None,
                )
            return _readback(state["values"]), None
    return "Please say yes to confirm, or correct a field using ‘field: value’.", None


def _transcript(messages: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{'Caller' if item['role'] == 'user' else 'Assistant'}: {item['message']}"
        for item in messages
        if item.get("role") in {"user", "assistant"}
    )


def _turn_result(call: CallLog, sequence: int) -> dict[str, Any]:
    assistant = next(
        (
            item["message"]
            for item in reversed(call.messages)
            if item.get("role") == "assistant"
        ),
        "This registration is already complete.",
    )
    return {
        "assistant": assistant,
        "patient_id": str(call.patient_id) if call.patient_id else None,
        "sequence": sequence,
        "messages": [
            item for item in call.messages if item.get("role") in {"user", "assistant"}
        ],
    }
