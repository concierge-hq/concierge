"""
State Manager - Centralized state management for Concierge workflows.

Contract based interface for all state operations.

Usage:
    initialize_state_manager(InMemoryStateManager())
    
    mgr = get_state_manager()
    await mgr.create_session("session-123", "stock_workflow", "data_collection")
    await mgr.update_global_state("session-123", {"symbol": "AAPL"})
    await mgr.update_stage_state("session-123", "data_collection", {"price": 150.25})
    
    global_state = await mgr.get_global_state("session-123")
    stage_state = await mgr.get_stage_state("session-123", "data_collection")
    history = await mgr.get_state_history("session-123")
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from copy import deepcopy


class StateManager(ABC):
    """Base class defining state management contract."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize state manager (e.g., database connections). Called once at startup."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close state manager resources (e.g., database connections). Called at shutdown."""
        pass
    
    @abstractmethod
    async def create_session(
        self,
        session_id: str,
        workflow_name: str,
        initial_stage: str
    ) -> None:
        """Create new workflow session."""
        pass
    
    @abstractmethod
    async def update_global_state(
        self,
        session_id: str,
        state_json: Dict[str, Any]
    ) -> None:
        """Update global state (merged)."""
        pass
    
    @abstractmethod
    async def update_stage_state(
        self,
        session_id: str,
        stage_id: str,
        state_json: Dict[str, Any]
    ) -> None:
        """Update stage-specific state (merged)."""
        pass
    
    @abstractmethod
    async def update_current_stage(
        self,
        session_id: str,
        stage_id: str
    ) -> None:
        """Update current stage pointer."""
        pass
    
    @abstractmethod
    async def update_session_status(
        self,
        session_id: str,
        status: str
    ) -> None:
        """Update session status (running, completed, failed, cancelled)."""
        pass
    
    @abstractmethod
    async def get_global_state(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Get current global state."""
        pass
    
    @abstractmethod
    async def get_stage_state(
        self,
        session_id: str,
        stage_id: str
    ) -> Dict[str, Any]:
        """Get current stage state."""
        pass
    
    @abstractmethod
    async def get_state_history(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get all state versions (array of snapshots)."""
        pass
    
    @abstractmethod
    async def delete_session(
        self,
        session_id: str
    ) -> bool:
        """Delete session. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def get_all_stage_states(
        self,
        session_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get all stage states as dict of stage_name -> state_dict."""
        pass

    @abstractmethod
    async def save_benchmark_logs(
        self,
        session_id: str,
        logs: List[Dict[str, Any]]
    ) -> None:
        """Save benchmark/audit logs for a session."""
        pass


class InMemoryStateManager(StateManager):
    """In-memory implementation. For development only."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
    
    async def initialize(self) -> None:
        """No initialization needed for in-memory state."""
        pass
    
    async def close(self) -> None:
        """No cleanup needed for in-memory state."""
        pass
    
    async def create_session(
        self,
        session_id: str,
        workflow_name: str,
        initial_stage: str
    ) -> None:
        """Create new workflow session"""
        if session_id in self._sessions:
            raise ValueError(f"Session {session_id} already exists") 
        
        self._sessions[session_id] = {
            "workflow_name": workflow_name,
            "current_stage": initial_stage,
            "status": "running",
            "global_state": {},
            "stage_states": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": 1
        }
        self._history[session_id] = []
        self._snapshot(session_id)
    
    async def get_all_stage_states(
        self,
        session_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get all stage states."""
        session = self._get_session(session_id)
        return deepcopy(session["stage_states"])

    async def save_benchmark_logs(self, session_id: str, logs: List[Dict[str, Any]]) -> None:
        """Save benchmark logs in memory."""
        if session_id in self._sessions:
            self._sessions[session_id]["benchmark_logs"] = logs

    async def update_global_state(
        self,
        session_id: str,
        state_json: Dict[str, Any]
    ) -> None:
        session = self._get_session(session_id)
        session["global_state"].update(state_json)
        session["updated_at"] = datetime.utcnow().isoformat()
        session["version"] += 1
        self._snapshot(session_id)
    
    async def update_stage_state(
        self,
        session_id: str,
        stage_id: str,
        state_json: Dict[str, Any]
    ) -> None:
        session = self._get_session(session_id)
        if stage_id not in session["stage_states"]:
            session["stage_states"][stage_id] = {}
        session["stage_states"][stage_id].update(state_json)
        session["updated_at"] = datetime.utcnow().isoformat()
        session["version"] += 1
        self._snapshot(session_id)
    
    async def update_current_stage(
        self,
        session_id: str,
        stage_id: str
    ) -> None:
        session = self._get_session(session_id)
        session["current_stage"] = stage_id
        session["updated_at"] = datetime.utcnow().isoformat()
        session["version"] += 1
        self._snapshot(session_id)
    
    async def update_session_status(
        self,
        session_id: str,
        status: str
    ) -> None:
        session = self._get_session(session_id)
        session["status"] = status
        session["updated_at"] = datetime.utcnow().isoformat()
    
    async def get_global_state(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        return self._get_session(session_id)["global_state"]
    
    async def get_stage_state(
        self,
        session_id: str,
        stage_id: str
    ) -> Dict[str, Any]:
        session = self._get_session(session_id)
        return session["stage_states"].get(stage_id, {})
    
    async def get_state_history(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        if session_id not in self._history:
            raise ValueError(f"Session {session_id} not found")
        return self._history[session_id]
    
    async def delete_session(
        self,
        session_id: str
    ) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._history[session_id]
            return True
        return False
    
    def _get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        return self._sessions[session_id]
    
    def _snapshot(self, session_id: str) -> None:
        session = self._sessions[session_id]
        self._history[session_id].append({
            "version": session["version"],
            "timestamp": session["updated_at"],
            "current_stage": session["current_stage"],
            "global_state": deepcopy(session["global_state"]),
            "stage_states": deepcopy(session["stage_states"])
        })


_state_manager: Optional[StateManager] = None


def initialize_state_manager(manager: StateManager) -> None:
    """Initialize global state manager. Call once at startup."""
    global _state_manager
    _state_manager = manager


def get_state_manager() -> StateManager:
    """Get global state manager instance."""
    if _state_manager is None:
        raise RuntimeError("State manager not initialized")
    return _state_manager
