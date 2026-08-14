// MOCK — Phase 4 (Core UX) only. Replaced by a real GET /scenarios call
// once Phase 5 (Scenario Engine) exists. This is the single MVP scenario
// defined in PHASE_0_PRODUCT_STRATEGY.md.

import type { Scenario } from "../types";

export const mockScenario: Scenario = {
  id: "scenario-mock-1",
  title: "Enterprise CFO — Price Objection",
  buyerPersona: {
    id: "persona-mock-cfo",
    name: "Enterprise CFO",
    description:
      "High sophistication. Primary concern is ROI and budget-cycle risk. Will raise a pricing objection early and push back on vague answers.",
  },
  productContext: "AI-powered CRM platform, positioned against Salesforce for a 400-seat enterprise deal.",
  knownObjection: "Price — currently evaluating a cheaper competitor.",
  difficulty: "standard",
  maxTurns: 12,
};
