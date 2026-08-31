from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

MAX_REQUEST_BODY_BYTES = 20 * 1024 * 1024  # 20MB limit


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces standard HTTP security response headers."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming requests exceeding maximum body size limits."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BODY_BYTES:
                    return Response(
                        status_code=413,
                        content="Payload Too Large: Request body exceeds size limit.",
                    )
            except ValueError:
                pass
        return await call_next(request)


# Setup centralized logging
setup_logging(
    level=settings.LOG_LEVEL,
    log_dir=settings.LOG_DIR,
    log_file=settings.LOG_FILE,
    json_format=settings.LOG_FORMAT_JSON,
    console_output=settings.LOG_CONSOLE_ENABLED,
    file_output=settings.LOG_FILE_ENABLED,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend foundation for AI Desktop Assistant",
    lifespan=lifespan,
)

# Enforce security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

cors_origins = (
    settings.CORS_ORIGINS
    if settings.CORS_ORIGINS
    else ["http://localhost:5173", "http://127.0.0.1:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint invoked")
    return {"status": "ok"}
