import logging
import re
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, request_id_context
from app.core.redis import redis_ready

configure_logging()
logger = logging.getLogger("forgeops.http")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API multiempresa para mantenimiento e inteligencia documental industrial.",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url=f"{settings.api_prefix}/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    expose_headers=["X-Request-ID"],
)


def _request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID", "")
    return candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else str(uuid.uuid4())


def _error_payload(request: Request, code: str, detail, status_code: int) -> dict:
    request_id = getattr(request.state, "request_id", "-")
    return {
        "detail": detail,
        "error": {"code": code, "message": detail, "status": status_code},
        "request_id": request_id,
    }


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(request, "http_error", exc.detail, exc.status_code),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = jsonable_encoder(exc.errors(), custom_encoder={ValueError: str})
    return JSONResponse(
        status_code=422,
        content=_error_payload(request, "validation_error", details, 422),
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error")
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            request,
            "internal_error",
            "No se pudo completar la operacion. Facilita el request_id a soporte.",
            500,
        ),
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = _request_id(request)
    request.state.request_id = request_id
    context_token = request_id_context.set(request_id)
    started_at = time.perf_counter()
    try:
        if settings.maintenance_mode and not request.url.path.startswith(
            ("/health", "/ready", f"{settings.api_prefix}/operator")
        ):
            response = JSONResponse(
                status_code=503,
                content=_error_payload(
                    request,
                    "maintenance",
                    "ForgeOps esta en mantenimiento programado. "
                    "Intentalo de nuevo en unos minutos.",
                    503,
                ),
                headers={"Retry-After": "120"},
            )
        else:
            response = await call_next(request)
    finally:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)
        logger.info(
            "request_completed",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": (
                    locals().get("response").status_code if "response" in locals() else 500
                ),
                "duration_ms": elapsed_ms,
            },
        )
        request_id_context.reset(context_token)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    if request.url.path.startswith(
        (f"{settings.api_prefix}/auth", f"{settings.api_prefix}/operator")
    ):
        response.headers["Cache-Control"] = "no-store"
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "commit": settings.build_commit,
    }


@app.get("/ready", tags=["Sistema"])
def readiness():
    checks = {"database": False, "redis": False}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("Database readiness check failed")
    checks["redis"] = redis_ready()
    available = checks["database"] and (checks["redis"] or not settings.redis_required)
    return JSONResponse(
        status_code=200 if available else 503,
        content={"status": "ready" if available else "unavailable", "checks": checks},
    )


app.include_router(api_router, prefix=settings.api_prefix)
