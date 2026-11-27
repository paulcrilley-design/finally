"""The portfolio and market orders."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, StrictFloat, StrictInt

from app.errors import ApiError
from app.identity import get_current_user
from app.market import PriceCache, normalize_ticker
from app.tracking import sync_tracked_tickers
from db import TradeError, cents, execute_trade, read_portfolio, value_history

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: StrictInt | StrictFloat


def value_position(ticker: str, quantity: Decimal, avg_cost: Decimal, price: float | None) -> dict:
    """A position at the current price. Unknown values stay None, never substituted."""
    market_value = pnl = percent = None
    if price is not None:
        current = Decimal(str(price))
        market_value = cents(quantity * current)
        pnl = market_value - cents(quantity * avg_cost)
        if avg_cost > 0:
            percent = ((current - avg_cost) / avg_cost * 100).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
    return {
        "ticker": ticker,
        "quantity": float(quantity),
        "avg_cost": float(avg_cost),
        "price": price,
        "market_value": None if market_value is None else float(market_value),
        "unrealized_pnl": None if pnl is None else float(pnl),
        "pnl_percent": None if percent is None else float(percent),
    }


def portfolio_view(path, cache: PriceCache, user_id: str) -> dict:
    cash, held = read_portfolio(path, user_id)
    positions = [
        value_position(ticker, quantity, avg_cost, cache.get_price(normalize_ticker(ticker)))
        for ticker, quantity, avg_cost in held
    ]
    values = [position["market_value"] for position in positions]
    total = None
    if None not in values:
        total = float(cash + sum((Decimal(str(v)) for v in values), Decimal(0)))
    return {"cash": float(cash), "total_value": total, "positions": positions}


@router.get("")
def get_portfolio(request: Request, user_id: Annotated[str, Depends(get_current_user)]) -> dict:
    state = request.app.state
    return portfolio_view(state.db_path, state.price_cache, user_id)


@router.get("/history")
def get_history(request: Request, user_id: Annotated[str, Depends(get_current_user)]) -> dict:
    return {"history": value_history(request.app.state.db_path, user_id)}


@router.post("/trade")
async def trade(
    order: TradeRequest,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    state = request.app.state
    symbol = normalize_ticker(order.ticker)
    update = state.price_cache.get(symbol)
    try:
        filled = await run_in_threadpool(
            execute_trade,
            state.db_path,
            user_id,
            symbol,
            order.side,
            Decimal(str(order.quantity)),
            update.price if update else None,
            update.prev_close if update else None,
            {t: u.price for t, u in state.price_cache.get_all().items()},
        )
    except TradeError as refusal:
        raise ApiError(refusal.code, refusal.message) from refusal
    # Value the result first: closing an unwatched position stops its price.
    view = await run_in_threadpool(portfolio_view, state.db_path, state.price_cache, user_id)
    await sync_tracked_tickers(state)
    return {"trade": filled, "portfolio": view}
