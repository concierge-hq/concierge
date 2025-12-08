"""
State management for Concierge.
Simple immutable dictionary that can store any objects.
"""

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional


class State:
    """
    Mutable state container for workflow sessions.
    Store any Python objects - Pydantic models, dataclasses, plain values, dicts, etc.

    Example with plain values:
        state = State()
        state.set("user_id", "123")
        state.set("counter", 0)
        state.set("items", ["item1", "item2"])

    Example with Pydantic objects:
        from pydantic import BaseModel

        class User(BaseModel):
            id: str
            email: str

        class Cart(BaseModel):
            items: list
            total: float

        user = User(id="123", email="test@example.com")
        cart = Cart(items=["item1"], total=99.99)

        state = State()
        state.set("user", user)
        state.set("cart", cart)

        # Access
        user = state.get("user")
        print(user.email)  # "test@example.com"

    Example with mixed types:
        state = State()
        state.set("user", User(id="123", email="test@example.com"))  # Object
        state.set("counter", 0)                                       # Int
        state.set("config", {"debug": True, "timeout": 30})          # Dict
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize state.
        Args:
            data: Initial state data (dict of key -> any value/object)
        """
        self._data = data or {}
        self._version = 0

    @property
    def data(self) -> Dict[str, Any]:
        """Get copy of state data"""
        return deepcopy(self._data)

    def set(self, key: str, value: Any) -> None:
        """
        Set key to value (replaces). Mutates in place.
        Accepts any Python object - Pydantic models, plain values, dicts, etc.
        """
        self._data[key] = value
        self._version += 1

    def update(self, key: str, value: Any) -> None:
        """
        Update key with value. Mutates in place.
        For dicts: merges with existing dict.
        For other types: replaces value.
        """
        current = self.get(key, {})
        if isinstance(current, dict) and isinstance(value, dict):
            merged = {**current, **value}
            self._data[key] = merged
        else:
            self._data[key] = value
        self._version += 1

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if key exists"""
        return key in self._data

    def delete(self, key: str) -> None:
        """Remove key from state. Mutates in place."""
        if key in self._data:
            del self._data[key]
            self._version += 1

    def append(self, key: str, value: Any) -> None:
        """Append to list at key. Mutates in place."""
        current = self.get(key, [])
        if not isinstance(current, list):
            raise TypeError(f"Cannot append to non-list value at key '{key}'")
        current.append(value)
        self._version += 1

    def increment(self, key: str, amount: float = 1) -> None:
        """Increment numeric value. Mutates in place."""
        current = self.get(key, 0)
        if not isinstance(current, (int, float)):
            raise TypeError(f"Cannot increment non-numeric value at key '{key}'")
        self._data[key] = current + amount
        self._version += 1

    def merge(self, other: "State") -> None:
        """Merge another state into this one. Mutates in place."""
        self._data.update(other._data)
        self._version = max(self._version, other._version) + 1

    def subset(self, keys: List[str]) -> "State":
        """Create new state with only specified keys"""
        new_data = {k: self._data[k] for k in keys if k in self._data}
        return State(new_data)

    def to_dict(self) -> dict:
        """Convert to plain dict"""
        return deepcopy(self._data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self._data, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "State":
        """Create state from dict"""
        return cls(data)

    @classmethod
    def from_json(cls, json_str: str) -> "State":
        """Create state from JSON"""
        return cls(json.loads(json_str))

    def __repr__(self) -> str:
        keys = list(self._data.keys())
        return f"State(keys={keys}, version={self._version})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, State) and self._data == other._data
