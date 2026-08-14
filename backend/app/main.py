from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base, engine

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience only. Production (Phase 21) relies exclusively on
    # Alembic migrations — never auto-create schema outside development.
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health_router, tags=["health"])


@app.get("/")
def root() -> dict:
    return {"message": f"{settings.app_name} API — Phase 3 foundation"}
