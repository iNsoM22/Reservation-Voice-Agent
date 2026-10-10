from datetime import UTC

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.patient import Base
from app.validations.patient import PatientCreate, PatientUpdate


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'patients.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


@pytest.fixture
def intake():
    return PatientCreate.model_validate(
        {
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "04/12/1990",
            "sex": "Female",
            "phone_number": "415-555-0100",
            "address_line_1": "1 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94105",
        }
    )


def test_create_then_filter_patient_by_each_supported_field(session, intake):
    from app.services.patients import PatientService

    service = PatientService(session)
    saved = service.create(intake)

    assert service.get(saved.patient_id).first_name == "Jane"
    assert [p.patient_id for p in service.list(last_name="Doe")] == [saved.patient_id]
    assert [p.patient_id for p in service.list(date_of_birth=intake.date_of_birth)] == [
        saved.patient_id
    ]
    assert [p.patient_id for p in service.list(phone_number="4155550100")] == [
        saved.patient_id
    ]
    assert service.list(last_name="Other") == []


def test_partial_update_preserves_other_values_and_advances_timestamp(session, intake):
    from app.services.patients import PatientService

    service = PatientService(session)
    saved = service.create(intake)
    previous = saved.updated_at
    changed = service.update(
        saved.patient_id, PatientUpdate.model_validate({"last_name": "Smith"})
    )

    assert changed.last_name == "Smith"
    assert changed.first_name == "Jane"
    assert changed.updated_at > previous


def test_soft_delete_hides_patient_but_preserves_row(session, intake):
    from app.services.patients import PatientService

    service = PatientService(session)
    saved = service.create(intake)
    deleted = service.delete(saved.patient_id)

    assert deleted.deleted_at is not None
    assert deleted.deleted_at.tzinfo == UTC
    assert service.get(saved.patient_id) is None
    assert service.list() == []
    assert session.get(type(saved), saved.patient_id) is not None
    assert service.delete(saved.patient_id) is None


def test_update_missing_patient_returns_none(session):
    from uuid import uuid4

    from app.services.patients import PatientService

    assert (
        PatientService(session).update(
            uuid4(), PatientUpdate.model_validate({"city": "Boston"})
        )
        is None
    )
