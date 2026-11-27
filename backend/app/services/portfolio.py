"""Portfolio valuation and trading."""

import logging
import math

import db
from app.market import reconcile_tickers
from app.services.errors import ServiceError
from app.services.snapshots import take_snapshot
from app.services.tickers import require_symbol

logger = logging.getLogger(__name__)

DECIMALS = db.QUANTITY_DECIMALS


def get_portfolio(state, user_id: str) -> dict:
    """Cash, positions valued at live prices, and totals. Unpriced positions have nulls."""
    cash = db.get_cash(user_id)
    positions = []
    positions_value = 0.0
    unrealized_pnl = 0.0
    for row in db.list_positions(user_id):
        quantity, avg_cost = row["quantity"], row["avg_cost"]
        price = state.price_cache.get_price(row["ticker"])
        value = pnl = pnl_percent = None
        if price is not None:
            value = round(quantity * price, 2)
            pnl = round((price - avg_cost) * quantity, 2)
            pnl_percent = round((price - avg_cost) / avg_cost * 100, 4) if avg_cost else None
            positions_value += value
            unrealized_pnl += pnl
        positions.append(
            {
                "ticker": row["ticker"],
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": price,
                "market_value": value,
                "unrealized_pnl": pnl,
                "unrealized_pnl_percent": pnl_percent,
            }
        )
    for position in positions:
        value = position["market_value"]
        if value is None:
            position["weight"] = None
        else:
            position["weight"] = value / positions_value if positions_value else 0.0
    return {
        "cash_balance": cash,
        "total_value": round(cash + positions_value, 2),
        "positions_value": round(positions_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "positions": positions,
    }


def check_trade(
    state,
    user_id: str,
    ticker: str,
    side: str,
    quantity: float | None = None,
    amount: float | None = None,
) -> float:
    """Validate a trade without writing. Returns the live price or raises ServiceError."""
    return _price_order(state, user_id, ticker, side, quantity, amount)[0]


def _price_order(
    state, user_id: str, ticker: str, side: str, quantity: float | None, amount: float | None
) -> tuple[float, float]:
    """Check an order given in shares (`quantity`) or US dollars (`amount`).

    Returns (live price, shares to trade).
    """
    symbol = require_symbol(ticker)
    if side not in ("buy", "sell"):
        raise ServiceError("invalid_side", "Side must be 'buy' or 'sell'.")
    if (quantity is None) == (amount is None):
        raise ServiceError("invalid_request", "Give either a quantity or a dollar amount.")
    if amount is None:
        if not math.isfinite(quantity) or round(quantity, DECIMALS) <= 0:
            raise ServiceError("invalid_quantity", "Quantity must be a number greater than zero.")
    elif not math.isfinite(amount) or round(amount, 2) <= 0:
        raise ServiceError("invalid_amount", "Amount must be at least $0.01.")
    price = state.price_cache.get_price(symbol)
    if price is None:
        raise ServiceError("no_price", f"There is no live price for {symbol}.")
    position = db.get_position(user_id, symbol) if side == "sell" else None
    held = round(position["quantity"], DECIMALS) if position else 0.0
    if amount is None:
        quantity = round(quantity, DECIMALS)
    else:
        quantity = _shares_for(round(amount, 2), price, held)
    if side == "buy":
        # Not rounded first: a huge order makes this inf, which still compares correctly.
        value = round(quantity * price, 2)
        if value <= 0:
            raise ServiceError(
                "invalid_quantity", f"That quantity of {symbol} is worth less than $0.01."
            )
        if value > db.get_cash(user_id):
            raise _insufficient_cash(symbol)
    elif position is None or quantity > held:
        raise _insufficient_shares(symbol)
    return price, quantity


def _shares_for(amount: float, price: float, held: float) -> float:
    """Shares worth `amount` dollars, never costing more than it.

    Selling exactly what a holding is shown to be worth sells all of it (`held` is 0 on a buy).
    """
    if held and amount == round(held * price, 2):
        return held
    shares = amount / price
    if not math.isfinite(shares):
        return shares
    shares = round(shares, DECIMALS)
    if round(shares * price, 2) > amount:  # only possible for very high share prices
        shares = round(shares - 10**-DECIMALS, DECIMALS)
    return shares


async def execute_trade(
    state,
    user_id: str,
    ticker: str,
    side: str,
    quantity: float | None = None,
    amount: float | None = None,
) -> dict:
    """Fill a market order at the live price. Returns {"trade", "portfolio"}."""
    price, shares = _price_order(state, user_id, ticker, side, quantity, amount)
    symbol = require_symbol(ticker)
    try:
        trade = db.apply_trade(user_id, symbol, side, shares, price)
    except db.InsufficientCash:
        raise _insufficient_cash(symbol) from None
    except db.InsufficientShares:
        raise _insufficient_shares(symbol) from None
    trade["value"] = round(trade["quantity"] * price, 2)
    # The trade is committed: a failure below must not report it as failed.
    try:
        await reconcile_tickers(state.market_source, db.all_tracked_tickers())
        take_snapshot(state, user_id)
    except Exception:
        logger.exception("Post-trade update failed")
    return {"trade": trade, "portfolio": get_portfolio(state, user_id)}


def _insufficient_cash(ticker: str) -> ServiceError:
    return ServiceError("insufficient_cash", f"Not enough cash to buy that much {ticker}.")


def _insufficient_shares(ticker: str) -> ServiceError:
    return ServiceError("insufficient_shares", f"Not enough {ticker} shares to sell.")
