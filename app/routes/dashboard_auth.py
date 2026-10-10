"""Cookie authentication for the server-rendered dashboard."""

import hashlib
import hmac
import secrets
import time
from html import escape
from urllib.parse import parse_qs
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.models.user import User
from app.services.auth import verify_password

router = APIRouter()
SESSION_SECONDS = 8 * 60 * 60


def _signature(secret: str, value: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _signed(secret: str, value: str) -> str:
    return f"{value}.{_signature(secret, value)}"


def _verified(secret: str, token: str) -> str | None:
    value, separator, signature = token.rpartition(".")
    if not separator or not hmac.compare_digest(_signature(secret, value), signature):
        return None
    return value


def csrf_token(request: Request) -> str:
    """Return the signed form token set by dashboard login."""
    return request.cookies.get("dashboard_csrf", "")


def validate_csrf(request: Request, submitted: str) -> None:
    token = csrf_token(request)
    secret = request.app.state.settings.dashboard_session_secret
    if (
        not secret
        or not token
        or not submitted
        or not hmac.compare_digest(token, submitted)
    ):
        raise HTTPException(403, "Invalid CSRF token")
    if _verified(secret, token) is None:
        raise HTTPException(403, "Invalid CSRF token")


def require_dashboard_user(request: Request) -> User:
    """Resolve the signed session or redirect a browser to login."""
    secret = request.app.state.settings.dashboard_session_secret
    value = (
        _verified(secret, request.cookies.get("dashboard_session", ""))
        if secret
        else None
    )
    if value:
        try:
            user_id, expires = value.split(":", 1)
            if int(expires) > time.time():
                with Session(request.app.state.engine) as session:
                    user = session.get(User, UUID(user_id))
                    if user and user.role == "admin":
                        session.expunge(user)
                        return user
        except (ValueError, TypeError):
            pass
    raise HTTPException(303, headers={"Location": "/dashboard/login"})


async def _form(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0]
    if content_type not in ("", "application/x-www-form-urlencoded"):
        raise HTTPException(415, "Form encoding required")
    fields = parse_qs((await request.body()).decode("utf-8"), max_num_fields=10)
    return {name: values[0] for name, values in fields.items()}


@router.get("/dashboard/login", response_class=HTMLResponse)
def login_page(request: Request):
    secret = request.app.state.settings.dashboard_session_secret
    if not secret:
        raise HTTPException(503, "Dashboard login is not configured")
    token = _signed(secret, secrets.token_urlsafe(32))
    response = HTMLResponse(
        "<!doctype html><html lang='en'><meta charset='utf-8'><title>Admin login</title>"
        "<main><h1>Patient dashboard</h1><form method='post'>"
        f"<input type='hidden' name='csrf_token' value='{escape(token)}'>"
        "<label>Email <input name='email' type='email' required></label>"
        "<label>Password <input name='password' type='password' required></label>"
        "<button type='submit'>Sign in</button></form></main></html>"
    )
    response.set_cookie(
        "dashboard_csrf",
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=SESSION_SECONDS,
    )
    return response


@router.post("/dashboard/login")
async def login(request: Request):
    fields = await _form(request)
    validate_csrf(request, fields.get("csrf_token", ""))
    email = fields.get("email", "").strip().lower()
    with Session(request.app.state.engine) as session:
        user = session.scalar(select(User).where(User.email == email))
        if (
            not user
            or user.role != "admin"
            or not verify_password(fields.get("password", ""), user.password_hash)
        ):
            raise HTTPException(401, "Invalid email or password")
        identifier = user.user_id
    secret = request.app.state.settings.dashboard_session_secret
    token = _signed(secret, f"{identifier}:{int(time.time()) + SESSION_SECONDS}")
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        "dashboard_session",
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=SESSION_SECONDS,
    )
    return response


@router.post("/dashboard/logout")
async def logout(request: Request):
    require_dashboard_user(request)
    fields = await _form(request)
    validate_csrf(request, fields.get("csrf_token", ""))
    response = RedirectResponse("/dashboard/login", status_code=303)
    response.delete_cookie("dashboard_session")
    return response
