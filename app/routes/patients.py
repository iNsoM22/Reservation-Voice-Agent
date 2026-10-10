"""Patient REST API."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.routes.dependencies import patient_service, require_api_key
from app.routes.errors import APIError
from app.services.patients import PatientService
from app.validations.patient import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", dependencies=[Depends(require_api_key)])


def payload(patient: object) -> dict[str, object]:
    return {"data": PatientResponse.model_validate(patient), "error": None}


@router.get("")
def list_patients(
    service: Annotated[PatientService, Depends(patient_service)],
    last_name: str | None = None,
    date_of_birth: str | None = None,
    phone_number: str | None = None,
) -> dict[str, object]:
    dob = None
    if date_of_birth is not None:
        try:
            dob = datetime.strptime(date_of_birth, "%m/%d/%Y").date()
            if dob.strftime("%m/%d/%Y") != date_of_birth:
                raise ValueError
        except ValueError as exc:
            raise APIError(
                400, "invalid_filter", "Use MM/DD/YYYY for date_of_birth"
            ) from exc
    if phone_number is not None and (
        len(phone_number) != 10
        or not phone_number.isascii()
        or not phone_number.isdigit()
    ):
        raise APIError(400, "invalid_filter", "Use a 10-digit phone_number")
    patients = service.list(
        last_name=last_name, date_of_birth=dob, phone_number=phone_number
    )
    return {
        "data": [PatientResponse.model_validate(patient) for patient in patients],
        "error": None,
    }


@router.get("/{patient_id}")
def get_patient(
    patient_id: UUID, service: Annotated[PatientService, Depends(patient_service)]
) -> dict[str, object]:
    patient = service.get(patient_id)
    if patient is None:
        raise APIError(404, "not_found", "Patient not found")
    return payload(patient)


@router.post("", status_code=201)
def create_patient(
    data: PatientCreate, service: Annotated[PatientService, Depends(patient_service)]
) -> dict[str, object]:
    return payload(service.create(data))


@router.put("/{patient_id}")
def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    service: Annotated[PatientService, Depends(patient_service)],
) -> dict[str, object]:
    if not data.model_fields_set:
        raise APIError(400, "empty_update", "Provide at least one field to update")
    patient = service.update(patient_id, data)
    if patient is None:
        raise APIError(404, "not_found", "Patient not found")
    return payload(patient)


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: UUID, service: Annotated[PatientService, Depends(patient_service)]
) -> dict[str, object]:
    patient = service.delete(patient_id)
    if patient is None:
        raise APIError(404, "not_found", "Patient not found")
    return payload(patient)
