# AI Sales Readiness Intelligence

An AI system that simulates realistic sales conversations against an adaptive buyer, evaluates rep behavior against cited transcript evidence (not opaque scores), and determines readiness for a specific customer scenario through a deterministic rules engine — not an LLM's opinion.

This is not a chatbot demo. The core design principle, enforced throughout the codebase: **LLMs propose, deterministic code decides.** Every scoring, readiness, coaching-priority, drill, difficulty, and root-cause decision is pure Python with no LLM in the loop; LLMs are used only where judgment on open text is genuinely required (classifying rep behavior, extracting evidence candidates, generating a coaching narrative), and every LLM claim is independently verified against real, persisted data before it's trusted.

See `PHASE_0_PRODUCT_STRATEGY.md` for the full product reasoning and `ARCHITECTURE.md` for the technical design.

## Status

**Phases 0–13 complete and checkpointed. Phase 14 (Skill Graph / root-cause analysis) is built and fully tested but not yet checkpoint-approved.** See `PROJECT_STATE.md` for the authoritative, up-to-the-minute status and `PROJECT_PLAN.md` for the full 26-phase roadmap.

What's live end-to-end today:

- **Scenario Engine** — one seeded MVP scenario (persona, product context, objection, difficulty, competency thresholds)
- **Adaptive AI Buyer** — LLM-classified rep behavior drives a deterministic hidden-state machine (trust/patience/budget sensitivity/interest); buyer replies never leak that state
- **Conversation Engine** — persistent multi-turn conversations with turn limits, patience exhaustion, and explicit close
- **Evaluation Engine** — evidence-grounded scoring across 3 competencies (Discovery, Objection Handling, Closing); every score traces to a real, verified line in the transcript
- **Readiness Engine** — deterministic READY / AT_RISK / NOT_READY verdict against scenario-specific thresholds
- **AI Coach** — a focused coaching narrative, grounded only in already-verified evidence, that never overrides the deterministic priority pick
- **Targeted Drills** — a practice assignment built from the coaching output
- **Adaptive Difficulty** — a recommendation to step up, hold, or step down scenario difficulty
- **Product RAG** — a small grounded-answer knowledge base (in-process retrieval, no external vector DB) that refuses to answer beyond what it actually retrieved
- **Skill Graph / Root-Cause Analysis** *(Phase 14, pending sign-off)* — surfaces correlated within-conversation weaknesses via a small hand-authored competency dependency graph; deliberately hedged language, never claims causation

**Backend: 259 automated tests, all passing.** Frontend type-checks clean but only 3 screens exist (Start Scenario, Conversation, Result) — Coaching, Drills, Difficulty, and Root-Cause are API-only with no UI yet (see `KNOWN_ISSUES.md`). **No one has visually verified the running frontend in a browser yet** — that's the single biggest gap between "the code is correct" and "this is a finished demo." Do that before trusting any screenshot-shaped claim about the UI.

## Project memory

This repo is its own source of truth across work sessions — see `MASTER_PROMPT.md` for the full working agreement. Key files:

- `PROJECT_STATE.md` — current phase and exact next action
- `PROJECT_PLAN.md` — all 26 phases and status, with acceptance criteria per phase
- `ARCHITECTURE.md` / `DATA_MODEL.md` — system design
- `DECISIONS.md` — why things were built the way they were, including every judgment call
- `KNOWN_ISSUES.md` — everything still open, classified P0–P3
- `TEST_STATUS.md` — test history

## Running locally

**Backend**
```bash
cd backend
pip install -r requirements.txt --break-system-packages
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The app runs with zero external dependencies out of the box: SQLite, no API key required. Every AI-touching module degrades gracefully (deterministic fallback) when `LLM_API_KEY` is unset — none of the 259 backend tests call a real LLM API.

To exercise the real AI buyer / coach / RAG generation, put a real Anthropic key in `backend/.env` (**never** commit `.env` — only `.env.example`, which should always hold a placeholder, not a real key).

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api/*` to `http://127.0.0.1:8000`. Open the printed local URL and walk through **Start → Conversation → Result**.

**Tests**
```bash
cd backend
python -m pytest -q
```

## API surface

All routes are prefixed and versioned per `app/main.py`; see the live OpenAPI schema at `/docs` once the backend is running for the exact request/response shapes.

| Area | Routes |
|---|---|
| Scenarios | `GET /scenarios`, `GET /scenarios/{id}` |
| Conversations | `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/turns`, `POST /conversations/{id}/close` |
| Evaluation | `POST`/`GET /conversations/{id}/evaluation` (evaluate / fetch) |
| Readiness | `POST`/`GET /conversations/{id}/readiness`, `GET /conversations/{id}/result` |
| Coaching | `POST`/`GET /conversations/{id}/coaching` |
| Drills | `POST`/`GET /conversations/{id}/drill` |
| Difficulty | `GET /conversations/{id}/difficulty-recommendation` |
| Root-cause | `GET /conversations/{id}/root-cause-analysis` |
| Knowledge (RAG) | `POST`/`GET /knowledge/documents`, `GET /knowledge/documents/{id}`, `POST /knowledge/query` |
| Health | `GET /health` |

## Known limitations

The full, honest list — including every deliberately deferred feature and why — lives in `KNOWN_ISSUES.md`. The headline items:

- Coaching, Drills, Difficulty, and Root-Cause exist only as tested API endpoints — no frontend screens yet.
- Single-tenant, single-scenario MVP: no scenario library, no multi-user auth, no per-org data scoping.
- The "reassessment" step of the training loop (auto-linking a fresh practice conversation back to the drill it came from) is not implemented.
- Root-cause analysis covers only the 3 MVP-seeded competencies, not the full 7 named in the product vision.
