"""
Phase 9 readiness API.

Three routes on the conversation resource, same "two verbs, one noun"
pattern as Phase 8's evaluation routes:

- `POST .../readiness` — explicit trigger (idempotent: computing readiness
  is free deterministic Python, so a repeat call just returns the existing
  persisted verdict rather than recomputing it — see DECISIONS.md, Phase 9).
  Requires evaluation (Phase 8) to have already run; this module never
  triggers that step itself (`readiness/` never calls anything that could
  make an LLM call, per ARCHITECTURE.md §3's module boundary) — a 409 here
  means "run POST .../evaluate first," not a crash.
- `GET .../readiness` — fetch-only, 404 if no verdict has been computed yet.
- `GET .../result` — the combined shape the frontend `Result` screen
  actually needs (Phase 8 evaluations, each now carrying its scenario
  threshold, alongside the Phase 9 verdict). Computes-and-persists
  readiness lazily if evaluation already ran but readiness hasn't been
  explicitly triggered yet — still free, still deterministic, still never
  triggers evaluation itself.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.readiness import service
from app.readiness.schemas import ConversationResultOut, ReadinessOut

router = APIRouter(prefix="/conversations", tags=["readiness"])


@router.post("/{conversation_id}/readiness", response_model=ReadinessOut)
def compute_readiness(conversation_id: str, db: Session = Depends(get_db)) -> ReadinessOut:
    try:
        readiness = service.compute_and_persist_readiness(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.EvaluationNotFoundError:
        raise HTTPException(status_code=409, detail="Conversation has not been evaluated yet")
    except service.ThresholdMissingError:
        raise HTTPException(status_code=500, detail="Failed to compute readiness")
    except Exception:
        # Never leak internal exception details — see ARCHITECTURE.md §7.
        raise HTTPException(status_code=500, detail="Failed to compute readiness")
    return service.to_readiness_out(readiness)


@router.get("/{conversation_id}/readiness", response_model=ReadinessOut)
def get_readiness(conversation_id: str, db: Session = Depends(get_db)) -> ReadinessOut:
    try:
        readiness = service.get_readiness(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.ReadinessNotFoundError:
        raise HTTPException(status_code=404, detail="No readiness decision found for this conversation")
    return service.to_readiness_out(readiness)


@router.get("/{conversation_id}/result", response_model=ConversationResultOut)
def get_conversation_result(conversation_id: str, db: Session = Depends(get_db)) -> ConversationResultOut:
    try:
        conversation, readiness = service.get_conversation_result(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.EvaluationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation has not been evaluated yet")
    except service.ThresholdMissingError:
        raise HTTPException(status_code=500, detail="Failed to compute result")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to compute result")
    return service.to_conversation_result_out(conversation, readiness)
