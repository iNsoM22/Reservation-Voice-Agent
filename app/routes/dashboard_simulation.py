"""Authenticated browser voice page using the saved Vapi assistant."""

from pathlib import Path

from fastapi import APIRouter, Request
from starlette.templating import Jinja2Templates

from app.routes.dashboard_auth import require_dashboard_user

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/dashboard/simulation")
def simulation_page(request: Request):
    require_dashboard_user(request)
    settings = request.app.state.settings
    return templates.TemplateResponse(
        request=request,
        name="simulation.html",
        context={
            "vapi_public_key": settings.vapi_public_key,
            "vapi_assistant_id": settings.vapi_assistant_id,
        },
    )
