"""
Phase 11 drills API.

Same "two verbs, one noun" pattern as Phase 9/10: `POST .../drill`
triggers the pipeline (idempotent), `GET .../drill` fetches the
persisted result. Requires coaching (Phase 10) to have already run —
this module never triggers that step itself.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.drills import service
from app.drills.schemas import DrillOut

router = APIRouter(prefix="/conversations", tags=["drills"])


@router.post("/{conversation_id}/drill", response_model=DrillOut)
def compute_drill(conversation_id: str, db: Session = Depends(get_db)) -> DrillOut:
    try:
        drill = service.compute_and_persist_drill(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.CoachingNotFoundError:
        raise HTTPException(status_code=409, detail="Conversation has not been coached yet")
    except Exception:
        # Never leak internal exception details — see ARCHITECTURE.md §7.
        raise HTTPException(status_code=500, detail="Failed to generate drill")
    return service.to_drill_out(drill)


@router.get("/{conversation_id}/drill", response_model=DrillOut)
def get_drill(conversation_id: str, db: Session = Depends(get_db)) -> DrillOut:
    try:
        drill = service.get_drill(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.DrillNotFoundError:
        raise HTTPException(status_code=404, detail="No drill found for this conversation")
    return service.to_drill_out(drill)
