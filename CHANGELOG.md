# CHANGELOG.md

## Phase 0 — Product Strategy
- Defined target user, buyer/salesperson personas, JTBD, problem statement, core user journey
- Applied Product Scope Gate: classified all roadmap features into MUST HAVE / SHOULD HAVE / LATER / DO NOT BUILD
- Defined MVP boundary: single persona (Enterprise CFO), 3 competencies (Discovery, Objection Handling, Closing), no RAG/coaching/drills/manager view/voice
- Identified assumptions to validate: state leakage, evidence hallucination, scoring consistency
- **Checkpoint: PASSED**

## Phase 1 — System Architecture
- Defined modular monolith architecture (frontend, backend module boundaries, DB)
- Split AI architecture into two components: LangGraph conversation graph + plain sequential evaluation pipeline
- Made readiness engine deterministic (no LLM call) — enforced at module boundary
- Made buyer state updates deterministic given LLM-classified rep behavior
- Made buyer hidden-state exclusion from API responses an architectural (serializer-level) guarantee
- Defined data flow, error handling/retry strategy, MVP-scoped security boundaries, placeholder deployment target
- Explicitly deferred: RAG, full skill graph, manager dashboard, coaching/drills, voice, multi-tenant security
- **Checkpoint: PASSED**

## Phase 2 — Data Model
- Designed MVP-scoped schema: users, buyer_personas, scenarios, scenario_competency_thresholds, competencies, conversations, messages, buyer_state_history, evaluations, evidence, readiness_results
- Normalized readiness thresholds into their own table instead of jsonb, so the deterministic readiness engine can query them directly
- Tied evidence to actual `messages` rows via foreign key, so evidence can never reference a quote that wasn't actually said
- Added `buyer_state_history` as an append-only debug log to test the Phase 0 state-leakage/consistency assumptions
- Explicitly deferred: organizations, products catalog, knowledge_documents, coaching_sessions, drills, reassessments, skill_graph_edges, manager_rollups
- **Checkpoint: PASSED**

## Phase 3 — Project Foundation
- Scaffolded backend: FastAPI app, module skeleton (`scenario/`, `buyer/`, `conversation/`, `evaluation/`, `readiness/`, `ai/`) with future-phase docstrings, config via pydantic-settings, logging setup
- Implemented all 11 SQLAlchemy models from `DATA_MODEL.md`; Alembic autogenerate detected every table correctly on first run; migration verified against a live SQLite DB
- Added `/health` endpoint that actively checks DB connectivity, not just app liveness
- Verified the backend for real: booted `uvicorn` and hit it with `curl` (not just the test client)
- Scaffolded frontend: Vite + React + TypeScript + Tailwind v4; placeholder health-check page only — real screens deliberately deferred to Phase 4
- Verified end-to-end: frontend dev server's `/api` proxy successfully reached the live backend process
- Added CI (GitHub Actions) to run backend tests on push
- Moved all project-memory docs into the repo root, added `PROJECT_PLAN.md`, `KNOWN_ISSUES.md`, `TEST_STATUS.md`, `AI_EVALUATION.md`
- **Checkpoint: PASSED**

## Phase 4 — Core UX
- Built all 3 MVP screens: Start Scenario (briefing), Conversation (live roleplay), Result (evidence-based debrief)
- Established a "briefing room / instrument panel" visual direction (dark theme, amber accent, Space Grotesk + Inter + JetBrains Mono) — deliberately avoided the generic AI-tool default looks
- Built the Evidence Chip as the product's signature UI element, reused consistently across every competency card
- Wired screens together with mock data (`src/mock/`, explicitly marked, typed against `types.ts` so Phases 5–9 swap in real data without a UI rewrite)
- Found and fixed a turn-indexing off-by-one between the mock conversation and mock evidence citations before it could ship as a subtle inconsistency
- Verified visually: built the production bundle, served it, and used Playwright to screenshot and inspect all 3 screens plus the interactive flow between them
- **Checkpoint: pending review**
