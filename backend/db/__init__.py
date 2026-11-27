"""Data access for FinAlly: all SQL lives in this package."""

from .chat import add_exchange, recent_messages
from .database import (
    DEFAULT_USER_ID,
    add_to_watchlist,
    connect,
    init_db,
    is_healthy,
    list_watchlist,
    load_prices,
    remove_from_watchlist,
    save_prices,
    tracked_tickers,
)
from .portfolio import TradeError, cents, execute_trade, read_portfolio
from .snapshots import record_snapshots, value_history

__all__ = [
    "DEFAULT_USER_ID",
    "TradeError",
    "add_exchange",
    "add_to_watchlist",
    "cents",
    "execute_trade",
    "load_prices",
    "read_portfolio",
    "recent_messages",
    "record_snapshots",
    "value_history",
    "remove_from_watchlist",
    "save_prices",
    "connect",
    "init_db",
    "is_healthy",
    "list_watchlist",
    "tracked_tickers",
]
