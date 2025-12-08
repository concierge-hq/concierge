"""State update message communication."""

from concierge.communications.base import Communications
from concierge.core.results import StateUpdateResult


class StateUpdateMessage(Communications):
    """Simple message for state updates (handshake, state population)"""

    def render(self, result: StateUpdateResult) -> str:
        """Render only the update message, presentation layer adds context"""
        return result.message
