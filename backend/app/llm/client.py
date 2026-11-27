"""The two LLM calls: LiteLLM -> OpenRouter -> Cerebras, with structured outputs."""

import asyncio
import os
from typing import TypeVar

from pydantic import BaseModel

# Set before importing litellm: nothing may load .env, and mock mode makes no network calls
# (litellm otherwise does both at import time).
os.environ.setdefault("LITELLM_MODE", "PRODUCTION")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

from litellm import acompletion  # noqa: E402

from .prompts import proposer_messages, reviewer_messages  # noqa: E402
from .schemas import ProposerResponse, ReviewerResponse  # noqa: E402

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
TIMEOUT_SECONDS = 30.0
PROPOSER_MAX_TOKENS = 800
REVIEWER_MAX_TOKENS = 500  # reasoning tokens count against this

Schema = TypeVar("Schema", bound=BaseModel)


class LLMError(Exception):
    """An LLM call failed in any way, including malformed output."""


class MissingAPIKeyError(LLMError):
    """OPENROUTER_API_KEY is not set."""


async def _structured_call(messages: list[dict], schema: type[Schema], max_tokens: int) -> Schema:
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        raise MissingAPIKeyError("OPENROUTER_API_KEY is not set")
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            response = await acompletion(
                model=MODEL,
                messages=messages,
                response_format=schema,
                max_tokens=max_tokens,
                reasoning_effort="low",
                extra_body=EXTRA_BODY,
                timeout=TIMEOUT_SECONDS,
                num_retries=0,
            )
        return schema.model_validate_json(response.choices[0].message.content)
    except Exception as exc:
        raise LLMError(f"{type(exc).__name__}: {exc}") from exc


async def propose(
    portfolio: dict, watchlist: dict, history: list[dict], user_message: str
) -> ProposerResponse:
    messages = proposer_messages(portfolio, watchlist, history, user_message)
    return await _structured_call(messages, ProposerResponse, PROPOSER_MAX_TOKENS)


async def review(portfolio: dict, user_message: str, actions: list[dict]) -> ReviewerResponse:
    messages = reviewer_messages(portfolio, user_message, actions)
    return await _structured_call(messages, ReviewerResponse, REVIEWER_MAX_TOKENS)
