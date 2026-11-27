"""The language model: a live OpenRouter client and a deterministic mock."""

from .client import ModelError, OpenRouterClient, create_llm_client
from .mock import MockClient
from .schema import Proposal, ProposedTrade, Review, ReviewResult, WatchlistChange

__all__ = [
    "MockClient",
    "ModelError",
    "OpenRouterClient",
    "Proposal",
    "ProposedTrade",
    "Review",
    "ReviewResult",
    "WatchlistChange",
    "create_llm_client",
]
