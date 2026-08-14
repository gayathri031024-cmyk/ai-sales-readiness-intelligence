# AI_EVALUATION.md

No AI component exists yet — the buyer (Phase 6) and evaluator (Phase 8) are the first LLM-backed pieces of the system. This file stays a template until then.

## Methodology (to be populated starting Phase 6)

Will cover: benchmark scenario set, expected vs. observed outputs, scoring consistency across repeated runs, hallucination checks, structured-output validity rate, prompt injection resistance (rep trying to extract buyer hidden state), RAG accuracy (once Phase 13 exists), readiness-decision correctness against hand-labeled cases.

## Phase 0 Assumptions to Validate (carried forward — not yet tested, no AI exists to test)

1. The LLM can maintain hidden buyer state across a conversation without leaking it.
2. Structured-output evidence extraction stays faithful to the actual transcript (no hallucinated quotes) — the `evidence.message_id` foreign key (Phase 2) is the mechanism that will make this testable.
3. A small, fixed rubric produces reasonably consistent scores across repeated runs of the same transcript.
4. Deterministic thresholds feel legible and fair to a human reviewing the readiness verdict.

## Test Scenarios

*(none yet — first entries land in Phase 6/8)*

## Known AI Failures

*(none yet)*
