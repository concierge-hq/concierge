"""Task result communication."""

from concierge.communications.base import Communications
from concierge.core.results import TaskResult


class TaskResultMessage(Communications):
    """Message after task execution - renders only the task execution result"""

    def render(self, result: TaskResult) -> str:
        """Render only the task execution result, without stage context"""
        result_str = str(result.result)

        return f"Task '{result.task_name}' executed successfully.\n\nResult:\n{result_str}"
