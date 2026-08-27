# AI Sales Readiness Intelligence

An AI system that simulates realistic sales conversations against an adaptive buyer, evaluates rep behavior with cited evidence (not opaque scores), and determines readiness for a specific customer scenario through a deterministic rules engine — not an LLM's opinion.

This is not a chatbot demo and not a clone of any existing product. See `PHASE_0_PRODUCT_STRATEGY.md` for the full product reasoning and `ARCHITECTURE.md` for the technical design.

## Project memory

This repo is the project's source of truth across sessions — see `MASTER_PROMPT.md` for the full working agreement. Key files:

- `PROJECT_STATE.md` — current phase and exact next action
- `PROJECT_PLAN.md` — all 26 phases and status
- `ARCHITECTURE.md` / `DATA_MODEL.md` — system design
- `DECISIONS.md` — why things were built the way they were
- `CHANGELOG.md` / `TEST_STATUS.md` / `KNOWN_ISSUES.md` / `AI_EVALUATION.md`

## Running locally

**Backend**
```bash
cd backend
pip install -r requirements.txt --break-system-packages
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api/*` to `http://127.0.0.1:8000`.

> **Note:** `backend/.env.example` should always ship with `LLM_API_KEY=` empty. Never commit a real key — copy `.env.example` to `.env` and put your own key there instead.

## API overview

All routes are served from `app.main:app`. Full request/response shapes are in each router's Pydantic schemas; this is just the map.

| Area | Routes |
|---|---|
| Health | `GET /health` |
| Scenarios | `GET /scenarios`, `GET /scenarios/{id}` |
| Conversations | `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/turns`, `POST /conversations/{id}/close` |
| Evaluation | `POST /conversations/{id}/evaluate`, `GET /conversations/{id}/evaluation` |
| Readiness | `POST /conversations/{id}/readiness`, `GET /conversations/{id}/readiness`, `GET /conversations/{id}/result` |
| Coaching | `POST /conversations/{id}/coaching`, `GET /conversations/{id}/coaching` |
| Drills | `POST /conversations/{id}/drill`, `GET /conversations/{id}/drill` |
| Adaptive difficulty | `GET /conversations/{id}/difficulty-recommendation` |
| Product RAG | `POST /knowledge/documents`, `GET /knowledge/documents`, `GET /knowledge/documents/{id}`, `POST /knowledge/query` |
| Skill graph / root cause | `GET /conversations/{id}/root-cause-analysis` |

Most write-triggering routes (`evaluate`, `readiness`, `coaching`, `drill`) require the prior phase's step to already exist and return `409` if it doesn't — nothing lazily triggers an upstream computation. The frontend currently only drives Scenarios, Conversations, and Result/Readiness; Coaching, Drills, Adaptive Difficulty, and RAG are API-only so far.

## Status

**Phase 14 of 26** — Skill Graph (competency dependency graph + deterministic root-cause analysis), built and tested, awaiting checkpoint sign-off. See `PROJECT_STATE.md` for the exact next action and `PROJECT_PLAN.md` for the full 26-phase roadmap and per-phase acceptance criteria.

**Completed (Phases 0–13, all checkpoint-approved):**
- Product strategy, architecture, and data model (0–2)
- Real backend + frontend scaffolding, CI, migrations (3)
- Core UX shell with a typed contract for real data (4)
- The core product loop — scenario → adaptive AI buyer → multi-turn conversation → cited evidence → deterministic evaluation → deterministic readiness verdict (5–9)
- AI Coach, targeted drills, and adaptive difficulty recommendations built on top of the readiness engine (10–12)
- Product-knowledge RAG with grounded, citation-verified answers (13)

**In progress (Phase 14):** a small, deterministic, zero-LLM competency dependency graph that surfaces correlated (never causal) within-conversation weaknesses — e.g. a failed Closing score alongside a failed Discovery score gets flagged as a possible contributing factor, quoting Discovery's own already-verified diagnosis as evidence.

**Known scope gaps** (see `PROJECT_STATE.md` / `KNOWN_ISSUES.md` for the full, current list):
- Phase 14 is a *within-conversation* skill graph, not the longitudinal cross-conversation "Sales DNA" profile from the original product vision — that's deferred as Phase 14b.
- Coaching, drills, adaptive difficulty, and RAG have no frontend yet (API-only).
- Single-tenant, single seeded scenario, no real auth — all intentional MVP boundaries, not oversights.
- `AnthropicProvider` and `SentenceTransformerEmbeddingProvider` are implemented but have never been exercised against a real network call in this environment; every test suite runs LLM-touching modules through their deterministic degrade path with zero API key / zero network access.
