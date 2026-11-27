from datetime import timedelta

import db


def values(**kwargs):
    return [s["total_value"] for s in db.list_snapshots("default", **kwargs)]


def test_add_and_list_oldest_first():
    for value in (1.0, 2.0, 3.0):
        db.add_snapshot("default", value)
    assert values() == [1.0, 2.0, 3.0]
    assert set(db.list_snapshots("default")[0]) == {"total_value", "recorded_at"}


def test_only_last_seven_days(insert_snapshot):
    insert_snapshot(1.0, timedelta(days=8))
    insert_snapshot(2.0, timedelta(days=6))
    assert values() == [2.0]


def test_downsample_keeps_first_and_newest(insert_snapshot):
    for i in range(100):
        insert_snapshot(float(i), timedelta(minutes=100 - i))
    sampled = values(limit=10)
    assert sampled == [float(i) for i in range(0, 100, 11)]
    assert values(limit=2) == [0.0, 99.0]
    assert values(limit=1) == [99.0]
    assert values(limit=0) == []
    assert len(values(limit=100)) == 100


def test_prune_is_per_user(insert_snapshot, other_user, execute):
    insert_snapshot(1.0, timedelta(days=8))
    insert_snapshot(2.0, timedelta(days=2))
    insert_snapshot(3.0, timedelta(days=8), user_id=other_user)
    db.prune_snapshots("default")
    remaining = execute("SELECT total_value FROM portfolio_snapshots ORDER BY total_value")
    assert remaining == [(2.0,), (3.0,)]
    db.prune_snapshots("default", days=1)
    assert execute("SELECT total_value FROM portfolio_snapshots") == [(3.0,)]
