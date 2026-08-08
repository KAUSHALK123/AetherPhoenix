from contextlib import asynccontextmanager

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, setup_logging
from fastapi import FastAPI

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


@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint invoked")
    return {"status": "ok"}
