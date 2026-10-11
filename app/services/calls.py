"""Validate confirmed Vapi tool calls and persist each call once."""

import logging
import re
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.call_log import CallLog
from app.services.patients import PatientService
from app.validations.patient import PatientCreate

logger = logging.getLogger(__name__)
CONFIRMATIONS = {
    "yes",
    "yes that's correct",
    "yes that is correct",
    "correct",
    "that's correct",
    "that is correct",
    "i confirm",
    "confirmed",
}


class CallService:
    def __init__(self, session: Session):
        self.session = session

    def lookup_patient(
        self,
        caller_number: str | None,
        arguments: dict[str, Any],
        *,
        call_type: str | None,
    ) -> dict[str, str]:
        if call_type != "inboundPhoneCall":
            return {
                "error": "Existing-record lookup is only available on inbound phone calls."
            }
        phone = _caller_phone(caller_number)
        if phone is None:
            return {
                "error": "I cannot verify the caller's phone number. Please use the patient API or contact the office."
            }
        if set(arguments) != {"last_name", "date_of_birth"}:
            return {
                "error": "Please provide the patient's last name and date of birth."
            }
        last_name = arguments["last_name"]
        dob_text = arguments["date_of_birth"]
        if not isinstance(last_name, str) or not isinstance(dob_text, str):
            return {"error": "Please provide a valid last name and date of birth."}
        try:
            dob = datetime.strptime(dob_text, "%m/%d/%Y").date()
            if dob.strftime("%m/%d/%Y") != dob_text:
                raise ValueError
        except ValueError:
            return {"error": "Please use MM/DD/YYYY for date of birth."}
        try:
            matches = [
                patient
                for patient in PatientService(self.session).list(
                    phone_number=phone, date_of_birth=dob
                )
                if patient.last_name.casefold() == last_name.strip().casefold()
            ]
        except SQLAlchemyError as exc:
            logger.error("Voice lookup database failure: %s", type(exc).__name__)
            return {
                "error": "I couldn't check the record right now. Please try again later."
            }
        if len(matches) != 1:
            return {
                "result": "No single matching record could be verified for this calling number."
            }
        patient = matches[0]
        return {
            "result": f"Verified existing record for {patient.first_name} {patient.last_name}. Patient ID: {patient.patient_id}."
        }

    def register_patient(
        self,
        call_id: str | None,
        arguments: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> dict[str, str]:
        if not call_id:
            return {"error": "Call ID is missing. Please try again."}
        try:
            data = PatientCreate.model_validate(arguments)
        except ValidationError as exc:
            fields = ", ".join(
                dict.fromkeys(str(error["loc"][0]) for error in exc.errors())
            )
            return {"error": f"Please correct these fields: {fields}."}
        if not _confirmed(messages, data):
            return {
                "error": "Please read back the details and get the caller's clear confirmation before saving."
            }
        try:
            existing = self.session.scalar(
                select(CallLog).where(CallLog.call_id == call_id).with_for_update()
            )
            if existing and existing.patient_id:
                patient = PatientService(self.session).get(existing.patient_id)
                if (
                    patient
                    and PatientCreate.model_validate(
                        patient, from_attributes=True
                    ).model_dump()
                    == data.model_dump()
                ):
                    return {
                        "result": f"Registration complete for {patient.first_name}. Patient ID: {patient.patient_id}."
                    }
                return {
                    "error": "This call already registered a different patient. Please start a new call."
                }
            if existing is None:
                existing = CallLog(call_id=call_id, source="vapi", status="in-progress")
                self.session.add(existing)
            patient = PatientService(self.session).create(data, commit=False)
            existing.patient_id = patient.patient_id
            if not existing.messages:
                existing.messages = messages
            if not existing.transcript:
                existing.transcript = "\n".join(
                    f"{item['role']}: {item.get('message', '')}"
                    for item in messages
                    if item.get("role") in {"user", "assistant"}
                )
            self.session.commit()
            logger.info(
                "Voice registration saved: call_id=%s patient_id=%s",
                call_id,
                patient.patient_id,
            )
            return {
                "result": f"Registration complete for {patient.first_name}. Patient ID: {patient.patient_id}."
            }
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("Voice registration database failure: %s", type(exc).__name__)
            return {
                "error": "I couldn't save the registration right now. Please try again later."
            }


def _confirmed(messages: list[dict[str, Any]], data: PatientCreate) -> bool:
    conversation = [
        item
        for item in messages
        if item.get("role") in {"user", "assistant"}
        and isinstance(item.get("message"), str)
    ]
    if (
        len(conversation) < 2
        or conversation[-1]["role"] != "user"
        or conversation[-2]["role"] != "assistant"
    ):
        return False
    reply = re.sub(r"[^a-z\s']", "", conversation[-1]["message"].casefold()).strip()
    readback = conversation[-2]["message"].casefold()
    values = data.model_dump(mode="json", exclude_unset=True)
    values["date_of_birth"] = data.date_of_birth.strftime("%m/%d/%Y")
    return (
        reply in CONFIRMATIONS
        and any(
            phrase in readback
            for phrase in (
                "is all of that correct",
                "is that correct",
                "do you confirm",
            )
        )
        and all(
            re.search(rf"(?<!\w){re.escape(str(value).casefold())}(?!\w)", readback)
            for value in values.values()
            if value is not None
        )
    )


def _caller_phone(number: str | None) -> str | None:
    if not number or not re.fullmatch(r"\+1[0-9]{10}", number):
        return None
    return number[2:]
