"""Abstract base class for state backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class StateBackend(ABC):
    """Abstract state storage backend for session data."""

    @abstractmethod
    def get_session_stage(self, session_id: str) -> Optional[str]:
        """Get current stage for a session. Returns None if not set."""
        pass

    @abstractmethod
    def set_session_stage(self, session_id: str, stage: str) -> None:
        """Set current stage for a session."""
        pass

    @abstractmethod
    def delete_session_stage(self, session_id: str) -> None:
        """Remove stage tracking for a session."""
        pass

    @abstractmethod
    def get_state(self, session_id: str, key: str) -> Any:
        """Get a value from session state. Returns None if not found."""
        pass

    @abstractmethod
    def set_state(self, session_id: str, key: str, value: Any) -> None:
        """Set a value in session state."""
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """Clear all state for a session (both stage and key-value state)."""
        pass
