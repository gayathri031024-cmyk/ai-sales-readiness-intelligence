"""
API schemas for the knowledge module. Same reasoning as every other
module's schemas.py: separate from the ORM, structurally excludes
anything internal — raw embedding vectors and full chunk text never
appear in any response here, by construction.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IngestDocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    chunk_count: int
    created_at: datetime


class KnowledgeQueryIn(BaseModel):
    question: str = Field(min_length=1)


class CitationOut(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str


class KnowledgeQueryOut(BaseModel):
    answer: str
    grounded: bool
    citations: list[CitationOut]
