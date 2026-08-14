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

## Status

Phase 3 — Project Foundation (see `PROJECT_STATE.md`). Core product loop (scenario → adaptive buyer → conversation → evidence → evaluation → readiness) is not yet implemented — that's Phases 4–9.
