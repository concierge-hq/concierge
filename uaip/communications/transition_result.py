"""Transition result communication."""
from uaip.communications.base import Communications
from uaip.core.results import TransitionResult


class TransitionResultMessage(Communications):
    """Message after successful stage transition - renders only the transition confirmation"""
    
    def render(self, result: TransitionResult) -> str:
        """Render only the transition confirmation, without stage context"""
        return f"Successfully transitioned from '{result.from_stage}' to '{result.to_stage}'."

