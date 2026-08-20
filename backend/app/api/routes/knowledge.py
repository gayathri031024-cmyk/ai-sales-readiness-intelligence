"""
Phase 13 Product RAG API.

POST /knowledge/documents      — ingest a new document (chunk + embed + persist)
GET  /knowledge/documents      — list ingested documents
GET  /knowledge/documents/{id} — document detail
POST /knowledge/query          — ask a product question, get a grounded
                                  answer + citations (or an explicit
                                  "not found" if nothing in the
                                  knowledge base supports an answer —
                                  see generation.py, never a guess)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.embedding_factory import build_embedding_provider
from app.ai.embedding_provider import EmbeddingProvider
from app.ai.provider import LLMProvider
from app.api.routes.conversation import get_llm_provider
from app.db.base import get_db
from app.knowledge import service
from app.knowledge.schemas import (
    IngestDocumentIn,
    KnowledgeDocumentOut,
    KnowledgeQueryIn,
    KnowledgeQueryOut,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_embedding_provider() -> EmbeddingProvider:
    """Real provider by default. Tests override this dependency with a
    `HashingEmbeddingProvider` instance they control directly — the
    exact same `get_db` / `get_llm_provider` override pattern, so no
    test ever requires a downloaded model or network access."""
    return build_embedding_provider()


@router.post("/documents", response_model=KnowledgeDocumentOut, status_code=201)
def ingest_document(
    body: IngestDocumentIn,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> KnowledgeDocumentOut:
    try:
        document = service.ingest_document(db, embedding_provider, title=body.title, content=body.content)
    except service.EmptyDocumentError:
        raise HTTPException(status_code=422, detail="Document content produced no chunks")
    return service.to_document_out(document)


@router.get("/documents", response_model=list[KnowledgeDocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[KnowledgeDocumentOut]:
    return [service.to_document_out(d) for d in service.list_documents(db)]


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)) -> KnowledgeDocumentOut:
    try:
        document = service.get_document(db, document_id)
    except service.DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    return service.to_document_out(document)


@router.post("/query", response_model=KnowledgeQueryOut)
def query_knowledge_base(
    body: KnowledgeQueryIn,
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> KnowledgeQueryOut:
    return service.query_knowledge_base(
        db, llm_provider=llm_provider, embedding_provider=embedding_provider, question=body.question
    )
