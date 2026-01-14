"""State update message communication."""
from uaip.communications.base import Communications
from uaip.core.results import StateUpdateResult


class StateUpdateMessage(Communications):
    """Simple message for state updates (handshake, state population)"""
    
    def render(self, result: StateUpdateResult) -> str:
        """Render only the update message, presentation layer adds context"""
        return result.message

