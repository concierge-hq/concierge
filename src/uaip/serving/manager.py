"""
Session Manager - Core application logic for managing sessions.
Transport-agnostic: can be used directly or wrapped by HTTP/WebSocket/etc.
"""
import uuid
import json
from typing import Dict
from uaip.core.workflow import Workflow
from uaip.engine.language_engine import LanguageEngine
from uaip.core.state_manager import get_state_manager, StateManager


class SessionManager:
    """
    SessionManager is the core application that manages sessions and language engines.
    
    """
    
    def __init__(self, workflow: Workflow, state_manager: StateManager = None):
        self.workflow = workflow
        self.sessions: Dict[str, LanguageEngine] = {}
        self.state_manager = state_manager or get_state_manager()
    
    async def create_session(self, user_id: str = None) -> str:
        """Create a new session and return the session ID"""
        session_id = str(uuid.uuid4())
        
        # Create session in state manager BEFORE creating the engine
        state_mgr = self.state_manager
        self.workflow.initialize()
        await state_mgr.create_session(
            session_id=session_id,
            workflow_name=self.workflow.name,
            initial_stage=self.workflow.get_cursor().name
        )
        
        language_engine = LanguageEngine(self.workflow, session_id, user_id=user_id)
        self.sessions[session_id] = language_engine
        return session_id
    
    async def handle_request(self, session_id: str, message: dict) -> str:
        """
        Handle incoming request for a session.
        Routes to language engine and returns formatted response.
        Raises KeyError if session_id is invalid.
        """
        if session_id not in self.sessions:
            raise KeyError(f"Session {session_id} not found")
        
        language_engine = self.sessions[session_id]
        result = await language_engine.process(message)
        
        # Check if this was a termination request and run the termination hook
        try:
            result_data = json.loads(result)
            if result_data.get("status") == "terminated":
                await self._run_termination_hook(session_id)
        except (json.JSONDecodeError, TypeError):
            pass  # Not JSON or not a termination response
        
        return result
    
    async def _run_termination_hook(self, session_id: str) -> None:
        """Clean up session on termination. Events already flushed per-task."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    async def terminate_session(self, session_id: str, status: str = 'completed') -> None:
        """Terminate a session and clean up resources. Events already flushed per-task."""
        if session_id not in self.sessions:
            raise KeyError(f"Session {session_id} not found")
        
        await self.state_manager.update_session_status(session_id, status)
        del self.sessions[session_id]
    
    def get_active_sessions(self) -> list[str]:
        """Return list of active session IDs"""
        return list(self.sessions.keys())

