"""
Main FastAPI Application Entrypoint for SAKSHAM AI.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.database.session import engine, SessionLocal
from app.database.base import Base
from app.models import *  # Import all models to register with Base
from app.services.execution_engine import ExecutionEngine


class ExecutionRequestSizeLimitMiddleware:
    """Bound request buffering for submitted source and stdin before parsing JSON."""

    def __init__(self, app, max_bytes: int = 64 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("path") != "/api/v1/coding/execute" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send)
                return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                await self._reject(send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        buffered_body = bytes(body)
        delivered = False

        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": buffered_body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, send):
        body = b'{"detail":"Execution request exceeds the 64 KiB limit"}'
        await send({"type": "http.response.start", "status": 413, "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]})
        await send({"type": "http.response.body", "body": body})


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ExecutionEngine.seed_problems_if_empty(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()
    yield


# Run schema creation at import time for tests as well
init_db()

# Import Routers
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
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="SAKSHAM AI — Elite AI Mock Interview Platform API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    app.add_middleware(ExecutionRequestSizeLimitMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API Routers
    api_v1_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_v1_prefix)
    app.include_router(users_router, prefix=api_v1_prefix)
    app.include_router(interviews_router, prefix=api_v1_prefix)
    app.include_router(interviewers_router, prefix=api_v1_prefix)
    app.include_router(coding_router, prefix=api_v1_prefix)
    app.include_router(problems_router, prefix=api_v1_prefix)
    app.include_router(resumes_router, prefix=api_v1_prefix)
    app.include_router(evaluations_router, prefix=api_v1_prefix)
    app.include_router(analytics_router, prefix=api_v1_prefix)
    app.include_router(companies_router, prefix=api_v1_prefix)
    app.include_router(roadmaps_router, prefix=api_v1_prefix)
    app.include_router(settings_router, prefix=api_v1_prefix)
    app.include_router(subscriptions_router, prefix=api_v1_prefix)
    app.include_router(voice_router, prefix=api_v1_prefix)
    app.include_router(admin_router, prefix=api_v1_prefix)
    app.include_router(websocket_router, prefix=api_v1_prefix)

    @app.get("/health", tags=["Health"])
    def health_check():
        return {
            "status": "online",
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV
        }

    return app


app = create_app()
