"""Patient request and response contracts shared by REST and voice tools."""

import re
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class Sex(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE = "Decline to Answer"


STATES = frozenset(
    [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    ]
)


class PatientFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: str | None = Field(default=None, max_length=255)
    address_line_1: str = Field(min_length=1, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str
    zip_code: str
    insurance_provider: str | None = Field(default=None, max_length=255)
    insurance_member_id: str | None = Field(default=None, max_length=100)
    preferred_language: str = Field(default="English", min_length=1, max_length=100)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not all(part.isalpha() for part in re.split(r"[-']", value)):
            raise ValueError("Use letters, hyphens, or apostrophes")
        return value

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def parse_dob(cls, value: object) -> date | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            result = value
        elif isinstance(value, str):
            try:
                result = datetime.strptime(value, "%m/%d/%Y").date()
            except ValueError as exc:
                raise ValueError("Use a valid date in MM/DD/YYYY format") from exc
            if result.strftime("%m/%d/%Y") != value:
                raise ValueError("Use MM/DD/YYYY format")
        else:
            raise ValueError("Use MM/DD/YYYY format")  # noqa: TRY004 - Pydantic wraps ValueError
        if result > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return result

    @field_validator("phone_number", "emergency_contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"[\s().-]", "", value)
        if not re.fullmatch(r"[0-9]{10}", digits):
            raise ValueError("Use a 10-digit U.S. phone number")
        return digits

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.upper()
        if value not in STATES:
            raise ValueError("Use a valid two-letter U.S. state abbreviation")
        return value

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[0-9]{5}(?:-[0-9]{4})?", value):
            raise ValueError("Use a 5-digit ZIP or ZIP+4")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Use a valid email address")
        return value

    @field_validator("insurance_member_id")
    @classmethod
    def validate_member_id(cls, value: str | None) -> str | None:
        if value is not None and not value.isalnum():
            raise ValueError("Use an alphanumeric member ID")
        return value


class PatientCreate(PatientFields):
    pass


class PatientUpdate(PatientFields):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone_number: str | None = None
    address_line_1: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = None
    zip_code: str | None = None
    preferred_language: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator(
        "first_name",
        "last_name",
        "date_of_birth",
        "sex",
        "phone_number",
        "address_line_1",
        "city",
        "state",
        "zip_code",
        "preferred_language",
    )
    @classmethod
    def required_fields_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Required fields cannot be null")
        return value


class PatientResponse(PatientFields):
    model_config = ConfigDict(from_attributes=True)

    patient_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @field_serializer("date_of_birth", when_used="json")
    def serialize_dob(self, value: date) -> str:
        return value.strftime("%m/%d/%Y")


class PatientEnvelope(BaseModel):
    data: PatientResponse | None
    error: str | None = None
