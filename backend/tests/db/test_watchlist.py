import db


def test_add_and_remove():
    assert db.add_watchlist("default", "PYPL") is True
    assert db.add_watchlist("default", "PYPL") is False
    assert db.list_watchlist("default")[-1] == "PYPL"
    assert db.remove_watchlist("default", "PYPL") is True
    assert db.remove_watchlist("default", "PYPL") is False
    assert "PYPL" not in db.list_watchlist("default")


def test_users_are_separate(other_user):
    assert db.list_watchlist(other_user) == []
    assert db.add_watchlist(other_user, "AAPL") is True
    assert db.remove_watchlist(other_user, "MSFT") is False
    assert db.list_watchlist(other_user) == ["AAPL"]
    assert "MSFT" in db.list_watchlist("default")


def test_tracked_tickers_unions_watchlists_and_positions(other_user):
    db.add_watchlist(other_user, "PYPL")
    db.apply_trade("default", "AAPL", "buy", 1, 100)
    db.remove_watchlist("default", "AAPL")
    db.apply_trade(other_user, "IBM", "buy", 1, 100)
    tracked = db.all_tracked_tickers()
    assert {"AAPL", "PYPL", "IBM", "MSFT"} <= tracked
    assert len(tracked) == 12
