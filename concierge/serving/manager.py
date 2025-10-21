"""
Session Manager - Core application logic for managing sessions.
Transport-agnostic: can be used directly or wrapped by HTTP/WebSocket/etc.
"""
import uuid
from typing import Dict
from concierge.core.workflow import Workflow
from concierge.engine.language_engine import LanguageEngine


class SessionManager:
    """
    SessionManager is the core application that manages sessions and language engines.
    
    """
    
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self.sessions: Dict[str, LanguageEngine] = {}
    
    def create_session(self) -> str:
        """Create a new session and return the session ID"""
        session_id = str(uuid.uuid4())
        language_engine = LanguageEngine(self.workflow, session_id)
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
        return await language_engine.process(message)
    
    def terminate_session(self, session_id: str) -> None:
        """Terminate a session and clean up resources. Raises KeyError if session not found."""
        if session_id not in self.sessions:
            raise KeyError(f"Session {session_id} not found")
        del self.sessions[session_id]
    
    def get_active_sessions(self) -> list[str]:
        """Return list of active session IDs"""
        return list(self.sessions.keys())

