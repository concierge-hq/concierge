"""External contracts - formal JSON schemas for Concierge API"""

from concierge.external.contracts import (
    STAGE_TRANSITION_EXAMPLE,
    TASK_CALL_EXAMPLE,
    TERMINATE_SESSION_EXAMPLE,
    StageTransition,
    TaskCall,
    TerminateSession,
)

__all__ = [
    "TaskCall",
    "StageTransition",
    "TerminateSession",
    "TASK_CALL_EXAMPLE",
    "STAGE_TRANSITION_EXAMPLE",
    "TERMINATE_SESSION_EXAMPLE",
]
