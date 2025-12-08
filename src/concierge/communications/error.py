"""Error communication."""

from concierge.communications.base import Communications
from concierge.core.results import ErrorResult


class ErrorMessage(Communications):
    """Message for errors - renders only the error details"""

    def render(self, result: ErrorResult) -> str:
        """Render only the error message and context"""
        lines = [f"Error: {result.message}"]

        if result.allowed:
            lines.append(f"\nAllowed options: {', '.join(result.allowed)}")

        return "\n".join(lines)
