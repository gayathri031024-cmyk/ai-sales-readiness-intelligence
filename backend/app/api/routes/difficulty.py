"""
Phase 12 adaptive-difficulty API.

Unlike Phase 9/10/11's "two verbs, one noun" (`POST` to compute +
persist, `GET` to fetch), this is a single read-only `GET` — there is
nothing to persist (see `difficulty/service.py`'s module docstring),
so there is no separate "trigger" step distinct from "fetch." Requires
readiness (Phase 9) to have already been computed — this module never
triggers that step itself.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.difficulty import service
from app.difficulty.schemas import DifficultyRecommendationOut

router = APIRouter(prefix="/conversations", tags=["difficulty"])


@router.get("/{conversation_id}/difficulty-recommendation", response_model=DifficultyRecommendationOut)
def get_difficulty_recommendation(conversation_id: str, db: Session = Depends(get_db)) -> DifficultyRecommendationOut:
    try:
        return service.compute_difficulty_recommendation(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.ReadinessNotFoundError:
        raise HTTPException(status_code=409, detail="Conversation has not been assessed for readiness yet")
    except service.ScenarioDifficultyInvalidError:
        # Never leak internal exception details — see ARCHITECTURE.md §7.
        raise HTTPException(status_code=500, detail="Unable to compute a difficulty recommendation")
