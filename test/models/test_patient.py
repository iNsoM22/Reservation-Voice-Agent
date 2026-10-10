from datetime import UTC, date, timedelta
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.patient import Base, Patient


def test_patient_persists_uuid_dates_and_utc_timestamps(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'patients.db'}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        patient = Patient(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 4, 12),
            sex="Female",
            phone_number="4155550100",
            address_line_1="1 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94105",
        )
        session.add(patient)
        session.commit()
        identifier = patient.patient_id
        assert isinstance(identifier, UUID)
        assert patient.created_at.tzinfo == UTC
        assert patient.updated_at.tzinfo == UTC

    with Session(engine) as session:
        saved = session.scalar(select(Patient).where(Patient.patient_id == identifier))
        assert saved is not None
        assert saved.date_of_birth == date(1990, 4, 12)
        assert saved.deleted_at is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_name", ""),
        ("phone_number", "123"),
        ("phone_number", "41555A0100"),
        ("state", "ZZ"),
        ("zip_code", "ABCDE"),
        ("zip_code", "941051234"),
        ("address_line_1", ""),
        ("date_of_birth", date.today() + timedelta(days=1)),
    ],
)
def test_database_rejects_invalid_core_fields(tmp_path, field, value):
    engine = create_engine(f"sqlite:///{tmp_path / 'patients.db'}")
    Base.metadata.create_all(engine)
    details = {
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": date(1990, 4, 12),
        "sex": "Female",
        "phone_number": "4155550100",
        "address_line_1": "1 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94105",
    }
    details[field] = value

    with Session(engine) as session, pytest.raises(IntegrityError):
        session.add(Patient(**details))
        session.commit()
