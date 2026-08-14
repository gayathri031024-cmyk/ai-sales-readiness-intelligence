# KNOWN_ISSUES.md

Classify: P0 — Critical | P1 — Important | P2 — Improvement | P3 — Optional
Remove an issue only after it's actually fixed and verified — don't just delete it because a phase ended.

## Open

**P2 — Conversation end-condition thresholds undefined**
Turn limit / patience threshold / explicit-close logic is referenced in the architecture but no concrete values exist yet.
Origin: Phase 1. Owner: Phase 5/6.

**P3 — `buyer_state_history` grows unbounded per conversation**
Fine at prototype scale; needs a retention/pruning policy before real deployment.
Origin: Phase 2. Owner: Phase 20/21.

**P3 — Dev-mode auto schema creation (`Base.metadata.create_all`) bypasses Alembic**
Convenient for local Phase 3 verification, but means dev and migration-managed schemas could silently drift if models change without a new migration. Acceptable now; must be removed or guarded more strictly before Phase 21 (production relies exclusively on Alembic per `main.py` comment).
Origin: Phase 3. Owner: Phase 21.

**P3 — MVP scenario seed data rides the same dev-only lifespan guard as schema auto-creation**
`seed_mvp_scenario()` is idempotent and correct for a single hardcoded MVP scenario, but is not how seeding should work once real scenario authoring exists — no proper seed migration path exists yet. Same bucket/owner as the item above; `seed_mvp_scenario()` is isolated in `scenario/service.py` specifically so a real Phase 21 migration can call it without touching its logic.
Origin: Phase 5. Owner: Phase 21.

**P2 — Phase 5 frontend integration not visually verified end-to-end in this environment**
Backend contract is covered by 5 passing tests plus one successful manual `curl` against a live server; frontend build type-checks clean against that exact contract. But unlike Phase 3/4, no Playwright screenshot of the real Start Scenario screen rendering live backend data exists — background dev processes were repeatedly reclaimed by the sandbox before a screenshot could be taken. Needs one manual local verification pass (`uvicorn` + `npm run dev`, look at the browser) before treating Phase 5 as fully verified to the project's own established bar.
Origin: Phase 5. Owner: you, before `CHECKPOINT PASSED`.

## Resolved

None yet.
