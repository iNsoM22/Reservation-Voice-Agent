"""Authenticated HTTP endpoints for the browser call simulation."""

from pathlib import Path

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException
from starlette.templating import Jinja2Templates

from app.routes.dashboard_auth import csrf_token, require_dashboard_user, validate_csrf
from app.services.simulation import SimulationNotFound, SimulationService

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
MAX_TEXT = 500


@router.get("/dashboard/simulation")
def simulation_page(request: Request):
    require_dashboard_user(request)
    return templates.TemplateResponse(
        request=request, name="simulation.html", context={"csrf": csrf_token(request)}
    )


@router.post("/dashboard/simulation/calls")
def start_simulation(request: Request):
    user = require_dashboard_user(request)
    _validate_csrf(request)
    return _service(request, user.user_id).start()


@router.get("/dashboard/simulation/current")
def current_simulation(request: Request):
    user = require_dashboard_user(request)
    return _service(request, user.user_id).current()


@router.post("/dashboard/simulation/calls/{call_id}/turn")
async def simulation_turn(request: Request, call_id: str):
    user = require_dashboard_user(request)
    _validate_csrf(request)
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "JSON body required") from exc
    text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise HTTPException(422, f"Enter 1 to {MAX_TEXT} characters")
    try:
        return _service(request, user.user_id).turn(call_id, text)
    except SimulationNotFound as exc:
        raise HTTPException(404, "Simulation not found") from exc


def _service(request: Request, user_id):
    return SimulationService(request.app.state.engine, user_id)


def _validate_csrf(request: Request) -> None:
    validate_csrf(request, request.headers.get("X-CSRF-Token", ""))
