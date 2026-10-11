"""Persisted call details from Vapi and historical local simulations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.patient import Base, UTCDateTime, utc_now


class CallLog(Base):
    __tablename__ = "call_logs"
    __table_args__ = (UniqueConstraint("call_id", name="uq_call_logs_call_id"),)

    call_log_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    call_id: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(32), default="vapi")
    status: Mapped[str] = mapped_column(String(100), default="ended")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    caller_number: Mapped[str | None] = mapped_column(String(100))
    called_number: Mapped[str | None] = mapped_column(String(100))
    transcript: Mapped[str] = mapped_column(Text, default="")
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    patient_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
