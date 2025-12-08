"""Test State - core mutations only."""

from concierge.core import State


def test_state_set_get():
    state = State()
    state.set("key", "value")
    assert state.get("key") == "value"


def test_state_update_dict():
    state = State()
    state.set("user", {"name": "Alice"})
    state.update("user", {"age": 30})
    assert state.get("user") == {"name": "Alice", "age": 30}


def test_state_delete():
    state = State()
    state.set("key", "value")
    state.delete("key")
    assert not state.has("key")


def test_state_append():
    state = State()
    state.set("items", [])
    state.append("items", "item1")
    assert state.get("items") == ["item1"]


def test_state_increment():
    state = State()
    state.set("count", 0)
    state.increment("count", 5)
    assert state.get("count") == 5
