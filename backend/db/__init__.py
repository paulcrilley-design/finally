"""FinAlly data layer: SQLite access, isolated behind this package."""

from .chat import add_chat_message, list_chat_messages
from .errors import InsufficientCash, InsufficientShares
from .portfolio import (
    QUANTITY_DECIMALS,
    add_snapshot,
    apply_trade,
    get_position,
    list_positions,
    list_snapshots,
    list_trades,
    prune_snapshots,
)
from .schema import init_db
from .users import get_cash, list_user_ids
from .watchlist import add_watchlist, all_tracked_tickers, list_watchlist, remove_watchlist

__all__ = [
    "QUANTITY_DECIMALS",
    "InsufficientCash",
    "InsufficientShares",
    "add_chat_message",
    "add_snapshot",
    "add_watchlist",
    "all_tracked_tickers",
    "apply_trade",
    "get_cash",
    "get_position",
    "init_db",
    "list_chat_messages",
    "list_positions",
    "list_snapshots",
    "list_trades",
    "list_user_ids",
    "list_watchlist",
    "prune_snapshots",
    "remove_watchlist",
]
