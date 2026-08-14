# PROJECT_PLAN.md

Full roadmap and status. See `PROJECT_STATE.md` for the live "what's next" snapshot — this file is the complete picture.

## Milestones

- **Milestone 1 — Technical Proof:** Scenario → AI Buyer → Conversation → Evidence → Evaluation → Readiness (Phases 0–9)
- **Milestone 2 — Product Proof:** + Root Cause → Coaching → Targeted Drill → Reassessment (Phases 10–12, 14)
- **Milestone 3 — Founder-Ready:** + RAG → Skill Intelligence → Manager View → Benchmarking → Security → Deployment → 2-minute demo (Phases 13, 15–26)

## Phase Status

| Phase | Name | Status | Checkpoint |
|---|---|---|---|
| 0 | Product Strategy | ✅ Done | PASSED |
| 1 | System Architecture | ✅ Done | PASSED |
| 2 | Data Model | ✅ Done | PASSED |
| 3 | Project Foundation | 🔄 In Progress | pending review |
| 4 | Core UX | Not started | — |
| 5 | Scenario Engine | Not started | — |
| 6 | Adaptive AI Buyer | Not started | — |
| 7 | Conversation Engine | Not started | — |
| 8 | Evaluation Engine | Not started | — |
| 9 | Readiness Engine | Not started | — |
| 10 | AI Coach | Not started | — |
| 11 | Targeted Drills | Not started | — |
| 12 | Adaptive Difficulty | Not started | — |
| 13 | Product RAG | Not started | — |
| 14 | Skill Graph | Not started | — |
| 15 | Stress Testing | Not started | — |
| 16 | Manager Intelligence | Not started | — |
| 17 | Voice | Not started | — |
| 18 | AI Evaluation Benchmark | Not started | — |
| 19 | Security | Not started | — |
| 20 | Cost Optimization | Not started | — |
| 21 | Deployment | Not started | — |
| 22 | Product Polish | Not started | — |
| 23 | Founder Demo | Not started | — |
| 24 | Documentation | Not started | — |
| 25 | CTO Review | Not started | — |
| 26 | Founder Outreach | Not started | — |

## Acceptance Criteria Per Completed/Active Phase

**Phase 0:** Target user, personas, JTBD, problem statement, MVP boundary via Scope Gate, differentiation, principles, metrics, demo strategy all defined; 7 output-rule questions answered.

**Phase 1:** Frontend/backend/module architecture, AI architecture (2-component split), data flow, state management, error handling, security boundaries defined; deterministic-readiness principle enforced at the module level.

**Phase 2:** MVP-scoped schema for every module; readiness thresholds normalized and queryable; evidence traceable to a real transcript line; no non-MVP tables introduced.

**Phase 3 (current):** Repo scaffolded; backend boots and serves real HTTP traffic; `/health` confirms DB connectivity; migrations apply cleanly and produce the exact Phase 2 schema; tests pass; frontend builds, type-checks, and its dev server successfully proxies to the live backend; CI workflow runs backend tests on push. Repo committed in 10 small units, tagged `v0.3-foundation`, packaged as a portable zip including git history. **Verification is done. Awaiting checkpoint sign-off.**
