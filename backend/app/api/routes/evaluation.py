"""
Phase 8 evaluation API.

Endpoint naming deliberately diverges from ARCHITECTURE.md §5's original
sketch (`POST /conversations/{id}/complete` -> `GET /conversations/{id}/result`)
for the same reason Phase 7 diverged on `/close` vs. `/complete` (see
DECISIONS.md, Phase 7): "complete" is already Phase 7's `/close` endpoint,
and "/result" would imply a readiness verdict is included, which this
phase's PHASE BOUNDARY explicitly excludes (see DECISIONS.md, Phase 8).
`POST .../evaluate` triggers the pipeline; `GET .../evaluation` fetches
the persisted result — two verbs on the same underlying resource, same
pattern as `POST /conversations` (create) vs. `GET /conversations/{id}`
(fetch) in Phase 7.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.provider import LLMProvider
from app.api.routes.conversation import get_llm_provider
from app.db.base import get_db
from app.evaluation import service
from app.evaluation.schemas import ConversationEvaluationOut

router = APIRouter(prefix="/conversations", tags=["evaluations"])


@router.post("/{conversation_id}/evaluate", response_model=ConversationEvaluationOut)
def evaluate_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
) -> ConversationEvaluationOut:
    try:
        evaluations = service.evaluate_conversation(db, conversation_id, provider)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.ConversationNotCompletedError:
        raise HTTPException(status_code=409, detail="Conversation has not ended yet")
    except Exception:
        # Never leak internal exception details, prompts, transcripts, or
        # stack traces to the client — see ARCHITECTURE.md §7.
        raise HTTPException(status_code=500, detail="Failed to evaluate conversation")
    return service.to_conversation_evaluation_out(conversation_id, evaluations)


@router.get("/{conversation_id}/evaluation", response_model=ConversationEvaluationOut)
def get_evaluation(conversation_id: str, db: Session = Depends(get_db)) -> ConversationEvaluationOut:
    try:
        evaluations = service.get_evaluation(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.EvaluationNotFoundError:
        raise HTTPException(status_code=404, detail="No evaluation found for this conversation")
    return service.to_conversation_evaluation_out(conversation_id, evaluations)
