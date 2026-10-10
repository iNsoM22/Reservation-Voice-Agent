"""Patient business operations shared by the REST and future voice paths."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient, utc_now
from app.validations.patient import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: PatientCreate) -> Patient:
        patient = Patient(**data.model_dump())
        self.session.add(patient)
        self._commit(patient)
        return patient

    def get(self, patient_id: UUID) -> Patient | None:
        return self.session.scalar(
            select(Patient).where(
                Patient.patient_id == patient_id, Patient.deleted_at.is_(None)
            )
        )

    def list(
        self,
        *,
        last_name: str | None = None,
        date_of_birth: date | None = None,
        phone_number: str | None = None,
    ) -> list[Patient]:
        query = select(Patient).where(Patient.deleted_at.is_(None))
        if last_name is not None:
            query = query.where(Patient.last_name == last_name)
        if date_of_birth is not None:
            query = query.where(Patient.date_of_birth == date_of_birth)
        if phone_number is not None:
            query = query.where(Patient.phone_number == phone_number)
        return list(
            self.session.scalars(query.order_by(Patient.created_at, Patient.patient_id))
        )

    def update(self, patient_id: UUID, data: PatientUpdate) -> Patient | None:
        patient = self.get(patient_id)
        if patient is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        patient.updated_at = max(
            utc_now(), patient.updated_at + timedelta(microseconds=1)
        )
        self._commit(patient)
        return patient

    def delete(self, patient_id: UUID) -> Patient | None:
        patient = self.get(patient_id)
        if patient is None:
            return None
        patient.updated_at = max(
            utc_now(), patient.updated_at + timedelta(microseconds=1)
        )
        patient.deleted_at = patient.updated_at
        self._commit(patient)
        return patient

    def _commit(self, patient: Patient) -> None:
        try:
            self.session.commit()
            self.session.refresh(patient)
        except Exception:
            self.session.rollback()
            raise
