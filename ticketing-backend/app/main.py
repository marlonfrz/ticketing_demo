import mimetypes
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text

from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.event_sessions import router as event_sessions_router
from app.api.routes.ticket_types import router as ticket_types_router
from app.api.routes.orders import router as orders_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.payments import router as payments_router
from app.api.routes.promoter import router as promoter_router
from app.api.routes.admin import router as admin_router
from app.api.routes.ticket_sale_groups import router as ticket_sale_groups_router
from app.api.routes.sales_order import router as sales_order_router
from app.api.routes.sales_options import router as sales_options_router
from app.api.routes.reservations import router as reservations_router
from app.api.routes.validation_stations import router as validation_stations_router
from app.api.routes.public_relations import router as public_relations_router
from app.api.routes.contact import router as contact_router
from app.api.routes.media import router as media_router

from app.core.config import settings
from app.db.session import SessionLocal


app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
)
logger = logging.getLogger("ticketing.requests")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
cors_allow_origins = [
    origin.strip()
    for origin in settings.cors_allow_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
mimetypes.add_type("image/webp", ".webp")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount(
    "/demo-media",
    StaticFiles(directory=Path(__file__).resolve().parent / "demo_media"),
    name="demo-media",
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request error method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(event_sessions_router)
app.include_router(ticket_types_router)
app.include_router(orders_router)
app.include_router(tickets_router)
app.include_router(payments_router)
app.include_router(promoter_router)
app.include_router(admin_router)
app.include_router(ticket_sale_groups_router)
app.include_router(sales_order_router)
app.include_router(sales_options_router)
app.include_router(reservations_router)
app.include_router(validation_stations_router)
app.include_router(public_relations_router)
app.include_router(contact_router)
app.include_router(media_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "ready"}


@app.get("/")
def root():
    return {"message": "Ticketing Demo backend running"}
