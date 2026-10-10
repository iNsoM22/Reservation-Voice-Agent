"""FastAPI application wiring."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import Settings
from app.models import user  # noqa: F401 - register the users table with Base
from app.models.patient import Base
from app.routes.dashboard import router as dashboard_router
from app.routes.dashboard_auth import router as dashboard_auth_router
from app.routes.dashboard_calls import router as dashboard_calls_router
from app.routes.errors import APIError, error_response
from app.routes.patients import router as patient_router
from app.routes.vapi import router as vapi_router
from app.services.auth import bootstrap_admin

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database_url = settings.database_url.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
    engine = create_engine(database_url, pool_pre_ping=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            bootstrap_admin(session, settings.admin_email, settings.admin_password)
        yield
        engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )
    app.include_router(patient_router)
    app.include_router(vapi_router)
    app.include_router(dashboard_auth_router)
    app.include_router(dashboard_router)
    app.include_router(dashboard_calls_router)

    @app.middleware("http")
    async def authenticate_vapi(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/calls/vapi":
            expected = settings.vapi_webhook_token
            if not expected:
                return error_response(
                    503, "not_configured", "Call webhook is not configured"
                )
            token = request.headers.get("Authorization", "")
            if not compare_digest(token, f"Bearer {expected}"):
                return error_response(
                    401, "unauthorized", "A valid webhook token is required"
                )
        return await call_next(request)

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Not found" if exc.status_code == 404 else str(exc.detail)
        return error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"] if part != "body"),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return error_response(422, "validation_error", "Invalid request", details)

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError):
        logger.error("Database operation failed: %s", type(exc).__name__)
        return error_response(
            500, "database_error", "The database is temporarily unavailable"
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
