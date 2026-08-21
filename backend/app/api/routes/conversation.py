from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.factory import build_llm_provider
from app.ai.provider import LLMProvider
from app.conversation import service
from app.conversation.schemas import ConversationOut, SendTurnIn, StartConversationIn
from app.db.base import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_llm_provider() -> LLMProvider:
    """Real provider by default. Tests override this dependency with a
    `MockLLMProvider` instance (see tests/test_conversation.py) — the
    exact same pattern `get_db` uses for a test database, so no test ever
    requires LLM_API_KEY / ANTHROPIC_API_KEY."""
    return build_llm_provider()


@router.post("", response_model=ConversationOut, status_code=201)
def start_conversation(
    body: StartConversationIn,
    db: Session = Depends(get_db),
) -> ConversationOut:
    try:
        conversation = service.start_conversation(db, body.scenario_id)
    except service.ScenarioNotFoundError:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return service.to_conversation_out(conversation)


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> ConversationOut:
    try:
        conversation = service.get_conversation(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return service.to_conversation_out(conversation)


@router.post("/{conversation_id}/turns", response_model=ConversationOut)
def send_turn(
    conversation_id: str,
    body: SendTurnIn,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
) -> ConversationOut:
    try:
        conversation = service.submit_turn(
            db,
            conversation_id,
            rep_message=body.message,
            provider=provider,
        )
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except service.ConversationNotActiveError:
        raise HTTPException(status_code=409, detail="Conversation has already ended")
    except Exception:
        # Never leak internal exception details, prompts, or stack traces
        # to the client — see ARCHITECTURE.md §7.
        raise HTTPException(status_code=500, detail="Failed to process turn")
    return service.to_conversation_out(conversation)


@router.post("/{conversation_id}/close", response_model=ConversationOut)
def close_conversation(conversation_id: str, db: Session = Depends(get_db)) -> ConversationOut:
    try:
        conversation = service.close_conversation(db, conversation_id)
    except service.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return service.to_conversation_out(conversation)
