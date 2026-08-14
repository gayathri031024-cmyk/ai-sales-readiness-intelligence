# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 4 — Core UX
**Current Checkpoint:** Phase 4 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED)

**Current Objective:** Get sign-off that the core 3-screen UX (Start Scenario → Conversation → Result) is right — interaction design and visual direction — before wiring in real backend logic starting Phase 5.

**Completed Work:**
- Phases 0–3 approved (see CHANGELOG.md for detail)
- Phase 4 Core UX built and verified:
  - 3 screens: StartScenario, Conversation, Result — all real React/TS components, not mockups
  - Visual direction: dark "briefing room" theme, Space Grotesk/Inter/JetBrains Mono, amber accent
  - Signature element: EvidenceChip, reused consistently to make "every score has evidence" visually unmistakable
  - Typed contract (`types.ts`) so mock data (Phase 4) and real API responses (Phase 5+) are interchangeable without a UI rewrite
  - Found and fixed a turn-indexing bug between mock conversation and mock evidence before it shipped
  - Verified with real screenshots (Playwright against the built app), not just "it compiles"

**In Progress:** Awaiting review of Phase 4 UX/design.

**Next Action:** User reviews the screens (screenshots + repo), then says `CHECKPOINT PASSED` to begin Phase 5 — Scenario Engine (first phase where scenario data becomes real instead of mocked).

**Known P0:** None.
**Known P1:** None.
**Known P2:** Conversation end-condition thresholds (turn limit / patience threshold / explicit close) not yet concretely specified — deferred to Phase 5/6.
**Known P3:** `buyer_state_history` unbounded growth (Phase 20/21). Dev-mode auto schema creation needs an explicit production guard (Phase 21). Mock data in `src/mock/` must be fully removed once Phases 5/6/8/9 provide real equivalents — tracked so it doesn't quietly linger.
**Technical Debt:** Mock layer (`src/mock/`) is temporary by design — explicitly marked, tracked above.
**Last Successful Test:** `pytest -v` (backend) — 2 passed. `npm run build` (frontend) — clean, 0 type errors.
**Current Blockers:** Waiting on Phase 4 approval.
