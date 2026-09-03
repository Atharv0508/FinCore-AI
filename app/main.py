from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.razorpay import router as razorpay_router
from app.routers.reconciliation import router as reconciliation_router
from app.services.mongo import MongoService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    mongo = MongoService(settings)
    app.state.mongo = mongo
    try:
        await mongo.ping()
        await mongo.ensure_indexes()
        yield
    finally:
        mongo.close()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_origin_regex=(r"https?://(localhost|127\.0\.0\.1):\d+" if settings.environment == "development" else None),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(razorpay_router)
app.include_router(reconciliation_router)
