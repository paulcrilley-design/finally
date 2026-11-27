# Phase 4: AI Copilot (short plan, built without GSD)

Status: approved with option A and built (see 04-SUMMARY.md). Requirements: CHAT-01 to 09.

## Model calls

`openrouter/openai/gpt-oss-120b` (OpenRouter model id `openai/gpt-oss-120b`), Cerebras as
provider, low reasoning effort, structured JSON output validated with Pydantic.

Library, owner to choose:
- **A (recommended):** call OpenRouter's HTTP API with `httpx`, already in the project. Departs
  from `planning/PLAN.md` section 9 and the `cerebras` skill, which name LiteLLM.
- **B:** `litellm==1.106.2` pinned exactly. LiteLLM 1.107.0 (21 Oct 2026) and 1.82.7/1.82.8
  (Mar 2026) were published with credential-stealing code.

## Rules

- **Flow:** proposer, then code checks, then reviewer, then execution through the same services
  as the REST routes. No reviewer call when nothing is proposed or nothing passes the checks.
- **Reviewer:** approve or reject only. An action without a clear approval is rejected.
- **Fail closed:** a reviewer error, timeout or bad output rejects every action, watchlist
  changes included.
- **Failures:** one rejected or failed action does not stop the others; each is reported.
- **Timeouts:** proposer 20 s with one retry for a network error, server error or bad output;
  reviewer 10 s with no retry.
- **Limits:** message up to 1,000 characters, 5 trades and 5 watchlist changes per reply, one
  chat request at a time, last 10 messages and compact context, 800 / 300 output tokens.
- **No key or model failure:** a clear message in the panel; the rest of the app keeps working.
- **Mock (`LLM_MOCK=true`):** no network. Understands "buy N TICKER", "sell N TICKER",
  "add TICKER", "remove TICKER"; a message containing "reject" makes the reviewer reject.
- **Privacy:** only the chat messages, portfolio and watchlist prices go to the model. The key
  is never logged or sent to the browser.

## API and page

`GET /api/chat` (recent history) and `POST /api/chat` `{message}` returning the reply and each
action's outcome and reason. A collapsible side panel with history, loading indicator and inline
results; cash, positions, watchlist and value chart refresh afterwards.

## Build order (one run, no stops)

1. Backend: storage, context, model client, mock, review and execution, routes.
2. Frontend: chat panel and refresh.
3. Verify: tests (no network), lint, typecheck, build, browser check in mock mode, then at most
   two live messages if `OPENROUTER_API_KEY` is set.
4. README, GSD records, commit and push.

Not included: streaming replies, Docker (Phase 5).
