// MOCK — Phase 4 (Core UX) only. Hand-authored to exercise every piece of
// the Result screen's UI (evidence citations, per-competency thresholds,
// a NOT_READY verdict). Replaced by the real evidence-extraction pipeline
// (Phase 8) and deterministic readiness engine (Phase 9). The turnIndex
// values here correspond to messages in mock/buyer.ts's canned exchange.

import type { ReadinessResult } from "../types";

export const mockReadinessResult: ReadinessResult = {
  verdict: "NOT_READY",
  reasoning: "Objection Handling scored 57, below the required minimum of 70 for this scenario.",
  evaluations: [
    {
      competencyKey: "discovery",
      displayName: "Discovery",
      score: 82,
      requiredMinScore: 70,
      diagnosis: "Rep asked follow-up questions about cost structure and team size before pitching.",
      impact: "Enough context was gathered to tailor the pitch, though pain wasn't fully quantified.",
      recommendation: "Ask what the cost of staying on the current tool actually is, in dollars.",
      evidence: [
        {
          turnIndex: 3,
          sender: "buyer",
          quote: "I still need to understand the total cost over three years, not just year one.",
          note: "Buyer signaled a cost-framing concern the rep could have probed further.",
        },
      ],
    },
    {
      competencyKey: "objection_handling",
      displayName: "Objection Handling",
      score: 57,
      requiredMinScore: 70,
      diagnosis: "Rep responded to the price objection with a feature list instead of a diagnostic question.",
      impact: "Value was not established before the price conversation continued.",
      recommendation: "Ask what's driving the price sensitivity before defending the price.",
      evidence: [
        {
          turnIndex: 1,
          sender: "buyer",
          quote: "your competitor quoted us about 30% less for a similar seat count. Why should I pay more?",
          note: "Opening objection — the critical moment for this competency.",
        },
      ],
    },
    {
      competencyKey: "closing",
      displayName: "Closing",
      score: 0,
      requiredMinScore: 65,
      diagnosis: "Conversation ended before a close was attempted.",
      impact: "No evidence available — competency not exercised in this conversation.",
      recommendation: "Not enough signal yet. This will improve once Objection Handling is addressed.",
      evidence: [],
    },
  ],
};
