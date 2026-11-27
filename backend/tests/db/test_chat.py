import db


def test_add_returns_decoded_record():
    actions = {"trades": [], "watchlist_changes": [], "error": None}
    message = db.add_chat_message("default", "assistant", "Hi", actions)
    assert set(message) == {"id", "role", "content", "actions", "created_at"}
    assert db.list_chat_messages("default") == [message]
    assert message["actions"] == actions


def test_newest_limit_returned_oldest_first():
    for i in range(15):
        db.add_chat_message("default", "user", str(i))
    messages = db.list_chat_messages("default")
    assert [m["content"] for m in messages] == [str(i) for i in range(5, 15)]
    assert messages[0]["actions"] is None
    assert [m["content"] for m in db.list_chat_messages("default", limit=2)] == ["13", "14"]


def test_users_are_separate(other_user):
    db.add_chat_message(other_user, "user", "secret")
    assert db.list_chat_messages("default") == []
