"""WorkSight FastAPI Application Entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    attendance,
    auth,
    cameras,
    dashboard,
    departments,
    employees,
    events,
    leaves,
    notifications,
    reports,
    settings as settings_api,
)
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import decode_token
from app.models.models import User
from app.services.realtime import realtime_hub
from app.services.retention import run_retention_purge
from app.services.seed import seed_demo_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worksight")


async def _background_retention_loop() -> None:
    """Periodically enforce video & metadata retention policies."""
    while True:
        await asyncio.sleep(3600)  # Hourly sweep
        db = SessionLocal()
        try:
            run_retention_purge(db)
        except Exception as exc:
            logger.warning("Background retention sweep skipped: %s", exc)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure schema exists and seed realistic demo data idempotently
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()

    retention_task = asyncio.create_task(_background_retention_loop())
    logger.info("WorkSight API ready.")
    try:
        yield
    finally:
        retention_task.cancel()


cfg = get_settings()

app = FastAPI(
    title="WorkSight — AI-Powered Employee Attendance & Workplace Intelligence API",
    description=(
        "Privacy-first enterprise workplace intelligence platform separating verified "
        "attendance from anonymous AI computer vision occupancy telemetry."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Robust CORS Configuration: Allow all localhost and 127.0.0.1 ports (3000, 3001, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ] + cfg.cors_origin_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register modular API routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(departments.router)
app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(leaves.router)
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(settings_api.router)


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": cfg.APP_NAME,
        "environment": cfg.APP_ENV,
        "simulated_feeds_enabled": cfg.ALLOW_SIMULATED_FEEDS,
        "ethical_guardrails": {
            "facial_recognition": False,
            "emotion_recognition": False,
            "automated_productivity_scoring": False,
            "human_review_required": True,
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(payload["sub"]), User.is_active == True).first()  # noqa: E712
        if not user:
            await websocket.close(code=1008)
            return
        user_id = user.id
        role = user.role
        managed_dept_id = user.managed_department_id
    finally:
        db.close()

    client = await realtime_hub.connect(
        websocket=websocket,
        user_id=user_id,
        role=role,
        managed_department_id=managed_dept_id,
    )
    try:
        await websocket.send_json({"type": "connected", "payload": {"role": role}})
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await realtime_hub.disconnect(client)
    except Exception:
        await realtime_hub.disconnect(client)
