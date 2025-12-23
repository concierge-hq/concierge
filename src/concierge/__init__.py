"""Concierge: Declarative LLM workflow framework."""

from concierge.core.state import State
from concierge.core.construct import construct, is_construct, validate_construct
from concierge.core.types import DefaultConstruct, SimpleResultConstruct
from concierge.core.task import Task, task
from concierge.core.stage import Stage, stage
from concierge.core.workflow import Workflow, workflow, StateTransfer

from concierge.engine.orchestrator import Orchestrator
from concierge.engine.language_engine import LanguageEngine
from concierge.serving.manager import SessionManager

from concierge.core.state_manager import initialize_state_manager, InMemoryStateManager
initialize_state_manager(InMemoryStateManager())

__version__ = "0.1.0"

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
