"""UAIP: Declarative agentic workflow framework."""

from uaip.core.state import State
from uaip.core.construct import construct, is_construct, validate_construct
from uaip.core.types import DefaultConstruct, SimpleResultConstruct
from uaip.core.task import Task, task
from uaip.core.stage import Stage, stage
from uaip.core.workflow import Workflow, workflow, StateTransfer

from uaip.engine.orchestrator import Orchestrator
from uaip.engine.language_engine import LanguageEngine
from uaip.serving.manager import SessionManager

from uaip.core.state_manager import initialize_state_manager, InMemoryStateManager
initialize_state_manager(InMemoryStateManager())

__version__ = "0.1.2"

__all__ = [
    "State",
    "construct", "is_construct", "validate_construct",
    "DefaultConstruct", "SimpleResultConstruct",
    "Task", "task",
    "Stage", "stage",
    "Workflow", "workflow", "StateTransfer",
    "Orchestrator", "LanguageEngine",
    "SessionManager"
]
