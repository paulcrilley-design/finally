"""Cash, positions and trades. Money is calculated with Decimal, stored as REAL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .database import UPSERT_PRICE, connect

CENT = Decimal("0.01")
UNIT = Decimal("0.0001")  # smallest quantity, and the precision of an average cost
MAX_QUANTITY = Decimal("1000000000")


class TradeError(Exception):
    """A trade that breaks a rule. Nothing has been changed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, ROUND_HALF_UP)


def _units(value: Decimal) -> Decimal:
    return value.quantize(UNIT, ROUND_HALF_UP)


def _stored(value: float) -> Decimal:
    return Decimal(str(value))


def check_quantity(quantity: Decimal) -> Decimal:
    if (
        not quantity.is_finite()
        or quantity <= 0
        or quantity > MAX_QUANTITY
        or quantity != _units(quantity)
    ):
        raise TradeError(
            "invalid_quantity", "Quantity must be above 0, with at most 4 decimal places."
        )
    return _units(quantity)


def read_portfolio(path: Path, user_id: str) -> tuple[Decimal, list[tuple[str, Decimal, Decimal]]]:
    """Cash and (ticker, quantity, average cost) per position, from one consistent read."""
    with connect(path) as conn:
        conn.execute("BEGIN")
        profile = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    cash = cents(_stored(profile["cash_balance"])) if profile else Decimal("0.00")
    positions = [
        (row["ticker"], _units(_stored(row["quantity"])), _units(_stored(row["avg_cost"])))
        for row in rows
    ]
    return cash, positions


def execute_trade(
    path: Path,
    user_id: str,
    ticker: str,
    side: str,
    quantity: Decimal,
    price: float | None,
    prev_close: float | None = None,
) -> dict:
    """Fill a market order in one transaction, or raise TradeError and change nothing."""
    quantity = check_quantity(quantity)
    if price is None or price <= 0:
        raise TradeError("no_price", f"There is no current price for {ticker}.")
    unit_price = _stored(price)
    value = cents(quantity * unit_price)
    now = datetime.now(UTC).isoformat()

    with connect(path) as conn:
        # Take the write lock before reading, so two trades cannot spend the same cash.
        conn.execute("BEGIN IMMEDIATE")
        profile = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        if profile is None:
            raise TradeError("unknown_user", "There is no account for this user.")
        cash = cents(_stored(profile["cash_balance"]))
        row = conn.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        held = _units(_stored(row["quantity"])) if row else Decimal(0)
        avg_cost = _stored(row["avg_cost"]) if row else Decimal(0)

        if side == "buy":
            if value > cash:
                raise TradeError(
                    "insufficient_cash",
                    f"Not enough cash: this costs ${value:,.2f} and you have ${cash:,.2f}.",
                )
            new_quantity = held + quantity
            avg_cost = _units((held * avg_cost + quantity * unit_price) / new_quantity)
            cash -= value
        else:
            if quantity > held:
                raise TradeError(
                    "insufficient_shares",
                    f"Not enough shares: you hold {held.normalize():f} {ticker}.",
                )
            new_quantity = held - quantity
            cash += value
        # A whole position can always be closed, however little it is worth.
        if value == 0 and not (side == "sell" and new_quantity == 0):
            raise TradeError("value_too_small", "This trade is worth less than one cent.")

        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (float(cash), user_id)
        )
        if new_quantity == 0:
            conn.execute(
                "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
            )
        else:
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (user_id, ticker) DO UPDATE SET"
                " quantity = excluded.quantity, avg_cost = excluded.avg_cost,"
                " updated_at = excluded.updated_at",
                (str(uuid.uuid4()), user_id, ticker, float(new_quantity), float(avg_cost), now),
            )
        trade = {
            "id": str(uuid.uuid4()),
            "ticker": ticker,
            "side": side,
            "quantity": float(quantity),
            "price": price,
            "executed_at": now,
        }
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)"
            " VALUES (:id, :user_id, :ticker, :side, :quantity, :price, :executed_at)",
            {**trade, "user_id": user_id},
        )
        # So that even a crash cannot restart below the price this trade filled at.
        conn.execute(UPSERT_PRICE, (ticker, price, prev_close or price, now))
    return trade
