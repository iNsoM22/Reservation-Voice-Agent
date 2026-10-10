"""Request authentication and database session dependencies."""

from collections.abc import Iterator
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.routes.errors import APIError
from app.services.patients import PatientService


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def require_api_key(
    request: Request, x_api_key: str | None = Header(default=None)
) -> None:
    expected = request.app.state.settings.api_key
    if not expected:
        raise APIError(503, "not_configured", "API access is not configured")
    if not x_api_key or not compare_digest(x_api_key, expected):
        raise APIError(401, "unauthorized", "A valid API key is required")


def patient_service(
    session: Annotated[Session, Depends(get_session)],
) -> PatientService:
    return PatientService(session)
