"""Authenticated patient dashboard pages."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.routes.dashboard_auth import require_dashboard_user
from app.services.patients import PatientService

router = APIRouter()
APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=APP_DIR / "templates")
PAGE_SIZE = 10


@router.get("/dashboard")
def dashboard(request: Request):
    require_dashboard_user(request)
    return RedirectResponse("/dashboard/patients", status_code=303)


@router.get("/dashboard/patients")
def patients(request: Request, page: int = Query(default=1, ge=1, le=100_000)):
    require_dashboard_user(request)
    with Session(request.app.state.engine) as session:
        rows, total = PatientService(session).list_page(page, PAGE_SIZE)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        if page > pages:
            return RedirectResponse(
                f"/dashboard/patients?page={pages}", status_code=303
            )
        return templates.TemplateResponse(
            request=request,
            name="patients.html",
            context={"patients": rows, "page": page, "pages": pages, "total": total},
        )


@router.get("/dashboard/patients/{patient_id}")
def patient_detail(request: Request, patient_id: UUID):
    require_dashboard_user(request)
    with Session(request.app.state.engine) as session:
        patient = PatientService(session).get(patient_id)
        if patient is None:
            return templates.TemplateResponse(
                request=request,
                name="not_found.html",
                context={},
                status_code=404,
            )
        session.expunge(patient)
    return templates.TemplateResponse(
        request=request, name="patient_detail.html", context={"patient": patient}
    )
