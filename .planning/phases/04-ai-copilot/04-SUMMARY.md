---
phase: 04-ai-copilot
status: complete
requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09]
---

# Phase 4 Summary: AI copilot

## Built

- Backend: `app/llm/` (OpenRouter over `httpx`, mock), `app/chat.py` (propose, code checks,
  review, execute, store), `app/services.py` shared with the REST routes, `/api/chat`.
- Page: collapsible chat panel with history, loading state and inline action results.
- Owner chose option A: no LiteLLM. `planning/PLAN.md` section 9 and the `cerebras` skill still
  name it.

## Verification

- Backend 261 passed, ruff clean (no network calls in tests); frontend 84 passed, lint,
  typecheck and build passed.
- Browser, mock model: question, add and buy, over-budget refusal, reviewer rejection, history
  after reload, no console warnings, no page scroll at 375 px.
- Live model, two messages on a temporary database: a 2-share buy was approved and filled; a
  question was answered. No key or bearer token appears in the server log.
- The answer to the second message misstated a weight (about 4% shown as 2%). The model is now
  sent each weight and told not to calculate its own; covered by a test, not re-run live.
