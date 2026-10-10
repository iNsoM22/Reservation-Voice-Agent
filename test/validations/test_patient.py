from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.validations.patient import PatientCreate, PatientUpdate


@pytest.fixture
def valid_patient():
    return {
        "first_name": "Anne-Marie",
        "last_name": "O'Neil",
        "date_of_birth": "04/12/1990",
        "sex": "Female",
        "phone_number": "(415) 555-0100",
        "address_line_1": "1 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94105-1234",
    }


def test_create_normalizes_demographics_and_defaults_language(valid_patient):
    patient = PatientCreate.model_validate(valid_patient)

    assert patient.date_of_birth == date(1990, 4, 12)
    assert patient.phone_number == "4155550100"
    assert patient.preferred_language == "English"
    assert patient.first_name == "Anne-Marie"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_name", "John3"),
        ("last_name", "A" * 51),
        ("date_of_birth", "02/30/2000"),
        ("date_of_birth", (date.today() + timedelta(days=1)).strftime("%m/%d/%Y")),
        ("sex", "Unknown"),
        ("phone_number", "123"),
        ("address_line_1", ""),
        ("city", "X" * 101),
        ("state", "ZZ"),
        ("zip_code", "1234"),
        ("email", "not-an-email"),
        ("email", "a" * 250 + "@example.com"),
        ("phone_number", "٤١٥٥٥٥٠١٠٠"),
        ("zip_code", "٩٤١٠٥"),
        ("insurance_member_id", "ABC 123"),
        ("emergency_contact_phone", "123"),
    ],
)
def test_create_rejects_invalid_field(valid_patient, field, value):
    valid_patient[field] = value

    with pytest.raises(ValidationError) as error:
        PatientCreate.model_validate(valid_patient)

    assert any(item["loc"] == (field,) for item in error.value.errors())


def test_create_rejects_unknown_fields(valid_patient):
    valid_patient["deleted_at"] = "2000-01-01"

    with pytest.raises(ValidationError):
        PatientCreate.model_validate(valid_patient)


def test_partial_update_validates_only_supplied_fields():
    update = PatientUpdate.model_validate({"phone_number": "415-555-0100"})

    assert update.model_dump(exclude_unset=True) == {"phone_number": "4155550100"}


def test_partial_update_rejects_null_required_field():
    with pytest.raises(ValidationError):
        PatientUpdate.model_validate({"first_name": None})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_name", "A" * 51),
        ("last_name", "A" * 51),
        ("address_line_1", ""),
        ("city", "A" * 101),
        ("preferred_language", ""),
    ],
)
def test_partial_update_keeps_required_field_limits(field, value):
    with pytest.raises(ValidationError):
        PatientUpdate.model_validate({field: value})
