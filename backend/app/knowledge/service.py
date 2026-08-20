"""
Knowledge-base orchestration (Phase 13). Ingestion: chunk -> embed ->
persist. Query: embed question -> retrieve top-k via cosine similarity
over persisted chunk embeddings -> generate a grounded answer ->
verify citations against real chunk ids.

Reuses the "propose vs. decide" split from every prior phase: the LLM
never gets to unilaterally declare an answer grounded (see
generation.py::verify_grounded_answer).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embedding_provider import EmbeddingProvider
from app.ai.provider import LLMProvider
from app.db.models import KnowledgeChunk, KnowledgeDocument
from app.knowledge.chunking import chunk_text
from app.knowledge.generation import generate_grounded_answer
from app.knowledge.retrieval import retrieve_top_k
from app.knowledge.schemas import CitationOut, KnowledgeDocumentOut, KnowledgeQueryOut


class KnowledgeServiceError(Exception):
    """Base class for knowledge-service errors the API layer translates
    into specific HTTP responses."""


class DocumentNotFoundError(KnowledgeServiceError):
    pass


class EmptyDocumentError(KnowledgeServiceError):
    """Raised when a document produces zero chunks (e.g. whitespace-only
    content) — nothing meaningful to persist or embed."""


def ingest_document(
    db: Session,
    embedding_provider: EmbeddingProvider,
    *,
    title: str,
    content: str,
) -> KnowledgeDocument:
    chunks = chunk_text(content)
    if not chunks:
        raise EmptyDocumentError(title)

    document = KnowledgeDocument(title=title, content=content)
    db.add(document)
    db.flush()  # assign document.id before creating chunk rows

    for chunk in chunks:
        embedding = embedding_provider.embed(chunk.text)
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=chunk.index,
                text=chunk.text,
                embedding=embedding,
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(document)
    return document


def list_documents(db: Session) -> list[KnowledgeDocument]:
    return list(db.execute(select(KnowledgeDocument)).scalars().all())


def get_document(db: Session, document_id: str) -> KnowledgeDocument:
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    return document


def to_document_out(document: KnowledgeDocument) -> KnowledgeDocumentOut:
    return KnowledgeDocumentOut(
        id=document.id,
        title=document.title,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
    )


def query_knowledge_base(
    db: Session,
    *,
    llm_provider: LLMProvider,
    embedding_provider: EmbeddingProvider,
    question: str,
) -> KnowledgeQueryOut:
    query_vector = embedding_provider.embed(question)

    rows = db.execute(
        select(
            KnowledgeChunk.id,
            KnowledgeChunk.document_id,
            KnowledgeDocument.title,
            KnowledgeChunk.text,
            KnowledgeChunk.embedding,
        ).join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
    ).all()

    candidates = [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    retrieved = retrieve_top_k(query_vector, candidates)

    result = generate_grounded_answer(llm_provider, question=question, retrieved_chunks=retrieved)

    return KnowledgeQueryOut(
        answer=result.answer,
        grounded=result.grounded,
        citations=[
            CitationOut(chunk_id=c.chunk_id, document_id=c.document_id, document_title=c.document_title)
            for c in retrieved
            if c.chunk_id in result.cited_chunk_ids
        ],
    )
