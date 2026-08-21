// Phase 5: real scenario data, replacing src/mock/scenario.ts (now deleted).
// Adapter layer: the backend returns snake_case (Python/Pydantic
// convention); the frontend's typed contract (types.ts) is camelCase.
// Keeping that translation here, in one place, means the rest of the
// frontend never has to think about the wire format.

import type { BuyerPersona, Difficulty, Scenario } from "../types";

interface BuyerPersonaApi {
  id: string;
  name: string;
  description: string;
}

interface ScenarioApi {
  id: string;
  title: string;
  buyer_persona: BuyerPersonaApi;
  product_context: string;
  known_objection: string;
  difficulty: string;
  max_turns: number;
}

function adaptBuyerPersona(api: BuyerPersonaApi): BuyerPersona {
  return { id: api.id, name: api.name, description: api.description };
}

function adaptScenario(api: ScenarioApi): Scenario {
  return {
    id: api.id,
    title: api.title,
    buyerPersona: adaptBuyerPersona(api.buyer_persona),
    productContext: api.product_context,
    knownObjection: api.known_objection,
    difficulty: api.difficulty as Difficulty,
    maxTurns: api.max_turns,
  };
}

/**
 * MVP: exactly one scenario exists (see PHASE_0_PRODUCT_STRATEGY.md §7 —
 * scenario-authoring / a real picker is explicitly out of scope). This
 * fetches the list and returns the first entry rather than hardcoding an
 * id, so it keeps working unchanged if a second scenario is ever seeded.
 */
export async function fetchMvpScenario(): Promise<Scenario> {
  const response = await fetch("/api/scenarios");
  if (!response.ok) {
    throw new Error(`Failed to load scenario (${response.status})`);
  }

  const scenarios = (await response.json()) as ScenarioApi[];
  if (scenarios.length === 0) {
    throw new Error("No scenario available — has the backend seeded its MVP scenario?");
  }

  return adaptScenario(scenarios[0]);
}
