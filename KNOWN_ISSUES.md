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

## Resolved

None yet.
