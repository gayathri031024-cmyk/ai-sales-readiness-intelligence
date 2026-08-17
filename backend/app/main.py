from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.conversation import router as conversation_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.health import router as health_router
from app.api.routes.scenario import router as scenario_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base, SessionLocal, engine
from app.scenario.service import seed_mvp_scenario

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience only. Production (Phase 21) relies exclusively on
    # Alembic migrations — never auto-create schema outside development.
    # MVP scenario seed data currently rides along with this same
    # dev-only guard (see KNOWN_ISSUES.md) rather than a proper seed
    # migration — appropriate for a single hardcoded MVP scenario, not
    # appropriate once real scenario authoring exists.
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_mvp_scenario(db)
        finally:
            db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health_router, tags=["health"])
app.include_router(scenario_router)
app.include_router(conversation_router)
app.include_router(evaluation_router)


@app.get("/")
def root() -> dict:
    return {"message": f"{settings.app_name} API — Phase 8: Evaluation Engine"}
