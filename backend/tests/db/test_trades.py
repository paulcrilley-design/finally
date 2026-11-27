import math

import pytest

import db


def state(user_id="default"):
    return db.get_cash(user_id), db.list_positions(user_id), db.list_trades(user_id)


def test_buy_creates_position_and_logs_trade():
    trade = db.apply_trade("default", "AAPL", "buy", 10, 190.0)
    assert set(trade) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
    assert trade["executed_at"].endswith("+00:00")
    assert db.get_cash("default") == 8100.0
    position = db.get_position("default", "AAPL")
    assert set(position) == {"ticker", "quantity", "avg_cost", "updated_at"}
    assert (position["quantity"], position["avg_cost"]) == (10.0, 190.0)
    assert db.list_positions("default") == [position]
    assert db.list_trades("default") == [trade]


def test_buy_uses_weighted_average_and_sell_keeps_it():
    db.apply_trade("default", "AAPL", "buy", 10, 100.0)
    db.apply_trade("default", "AAPL", "buy", 30, 200.0)
    assert db.get_position("default", "AAPL")["avg_cost"] == pytest.approx(175.0)
    db.apply_trade("default", "AAPL", "sell", 15, 300.0)
    position = db.get_position("default", "AAPL")
    assert (position["quantity"], position["avg_cost"]) == (25.0, pytest.approx(175.0))
    assert db.get_cash("default") == 10000.0 - 1000 - 6000 + 4500


def test_selling_everything_deletes_position():
    for _ in range(3):
        db.apply_trade("default", "AAPL", "buy", 0.1, 100.0)
    db.apply_trade("default", "AAPL", "sell", 0.3, 100.0)
    assert db.get_position("default", "AAPL") is None
    assert db.get_cash("default") == 10000.0


def test_rounding():
    trade = db.apply_trade("default", "AAPL", "buy", 1.234567, 33.33)
    assert trade["quantity"] == 1.2346
    assert db.get_cash("default") == round(10000 - round(1.2346 * 33.33, 2), 2)


def test_can_spend_all_cash():
    db.apply_trade("default", "AAPL", "buy", 100, 100.0)
    assert db.get_cash("default") == 0.0


def test_insufficient_cash_changes_nothing():
    before = state()
    with pytest.raises(db.InsufficientCash):
        db.apply_trade("default", "AAPL", "buy", 100.0001, 100.0)
    assert state() == before


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT"])
def test_insufficient_shares_changes_nothing(ticker):
    db.apply_trade("default", "AAPL", "buy", 5, 100.0)
    before = state()
    with pytest.raises(db.InsufficientShares):
        db.apply_trade("default", ticker, "sell", 5.0001, 100.0)
    assert state() == before


@pytest.mark.parametrize(
    ("side", "quantity", "price"),
    [
        ("hold", 1, 100),
        ("buy", 0, 100),
        ("buy", -1, 100),
        ("buy", 0.00001, 100),
        ("buy", math.nan, 100),
        ("sell", math.inf, 100),
        ("buy", 1, 0),
        ("buy", 1, math.nan),
    ],
)
def test_invalid_input_rejected(side, quantity, price):
    before = state()
    with pytest.raises(ValueError):
        db.apply_trade("default", "AAPL", side, quantity, price)
    assert state() == before


def test_unknown_user():
    with pytest.raises(KeyError):
        db.apply_trade("nobody", "AAPL", "buy", 1, 100)
    with pytest.raises(KeyError):
        db.get_cash("nobody")


def test_failure_mid_transaction_rolls_back(execute):
    execute("CREATE TRIGGER fail BEFORE INSERT ON trades BEGIN SELECT RAISE(ABORT, 'boom'); END")
    before = state()
    with pytest.raises(Exception, match="boom"):
        db.apply_trade("default", "AAPL", "buy", 1, 100)
    assert state() == before


def test_trades_newest_first_with_limit():
    ids = [db.apply_trade("default", "AAPL", "buy", 1, 10)["id"] for _ in range(3)]
    assert [t["id"] for t in db.list_trades("default")] == ids[::-1]
    assert [t["id"] for t in db.list_trades("default", limit=2)] == ids[:0:-1]


def test_users_are_separate(other_user):
    db.apply_trade(other_user, "AAPL", "buy", 1, 100)
    assert state() == (10000.0, [], [])
    assert db.get_position("default", "AAPL") is None
    assert db.get_cash(other_user) == 400.0
    with pytest.raises(db.InsufficientShares):
        db.apply_trade("default", "AAPL", "sell", 1, 100)
