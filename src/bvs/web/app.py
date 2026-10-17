"""Local HTTP application with origin, authentication and CSRF checks."""

from __future__ import annotations

import base64
import secrets
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint

from bvs import __version__
from bvs.config import Settings
from bvs.errors import BVSError
from bvs.service import Service

STATIC = Path(__file__).parent / "static"
STATUSES = {
    "NOT_FOUND": 404,
    "ENGINE_UNAVAILABLE": 409,
    "EXTRA_MISSING": 409,
    "MODEL_MISSING": 409,
    "MODEL_INCOMPLETE": 409,
    "OFFLINE": 409,
    "WORKER_LOCKED": 409,
    "INVALID_STATE": 409,
    "IDEMPOTENCY_CONFLICT": 409,
    "IDEMPOTENCY_EXPIRED": 410,
    "QUEUE_FULL": 429,
    "TOO_LARGE": 413,
    "UNSUPPORTED_MEDIA": 415,
    "EXPORT_FAILED": 409,
}


def error_response(
    code: str,
    message: str,
    status: int,
    *,
    details: list[dict[str, str]] | None = None,
    retryable: bool = False,
) -> JSONResponse:
    return JSONResponse(
        dict(
            error=dict(code=code, message=message, details=details or [], retryable=retryable),
            request_id=str(uuid4()),
        ),
        status_code=status,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    service = Service(settings)
    csrf = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        with service:
            yield

    app = FastAPI(title="Bangla Voice Studio", version=__version__, lifespan=lifespan)
    app.state.service = service

    @app.exception_handler(BVSError)
    async def bvs_error(request: Request, exc: BVSError) -> JSONResponse:
        return error_response(
            exc.code, exc.message, STATUSES.get(exc.code, 422), retryable=exc.retryable
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
        ]
        malformed = any(e["type"] == "json_invalid" for e in exc.errors())
        return error_response(
            "INVALID_INPUT",
            "Check the highlighted fields",
            400 if malformed else 422,
            details=details,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            "Resource not found" if exc.status_code == 404 else "Request could not be completed",
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        return error_response(
            "INTERNAL_ERROR", "Request failed; retry or check local service state", 500
        )

    @app.middleware("http")
    async def boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = urlsplit("//" + request.headers.get("host", "")).hostname
        allowed = {"localhost", "127.0.0.1", "::1", settings.host}
        if settings.demo or __import__("os").getenv("BVS_TEST_MODE") == "1":
            allowed.add("testserver")
        if host not in allowed:
            return error_response("ACCESS_DENIED", "Host is not allowed", 403)
        if request.url.path not in {"/health", "/api/v1/health"} and settings.api_token:
            authorization = request.headers.get("authorization", "")
            supplied = ""
            if authorization.startswith("Bearer "):
                supplied = authorization[7:]
            elif authorization.startswith("Basic "):
                try:
                    username, password = (
                        base64.b64decode(authorization[6:], validate=True).decode().split(":", 1)
                    )
                    if username == "bvs":
                        supplied = password
                except (ValueError, UnicodeError):
                    pass
            if not secrets.compare_digest(supplied.encode(), settings.api_token.encode()):
                response: Response = error_response("AUTH_REQUIRED", "Authentication required", 401)
                response.headers["WWW-Authenticate"] = 'Basic realm="Bangla Voice Studio"'
                return response
        mutation = request.method not in {"GET", "HEAD", "OPTIONS"}
        origin = request.headers.get("origin")
        if mutation and origin:
            if origin != f"{request.url.scheme}://{request.headers.get('host')}":
                return error_response("ACCESS_DENIED", "Cross-origin requests are not allowed", 403)
            if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), csrf):
                return error_response("CSRF_REQUIRED", "Reload the page and retry", 403)
        if mutation and request.headers.get("sec-fetch-site") == "cross-site":
            return error_response("ACCESS_DENIED", "Cross-site requests are not allowed", 403)
        if request.headers.get("idempotency-key") is not None:
            path = request.url.path
            supported = path in {
                "/api/v1/syntheses",
                "/api/v1/clones",
                "/api/v1/transcriptions",
                "/api/v1/audiobooks",
            } or path.endswith(("/downloads", "/resumptions"))
            if request.method != "POST" or not supported:
                return error_response(
                    "INVALID_HEADER", "This route does not support Idempotency-Key", 400
                )
        limit = 251_000_000 if request.url.path == "/api/v1/uploads" else 4_100_000
        try:
            if int(request.headers.get("content-length", "0")) > limit:
                return error_response("TOO_LARGE", "Request exceeds size limit", 413)
        except ValueError:
            return error_response("INVALID_INPUT", "Invalid content length", 400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        return dict(
            status="ok",
            version=__version__,
            offline=settings.offline,
            test_mode=settings.demo,
            ffmpeg_available=bool(shutil.which("ffmpeg")),
        )

    from bvs.web.routes import router

    app.include_router(router)

    def shell() -> Response:
        response: Response = (
            FileResponse(STATIC / "index.html")
            if (STATIC / "index.html").exists()
            else Response("Bangla Voice Studio", media_type="text/plain")
        )
        response.set_cookie("bvs_csrf", csrf, samesite="strict", secure=False)
        return response

    for path in ("/", "/speak", "/clone", "/transcribe", "/audiobook", "/engines"):
        app.add_api_route(path, shell, methods=["GET"], include_in_schema=False)
    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
