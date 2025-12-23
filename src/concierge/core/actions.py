"""Action types for workflow execution."""
from dataclasses import dataclass
from typing import Any


@dataclass
class MethodCallAction:
    """Action to call a task in current stage"""
    task_name: str
    args: dict[str, Any]


@dataclass
class StageTransitionAction:
    """Action to transition to a new stage"""
    target_stage: str


@dataclass
class StateInputAction:
    """Action to update state with provided values"""
    state_updates: dict[str, Any]


Action = MethodCallAction | StageTransitionAction | StateInputAction

