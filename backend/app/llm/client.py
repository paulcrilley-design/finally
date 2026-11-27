"""OpenRouter over HTTP, with Cerebras as the inference provider."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .mock import MockClient
from .schema import PROPOSAL_SCHEMA, REVIEW_SCHEMA, Proposal, ReviewResult

logger = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

Answer = TypeVar("Answer", bound=BaseModel)


class ModelError(Exception):
    """The model could not give a usable answer. The message is safe to show."""

    def __init__(self, code: str, message: str, retry: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry = retry


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
        propose_timeout: float = 20.0,
        review_timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._transport = transport  # tests replace the network
        self._propose_timeout = propose_timeout
        self._review_timeout = review_timeout

    async def propose(self, messages: list[dict]) -> Proposal:
        """One retry for a network error, server error or unusable answer."""
        try:
            return await self._ask(messages, Proposal, PROPOSAL_SCHEMA, 800, self._propose_timeout)
        except ModelError as error:
            if not error.retry:
                raise
        return await self._ask(messages, Proposal, PROPOSAL_SCHEMA, 800, self._propose_timeout)

    async def review(self, messages: list[dict]) -> ReviewResult:
        """No retry: a failed review rejects the actions."""
        return await self._ask(messages, ReviewResult, REVIEW_SCHEMA, 300, self._review_timeout)

    async def _ask(
        self,
        messages: list[dict],
        answer: type[Answer],
        schema: dict,
        max_tokens: int,
        timeout: float,
    ) -> Answer:
        if not self._api_key:
            raise ModelError(
                "no_api_key", "AI chat needs OPENROUTER_API_KEY in the root .env file."
            )
        body = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "reasoning": {"effort": "low"},
            "provider": {"order": ["cerebras"]},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": answer.__name__, "strict": True, "schema": schema},
            },
        }
        unavailable = "The AI model is not available right now. Try again."
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(transport=self._transport, timeout=timeout) as http:
                    response = await http.post(
                        URL, json=body, headers={"Authorization": f"Bearer {self._api_key}"}
                    )
        except (TimeoutError, httpx.HTTPError) as error:
            logger.warning("Model call failed: %s", type(error).__name__)
            raise ModelError("model_unavailable", unavailable, retry=True) from error
        if response.status_code in (401, 403):
            logger.warning("Model call refused: HTTP %s", response.status_code)
            raise ModelError("bad_api_key", "OpenRouter refused the API key.")
        if response.status_code != 200:
            logger.warning("Model call failed: HTTP %s", response.status_code)
            raise ModelError("model_unavailable", unavailable, retry=response.status_code >= 500)
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return answer.model_validate_json(content)
        except (ValueError, LookupError, TypeError, ValidationError) as error:
            logger.warning("Model answer unusable: %s", type(error).__name__)
            raise ModelError(
                "model_bad_output", "The AI model gave an unusable answer. Try again.", retry=True
            ) from error


def create_llm_client() -> MockClient | OpenRouterClient:
    if os.environ.get("LLM_MOCK", "").strip().lower() in ("1", "true", "yes"):
        logger.info("LLM: mock")
        return MockClient()
    return OpenRouterClient(os.environ.get("OPENROUTER_API_KEY", "").strip())
