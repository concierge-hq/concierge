"""Result types for workflow execution."""
from dataclasses import dataclass
from typing import Any, List, Optional, Type, Union
from uaip.presentations import Presentation


@dataclass
class TaskResult:
    """Result of a task execution"""
    task_name: str
    result: Any
    presentation_type: Type[Presentation]
    error: Optional[str] = None


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
    allowed: Optional[List[str]] = None


@dataclass
class StateInputRequiredResult:
    """Request for missing prerequisite state before transition"""
    target_stage: str
    message: str
    required_fields: List[str]
    presentation_type: Type[Presentation]


@dataclass
class StateUpdateResult:
    """Result of state update (handshake, state population, etc.)"""
    message: str
    presentation_type: Type[Presentation]


Result = Union[TaskResult, TransitionResult, ErrorResult, StateInputRequiredResult, StateUpdateResult]

