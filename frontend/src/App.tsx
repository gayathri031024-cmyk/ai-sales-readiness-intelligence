import { useEffect, useState } from "react";
import type { ReadinessResult, Scenario } from "./types";
import { fetchMvpScenario } from "./api/scenario";
import { getConversationResult } from "./api/readiness";
import { StartScenario } from "./screens/StartScenario";
import { Conversation } from "./screens/Conversation";
import { Result } from "./screens/Result";

type Screen = "start" | "conversation" | "result";

/**
 * Phase 5 (Scenario Engine): scenario data is real. Phase 7 (Conversation
 * Engine): the Conversation screen drives a real multi-turn conversation.
 * Phase 9 (Readiness Engine): Result now consumes real evaluation +
 * readiness data too — src/api/readiness.ts sequences Phase 8's
 * (idempotent) evaluation trigger and Phase 9's combined result fetch, since
 * the backend `readiness/` module deliberately never triggers evaluation
 * itself (see backend ARCHITECTURE.md §3). The point of Phase 4's typed
 * contract was exactly this: swapping each screen's data source one phase
 * at a time without a UI rewrite — App.tsx's interface with the screen
 * components barely changed across five phases of real backend behind them.
 */
function App() {
  const [screen, setScreen] = useState<Screen>("start");
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [result, setResult] = useState<ReadinessResult | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchMvpScenario()
      .then((s) => {
        if (!cancelled) setScenario(s);
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    setResult(null);
    setResultError(null);
    getConversationResult(conversationId)
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((err: Error) => {
        if (!cancelled) setResultError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  function restart() {
    setConversationId(null);
    setResult(null);
    setResultError(null);
    setScreen("start");
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-4 text-ink">
        <div className="max-w-md text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-amber">Couldn't load scenario</p>
          <p className="mt-3 text-sm text-ink-muted">{loadError}</p>
          <p className="mt-3 text-xs text-ink-faint">Is the backend running at the proxied /api target?</p>
        </div>
      </main>
    );
  }

  if (!scenario) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg text-ink-faint">
        <p className="font-mono text-xs uppercase tracking-widest">Loading scenario…</p>
      </main>
    );
  }

  if (screen === "start") {
    return <StartScenario scenario={scenario} onBegin={() => setScreen("conversation")} />;
  }

  if (screen === "conversation") {
    return (
      <Conversation
        scenario={scenario}
        onComplete={(id) => {
          setConversationId(id);
          setScreen("result");
        }}
      />
    );
  }

  if (resultError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-4 text-ink">
        <div className="max-w-md text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-amber">Couldn't load your evaluation</p>
          <p className="mt-3 text-sm text-ink-muted">{resultError}</p>
        </div>
      </main>
    );
  }

  if (!result) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg text-ink-faint">
        <p className="font-mono text-xs uppercase tracking-widest">Evaluating your conversation…</p>
      </main>
    );
  }

  return <Result result={result} onRestart={restart} />;
}

export default App;
