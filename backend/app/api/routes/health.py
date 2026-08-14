from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()

    db_ok = True
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — health check must never crash the endpoint
        db_ok = False
        db_error = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "ok" if db_ok else "error",
        "database_error": db_error,
    }
