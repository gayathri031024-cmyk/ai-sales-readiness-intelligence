// MOCK — Phase 4 (Core UX) only. This is a simple canned-response stand-in
// so the Conversation screen's UX can be built and tested end-to-end. It has
// no hidden state, no adaptivity, and no LLM behind it — none of that exists
// until Phase 6 (Adaptive AI Buyer). Do not read anything into these replies
// beyond "the UI flow works."

const cannedReplies = [
  "Thanks for reaching out. Before we go further — your competitor quoted us about 30% less for a similar seat count. Why should I pay more?",
  "That's a fair point, but I still need to understand the total cost over three years, not just year one.",
  "Implementation time matters to me too. How long until my team is actually using this?",
  "Alright. Walk me through what happens if we don't renew after year one — am I locked into anything?",
  "I appreciate the detail. Let me think about what you've shared and get back to my team.",
];

let replyIndex = 0;

export function resetMockBuyer(): void {
  replyIndex = 0;
}

export function getMockBuyerReply(): string {
  const reply = cannedReplies[Math.min(replyIndex, cannedReplies.length - 1)];
  replyIndex += 1;
  return reply;
}
