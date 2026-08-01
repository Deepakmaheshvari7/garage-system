"""
FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload

Production (Render/Heroku, etc.):
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403 — ensures models register with Base.metadata
from app.routers import auth, inventory, job_cards, billing, dashboard, users

app = FastAPI(
    title="Bike Showroom & Service Center Inventory System",
    description="Backend API for garage inventory, job card lifecycle, and billing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(job_cards.router)
app.include_router(billing.router)
app.include_router(dashboard.router)
app.include_router(users.router)


@app.on_event("startup")
def on_startup():
    # create_all is convenient for getting started, but for real schema
    # evolution over time you should migrate to Alembic migrations.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "garage-system-api"}
