"""Authenticated call-log dashboard pages."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.routes.dashboard_auth import require_dashboard_user
from app.services.call_logs import CallLogService

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
PAGE_SIZE = 20


@router.get("/dashboard/calls")
def call_logs(request: Request, page: int = Query(default=1, ge=1, le=100_000)):
    require_dashboard_user(request)
    with Session(request.app.state.engine) as session:
        rows, total = CallLogService(session).list_page(page, PAGE_SIZE)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        return templates.TemplateResponse(
            request=request,
            name="calls_list.html",
            context={"call_logs": rows, "page": page, "pages": pages, "total": total},
        )


@router.get("/dashboard/calls/{call_log_id}")
def call_log_detail(request: Request, call_log_id: UUID):
    require_dashboard_user(request)
    with Session(request.app.state.engine) as session:
        call_log = CallLogService(session).get_by_id(call_log_id)
        if call_log is None:
            return templates.TemplateResponse(
                request=request,
                name="call_not_found.html",
                context={},
                status_code=404,
            )
        session.expunge(call_log)
    return templates.TemplateResponse(
        request=request,
        name="call_detail.html",
        context={"call_log": call_log},
    )
