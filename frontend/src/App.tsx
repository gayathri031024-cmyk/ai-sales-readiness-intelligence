import { useEffect, useState } from "react";
import type { Scenario, TranscriptMessage } from "./types";
import { fetchMvpScenario } from "./api/scenario";
import { mockReadinessResult } from "./mock/readiness";
import { StartScenario } from "./screens/StartScenario";
import { Conversation } from "./screens/Conversation";
import { Result } from "./screens/Result";

type Screen = "start" | "conversation" | "result";

/**
 * Phase 5 (Scenario Engine): scenario data is real, fetched from the
 * backend (see src/api/scenario.ts). Phase 7 (Conversation Engine): the
 * Conversation screen now drives a real multi-turn conversation via
 * src/api/conversation.ts instead of mock canned replies — see
 * screens/Conversation.tsx. Result still consumes mock data; that
 * becomes real in Phases 8–9 (Evaluation Engine, Readiness Engine). The
 * point of Phase 4's typed contract was exactly this: swapping one
 * screen's data source at a time without touching the screen components
 * themselves — App.tsx's interface with <Conversation /> is unchanged.
 */
function App() {
  const [screen, setScreen] = useState<Screen>("start");
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Transcript is captured but not yet sent anywhere — real evaluation
  // (Phase 8) will consume it in place of mockReadinessResult.
  const [, setTranscript] = useState<TranscriptMessage[]>([]);

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
        onComplete={(finalTranscript) => {
          setTranscript(finalTranscript);
          setScreen("result");
        }}
      />
    );
  }

  return (
    <Result
      result={mockReadinessResult}
      onRestart={() => {
        setTranscript([]);
        setScreen("start");
      }}
    />
  );
}

export default App;
