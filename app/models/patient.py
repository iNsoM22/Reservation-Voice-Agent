"""Persistent patient table. Request validation lives in app.validations."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    String,
    Uuid,
    and_,
    column,
    func,
    or_,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.validations.patient import STATES


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Timestamp must include a timezone")
        return value

    def process_result_value(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    pass


def non_digit_count(value: object) -> object:
    for digit in "0123456789":
        value = func.replace(value, digit, "")
    return func.length(value)


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(
            "length(first_name) between 1 and 50", name="first_name_length"
        ),
        CheckConstraint("length(last_name) between 1 and 50", name="last_name_length"),
        CheckConstraint("length(city) between 1 and 100", name="city_length"),
        CheckConstraint(
            "length(address_line_1) between 1 and 255", name="address_length"
        ),
        CheckConstraint("length(phone_number) = 10", name="phone_length"),
        CheckConstraint(
            non_digit_count(column("phone_number")) == 0, name="phone_digits"
        ),
        CheckConstraint("length(zip_code) in (5, 10)", name="zip_length"),
        CheckConstraint(
            and_(
                non_digit_count(func.replace(column("zip_code"), "-", "")) == 0,
                or_(
                    func.length(column("zip_code")) == 5,
                    func.substr(column("zip_code"), 6, 1) == "-",
                ),
            ),
            name="zip_format",
        ),
        CheckConstraint(column("state").in_(sorted(STATES)), name="state_value"),
        CheckConstraint(
            column("date_of_birth") <= func.current_date(), name="dob_not_future"
        ),
        CheckConstraint(
            "sex in ('Male', 'Female', 'Other', 'Decline to Answer')", name="sex_value"
        ),
    )

    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(20))
    phone_number: Mapped[str] = mapped_column(String(10), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    address_line_1: Mapped[str] = mapped_column(String(255))
    address_line_2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(10))
    insurance_provider: Mapped[str | None] = mapped_column(String(255))
    insurance_member_id: Mapped[str | None] = mapped_column(String(100))
    preferred_language: Mapped[str] = mapped_column(String(100), default="English")
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
