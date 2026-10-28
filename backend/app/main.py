from contextlib import asynccontextmanager
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.holdings import router as holdings_router
from app.api.routes.rules import router as rules_router
from app.api.routes.screening import router as screening_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.db.connection import db_manager

configure_logging(settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event: initialize database tables automatically on server startup."""
    logger.info("Server starting up: verifying database tables...")
    db_manager.init_tables()
    yield
    logger.info("Server shutting down: closing database connection pool...")
    db_manager.close_all()


app = FastAPI(
    title="Screening Frontend API",
    description="Backend API for the equity screening application.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s %s %.2fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


register_error_handlers(app)
app.include_router(health_router)
app.include_router(screening_router)
app.include_router(rules_router)
app.include_router(holdings_router)


@app.get("/", tags=["root"])
def root():
    """Welcome endpoint providing status and links to interactive documentation."""
    return {
        "status": "online",
        "service": "Equity Screening API",
        "documentation": "/docs",
        "health_check": "/health",
    }

