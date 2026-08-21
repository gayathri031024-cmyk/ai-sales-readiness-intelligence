"""
Phase 14 Skill Graph / Root-Cause Analysis API.

One route, `GET /conversations/{id}/root-cause-analysis` — a single
read-only verb, same deliberate API-shape decision as Phase 12's
difficulty-recommendation endpoint (see DECISIONS.md, Phase 12 and
Phase 14): the result is a pure, free-to-recompute function of
already-durable data, so there is nothing to trigger or persist.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.skill_graph import service
from app.skill_graph.schemas import RootCauseAnalysisOut

router = APIRouter(prefix="/conversations", tags=["skill-graph"])


@router.get("/{conversation_id}/root-cause-analysis", response_model=RootCauseAnalysisOut)
def get_root_cause_analysis(conversation_id: str, db: Session = Depends(get_db)) -> RootCauseAnalysisOut:
    try:
        return service.compute_root_cause_analysis(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.EvaluationNotFoundError:
        raise HTTPException(status_code=409, detail="Conversation has not been evaluated yet")
