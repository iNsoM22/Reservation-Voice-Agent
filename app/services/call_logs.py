"""Call-log persistence and pagination."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.call_log import CallLog
from app.models.patient import utc_now


class CallLogService:
    def __init__(self, session: Session):
        self.session = session

    def record_vapi_report(self, report: dict[str, Any]) -> CallLog:
        call = report.get("call", {})
        artifact = report.get("artifact", {})
        return self._upsert(
            call_id=call["id"],
            source="vapi",
            status=report.get("endedReason") or "ended",
            started_at=_timestamp(call.get("startedAt")),
            ended_at=_timestamp(call.get("endedAt")),
            caller_number=call.get("customer", {}).get("number"),
            called_number=call.get("phoneNumber", {}).get("number"),
            transcript=artifact.get("transcript") or "",
            messages=artifact.get("messages") or [],
        )

    def log_simulation(
        self,
        call_id: str,
        transcript: str,
        messages: list[dict[str, Any]],
        *,
        patient_id: UUID | None = None,
        status: str = "ended",
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> CallLog:
        return self._upsert(
            call_id=call_id,
            source="simulation",
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            transcript=transcript,
            messages=messages,
            patient_id=patient_id,
        )

    def get(self, call_id: str) -> CallLog | None:
        return self.session.scalar(select(CallLog).where(CallLog.call_id == call_id))

    def get_by_id(self, call_log_id: UUID) -> CallLog | None:
        return self.session.get(CallLog, call_log_id)

    def list_page(self, page: int, page_size: int = 20) -> tuple[list[CallLog], int]:
        query = select(CallLog)
        total = (
            self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        )
        rows = self.session.scalars(
            query.order_by(CallLog.created_at.desc(), CallLog.call_log_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), total

    def _upsert(self, **values: Any) -> CallLog:
        call_log = self.get(values["call_id"])
        if call_log is None:
            call_log = CallLog(
                **values, created_at=values.get("started_at") or utc_now()
            )
            self.session.add(call_log)
        else:
            for key, value in values.items():
                if key in {"transcript", "messages"} and not value:
                    continue
                setattr(call_log, key, value)
        try:
            self.session.commit()
            self.session.refresh(call_log)
        except Exception:
            self.session.rollback()
            raise
        return call_log


def _timestamp(value: str | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value) if value else None
