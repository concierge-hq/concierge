"""Result types for workflow execution."""
from dataclasses import dataclass
from typing import Any, Type
from concierge.presentations import Presentation


@dataclass
class TaskResult:
    """Result of a task execution"""
    task_name: str
    result: Any
    presentation_type: Type[Presentation]
    error: str | None = None


@dataclass
class TransitionResult:
    """Result of a stage transition"""
    from_stage: str
    to_stage: str
    presentation_type: Type[Presentation]


@dataclass
class ErrorResult:
    """Error result"""
    message: str
    presentation_type: Type[Presentation]
    allowed: list[str] | None = None


@dataclass
class StateInputRequiredResult:
    """Request for missing prerequisite state before transition"""
    target_stage: str
    message: str
    required_fields: list[str]
    presentation_type: Type[Presentation]


@dataclass
class StateUpdateResult:
    """Result of state update (handshake, state population, etc.)"""
    message: str
    presentation_type: Type[Presentation]


Result = TaskResult | TransitionResult | ErrorResult | StateInputRequiredResult | StateUpdateResult

