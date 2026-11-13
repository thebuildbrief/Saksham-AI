"""
FastAPI application for Saksham AI.

Database schema initialization is idempotent and registers every ORM model first.
Production requires managed PostgreSQL, configured secrets, AI, and persistent storage.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.database.session import engine, SessionLocal
from app.database.base import Base
from app.models import *  # noqa: F403 - register all ORM metadata before create_all
from app.services.execution_engine import ExecutionEngine


class RequestSizeLimitMiddleware:
    """Bound bodies before JSON/form parsing, including resume multipart overhead."""
    def __init__(self, app, max_execution_bytes: int = 64 * 1024):
        self.app = app
        self.max_execution_bytes = max_execution_bytes

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/api/v1/coding/execute":
            limit = self.max_execution_bytes
        elif path == "/api/v1/resumes":
            limit = settings.MAX_RESUME_SIZE_BYTES + 256 * 1024
        else:
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > limit:
                    await self._reject(send, limit)
                    return
            except ValueError:
                await self._reject(send, limit)
                return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                await self._reject(send, limit)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        buffered = bytes(body)
        delivered = False
        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": buffered, "more_body": False}
            return await receive()
        await self.app(scope, replay_receive, send)

    async def _reject(self, send, limit):
        body = b'{"detail":"Request exceeds the configured upload limit"}'
        await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))]})
        await send({"type": "http.response.body", "body": body})


def init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ExecutionEngine.seed_problems_if_empty(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Saksham AI API started")
    yield
    # SQLAlchemy's bounded pool is kept warm per function instance and reaped by the runtime.


# Import-time registration supports serverless function cold starts and direct TestClient use.
init_db()

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.interviewers import router as interviewers_router
from app.api.v1.coding import router as coding_router
from app.api.v1.problems import router as problems_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.companies import router as companies_router
from app.api.v1.roadmaps import router as roadmaps_router
from app.api.v1.settings import router as settings_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.voice import router as voice_router
from app.api.v1.admin import router as admin_router
from app.websocket.interview_socket import router as websocket_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0", description="SAKSHAM AI — AI interview practice and coding platform API", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "Stripe-Signature"])
    prefix = "/api/v1"
    for router in (auth_router, users_router, interviews_router, interviewers_router, coding_router, problems_router, resumes_router, evaluations_router, analytics_router, companies_router, roadmaps_router, settings_router, subscriptions_router, voice_router, admin_router, websocket_router):
        app.include_router(router, prefix=prefix)

    @app.get("/", tags=["Health"])
    def root():
        return {"name": settings.APP_NAME, "docs": "/docs"}

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "online", "app": settings.APP_NAME, "version": "1.0.0", "environment": settings.APP_ENV}

    return app


app = create_app()
