"""Authenticated browser voice page using the saved Vapi assistant."""

import re
import time
from pathlib import Path

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException
from starlette.templating import Jinja2Templates

from app.routes.dashboard_auth import (
    _signed,
    csrf_token,
    require_dashboard_user,
    validate_csrf,
)
from app.validations.simulation import SimulationNumber

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
            "csrf_token": csrf_token(request),
        },
    )


@router.post("/dashboard/simulation/number")
def simulation_number(request: Request, data: SimulationNumber):
    require_dashboard_user(request)
    validate_csrf(request, data.csrf_token)
    number = re.sub(r"[\s().-]", "", data.phone_number)
    if re.fullmatch(r"[0-9]{10}", number):
        number = "+1" + number
    if not re.fullmatch(r"\+1[0-9]{10}", number):
        raise HTTPException(422, "Enter a 10-digit US phone number")
    secret = request.app.state.settings.dashboard_session_secret
    return {"token": _signed(secret, f"{number}:{int(time.time()) + 3600}")}
