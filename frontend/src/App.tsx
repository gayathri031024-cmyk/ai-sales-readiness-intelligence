import { useState } from "react";
import type { TranscriptMessage } from "./types";
import { mockScenario } from "./mock/scenario";
import { mockReadinessResult } from "./mock/readiness";
import { StartScenario } from "./screens/StartScenario";
import { Conversation } from "./screens/Conversation";
import { Result } from "./screens/Result";

type Screen = "start" | "conversation" | "result";

/**
 * Phase 4 (Core UX): the full MVP journey — Start Scenario → Conversation
 * → Result — wired together with mock data (src/mock/). Real data starts
 * arriving screen-by-screen in Phases 5–9; this file's job is to prove the
 * flow and interaction design hold up, independent of any backend logic.
 */
function App() {
  const [screen, setScreen] = useState<Screen>("start");
  // Transcript is captured but not yet sent anywhere — real evaluation
  // (Phase 8) will consume it in place of mockReadinessResult.
  const [, setTranscript] = useState<TranscriptMessage[]>([]);

  if (screen === "start") {
    return <StartScenario scenario={mockScenario} onBegin={() => setScreen("conversation")} />;
  }

  if (screen === "conversation") {
    return (
      <Conversation
        scenario={mockScenario}
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
