"""GET /api/watchlist: the user's tickers with their latest cached prices."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.identity import get_current_user
from app.market import normalize_ticker
from db import list_watchlist

router = APIRouter(prefix="/api", tags=["watchlist"])

# PriceUpdate.to_dict() without "ticker": all null while a price is unknown.
PRICE_FIELDS = (
    "price",
    "previous_price",
    "timestamp",
    "change",
    "change_percent",
    "direction",
    "prev_close",
    "day_change",
    "day_change_percent",
)


@router.get("/watchlist")
def get_watchlist(request: Request, user_id: Annotated[str, Depends(get_current_user)]) -> dict:
    items = []
    for ticker in list_watchlist(request.app.state.db_path, user_id):
        symbol = normalize_ticker(ticker)
        update = request.app.state.price_cache.get(symbol)
        if update is None:
            items.append({"ticker": symbol, **dict.fromkeys(PRICE_FIELDS)})
        else:
            items.append(update.to_dict())
    return {"watchlist": items}
