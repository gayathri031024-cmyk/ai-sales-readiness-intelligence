// Phase 9 (Readiness Engine): real evaluation + readiness data, replacing
// src/mock/readiness.ts. Same adapter pattern as src/api/scenario.ts and
// src/api/conversation.ts — snake_case wire format -> camelCase types.
//
// Note: the existing `Evidence` type carries a `sender` field the backend
// no longer needs to send — Phase 8's verification.py structurally
// guarantees every persisted piece of evidence is a REP line (evidence
// attributed to the buyer is deterministically rejected before it's ever
// persisted, see backend DECISIONS.md, Phase 8) — so it's hardcoded to
// "rep" here rather than added to the wire format for a value that can
// only ever be one thing.

import type { CompetencyEvaluation, CompetencyKey, Evidence, ReadinessResult, ReadinessVerdict } from "../types";

interface EvidenceApi {
  id: string;
  message_id: string;
  turn_index: number;
  quote: string;
  note: string | null;
}

interface EvaluationApi {
  id: string;
  competency_key: string;
  display_name: string;
  score: number;
  required_min_score: number;
  diagnosis: string;
  impact: string;
  recommendation: string;
  created_at: string;
  evidence: EvidenceApi[];
}

interface ConversationResultApi {
  conversation_id: string;
  verdict: string;
  reasoning: string;
  computed_at: string;
  evaluations: EvaluationApi[];
}

function adaptEvidence(api: EvidenceApi): Evidence {
  return {
    turnIndex: api.turn_index,
    sender: "rep",
    quote: api.quote,
    note: api.note ?? "",
  };
}

function adaptEvaluation(api: EvaluationApi): CompetencyEvaluation {
  return {
    competencyKey: api.competency_key as CompetencyKey,
    displayName: api.display_name,
    score: api.score,
    requiredMinScore: api.required_min_score,
    diagnosis: api.diagnosis,
    impact: api.impact,
    recommendation: api.recommendation,
    evidence: api.evidence.map(adaptEvidence),
  };
}

function adaptResult(api: ConversationResultApi): ReadinessResult {
  return {
    verdict: api.verdict as ReadinessVerdict,
    reasoning: api.reasoning,
    evaluations: api.evaluations.map(adaptEvaluation),
  };
}

async function parseOrThrow(response: Response): Promise<ConversationResultApi> {
  if (!response.ok) {
    // Never surface raw response bodies (could contain framework detail);
    // a status-coded message is enough for the UI to react to.
    if (response.status === 404) throw new Error("This conversation hasn't been evaluated yet.");
    if (response.status === 409) throw new Error("This conversation hasn't ended yet.");
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as ConversationResultApi;
}

/**
 * Runs the full post-conversation pipeline for a just-closed conversation:
 * Phase 8's evaluation step (idempotent — safe to call even if it already
 * ran) followed by Phase 9's combined result fetch (which itself lazily
 * computes and persists the readiness verdict if it hasn't been yet).
 * Two calls because `readiness/`'s own module boundary forbids it from
 * ever triggering evaluation itself (see backend ARCHITECTURE.md §3) —
 * the frontend is what sequences them, the same way a human would.
 */
export async function getConversationResult(conversationId: string): Promise<ReadinessResult> {
  const evaluateResponse = await fetch(`/api/conversations/${conversationId}/evaluate`, { method: "POST" });
  if (!evaluateResponse.ok) {
    if (evaluateResponse.status === 409) throw new Error("This conversation hasn't ended yet.");
    throw new Error(`Request failed (${evaluateResponse.status})`);
  }

  const resultResponse = await fetch(`/api/conversations/${conversationId}/result`);
  return adaptResult(await parseOrThrow(resultResponse));
}
