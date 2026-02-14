"""In-memory state backend - default, single-pod only."""
from __future__ import annotations

from typing import Any, Dict, Optional

from concierge.state.base import StateBackend


class InMemoryBackend(StateBackend):
    """In-memory state storage. Stateless, this is not distributed and only for dev purposes.."""
    
    def __init__(self):
        self._session_stages: Dict[str, str] = {}
        self._session_state: Dict[str, Dict[str, Any]] = {}
    
    def get_session_stage(self, session_id: str) -> Optional[str]:
        return self._session_stages.get(session_id)
    
    def set_session_stage(self, session_id: str, stage: str) -> None:
        self._session_stages[session_id] = stage
    
    def delete_session_stage(self, session_id: str) -> None:
        self._session_stages.pop(session_id, None)
    
    def get_state(self, session_id: str, key: str) -> Any:
        session_data = self._session_state.get(session_id, {})
        return session_data.get(key)
    
    def set_state(self, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._session_state:
            self._session_state[session_id] = {}
        self._session_state[session_id][key] = value
    
    def clear_session(self, session_id: str) -> None:
        self._session_stages.pop(session_id, None)
        self._session_state.pop(session_id, None)
