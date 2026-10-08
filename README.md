## Live Demo

[**Try AI Sales Readiness Intelligence →**](https://ai-sales-readiness-intelligence.vercel.app/)

# AI Sales Readiness Intelligence

**Evidence-based AI sales simulation and readiness evaluation platform.**

Simulates realistic sales conversations with an adaptive AI buyer, evaluates representative behavior using cited evidence, and determines readiness through a **deterministic evaluation and rules engine** rather than relying on an opaque LLM score.

**Live Demo:** [https://ai-sales-readiness-intelligence.vercel.app/](https://ai-sales-readiness-intelligence.vercel.app/)

**Stack:** React · TypeScript · FastAPI · PostgreSQL · LangGraph · Anthropic Claude · Alembic

---

## Why I Built This

Most AI sales-training systems can generate a conversation or produce a score, but a score alone does not explain **why** someone is or isn't ready.

This project focuses on an evidence-based evaluation pipeline:

```
Scenario
   ↓
Adaptive AI Buyer
   ↓
Sales Conversation
   ↓
Evidence Extraction
   ↓
Competency Evaluation
   ↓
Deterministic Readiness Engine
   ↓
Readiness Decision
   ↓
Coaching / Targeted Practice

```

The key design principle is that the LLM can help interpret the conversation, but the final readiness decision is produced by deterministic business logic operating on evaluated evidence.

---

## Key Features

### 🤝 Adaptive AI Buyer

Conducts multi-turn sales conversations within a defined customer and product scenario.

### 🔎 Evidence-Based Evaluation

Extracts and evaluates representative behavior using cited conversation evidence instead of relying on an unexplained overall score.

### 🎯 Deterministic Readiness Engine

Transforms evaluated competencies and evidence into an explicit readiness decision using deterministic rules.

### 🧠 AI Coaching

Produces targeted coaching based on identified competency weaknesses and previously evaluated evidence.

### 🏋️ Targeted Drills

Creates focused practice opportunities based on identified skill gaps.

### 📈 Adaptive Difficulty

Provides recommendations for adjusting practice difficulty based on evaluation results.

### 📚 Product Knowledge RAG

Supports product-knowledge queries with grounded answers and citation verification.

### 🕸️ Skill Graph & Root-Cause Analysis

Uses a deterministic competency dependency graph to surface correlated weaknesses within a conversation without claiming causal relationships.

---

## Architecture

[Architecture](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/docs/architecture.svg) ([image](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/raw/master/docs/architecture.svg))

---

## Technical Stack

| **Layer**        | **Technology**    |
| ---------------- | ----------------- |
| Frontend         | React, TypeScript |
| Backend          | Python, FastAPI   |
| Database         | PostgreSQL        |
| AI Orchestration | LangGraph         |
| LLM              | Anthropic Claude  |
| Migrations       | Alembic           |
| Validation       | Pydantic          |
| Testing          | pytest            |
| CI               | GitHub Actions    |

---

## Engineering Highlights

- Separated **LLM-based interpretation** from deterministic evaluation and readiness logic.
- Designed an explicit multi-stage pipeline from scenario → conversation → evidence → evaluation → readiness.
- Added dependency checks between pipeline stages instead of silently triggering missing computations.
- Implemented grounded product-knowledge RAG with citation verification.
- Added deterministic competency dependency analysis for correlated weaknesses.
- Built backend and frontend as separate application layers.
- Added automated testing and CI.
- Uses database migrations through Alembic.

---

## API

The FastAPI backend exposes endpoints for:

- Scenarios
- Conversations
- Evaluation
- Readiness
- Coaching
- Drills
- Adaptive difficulty
- Product-knowledge RAG
- Skill graph / root-cause analysis

Example:

```
GET  /health
GET  /scenarios

POST /conversations
POST /conversations/{id}/turns
POST /conversations/{id}/evaluate
POST /conversations/{id}/readiness

POST /conversations/{id}/coaching
POST /conversations/{id}/drill

POST /knowledge/documents
POST /knowledge/query

GET  /conversations/{id}/root-cause-analysis

```

For complete request/response schemas, see the Pydantic models and backend routers.

---

## Running Locally

### Backend

```
cd backend
pip install -r requirements.txt --break-system-packages
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```
cd frontend
npm install
npm run dev
```

The frontend development server proxies `/api/*` to the local FastAPI backend.

### Environment Variables

Copy the example environment file and provide your own credentials:

```
cp backend/.env.example backend/.env
```

Never commit real API keys or secrets.

---

## Testing

Run the backend test suite using the repository's configured pytest commands.

**259 backend tests passing** — if this is still the current verified test count.

The test environment also supports deterministic degradation paths for LLM-dependent components so the core system can be tested without requiring live API calls.

---

## Current Status

**Phase 14 of 26 — Skill Graph & Deterministic Root-Cause Analysis**

Completed functionality includes:

- Product strategy and architecture
- Backend/frontend foundation
- Database migrations
- Scenario management
- Adaptive AI buyer
- Multi-turn conversations
- Evidence extraction
- Deterministic evaluation
- Deterministic readiness
- AI coaching
- Targeted drills
- Adaptive difficulty recommendations
- Product-knowledge RAG
- Competency dependency graph

---

## Current Scope

The current implementation intentionally has several MVP boundaries:

- The skill graph currently operates within a conversation.
- Longitudinal cross-conversation "Sales DNA" functionality is deferred.
- Coaching, drills, adaptive difficulty, and RAG are currently API-first and do not yet have complete frontend workflows.
- The application is currently single-tenant.
- The current MVP uses a seeded scenario.
- Real authentication is not yet implemented.

These are documented product-scope decisions rather than hidden limitations.

---

## Project Documentation

For deeper technical details:

- [`ARCHITECTURE.md`](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/ARCHITECTURE.md)
- [`DATA_MODEL.md`](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/DATA_MODEL.md)
- [`DECISIONS.md`](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/DECISIONS.md)
- [`TEST_STATUS.md`](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/TEST_STATUS.md)
- [`KNOWN_ISSUES.md`](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/KNOWN_ISSUES.md)
- [`PROJECT_PLAN.md`](https://github.com/gayathri031024-cmyk/ai-sales-readiness-intelligence/blob/master/PROJECT_PLAN.md)

---

## Live Demo

**Try the application:** [https://ai-sales-readiness-intelligence.vercel.app/](https://ai-sales-readiness-intelligence.vercel.app/)

---
