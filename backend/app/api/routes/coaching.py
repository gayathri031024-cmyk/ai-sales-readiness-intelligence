"""
Phase 10 coaching API.

Same "two verbs, one noun" pattern as Phase 8/9: `POST .../coaching`
triggers the pipeline (idempotent), `GET .../coaching` fetches the
persisted result. Requires readiness (Phase 9) to have already been
computed — this module never triggers that step itself.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.provider import LLMProvider
from app.api.routes.conversation import get_llm_provider
from app.coaching import service
from app.coaching.schemas import CoachingSessionOut
from app.db.base import get_db

router = APIRouter(prefix="/conversations", tags=["coaching"])


@router.post("/{conversation_id}/coaching", response_model=CoachingSessionOut)
def compute_coaching(
    conversation_id: str,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
) -> CoachingSessionOut:
    try:
        coaching = service.compute_and_persist_coaching(db, conversation_id, provider)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.ReadinessNotFoundError:
        raise HTTPException(status_code=409, detail="Conversation has not been assessed for readiness yet")
    except Exception:
        # Never leak internal exception details — see ARCHITECTURE.md §7.
        raise HTTPException(status_code=500, detail="Failed to generate coaching")
    return service.to_coaching_session_out(coaching)


@router.get("/{conversation_id}/coaching", response_model=CoachingSessionOut)
def get_coaching(conversation_id: str, db: Session = Depends(get_db)) -> CoachingSessionOut:
    try:
        coaching = service.get_coaching(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.CoachingNotFoundError:
        raise HTTPException(status_code=404, detail="No coaching session found for this conversation")
    return service.to_coaching_session_out(coaching)
