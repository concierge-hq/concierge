"""
Stage: Represents a logical grouping of tasks.
State is managed externally via state_manager.
"""

import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from concierge.core.construct import validate_construct
from concierge.core.state import State
from concierge.core.task import Task


@dataclass
class Stage:
    """
    A stage represents a logical grouping of tasks.
    Analogous to a page in a web application.

    State is managed externally via state_manager, not stored here.
    """

    name: str
    description: str

    # Components
    tasks: Dict[str, Task] = field(default_factory=dict)

    # Navigation
    transitions: List[str] = field(default_factory=list)
    prerequisites: List[Type] = field(default_factory=list)

    # Hierarchy
    substages: Dict[str, "Stage"] = field(default_factory=dict)
    parent: Optional["Stage"] = None

    def __post_init__(self):
        """Validate prerequisites are constructs"""
        for prereq in self.prerequisites:
            validate_construct(prereq, f"Stage '{self.name}' prerequisite {prereq.__name__}")

    def __hash__(self):
        """Make Stage hashable (for use as dict keys)"""
        return hash(self.name)

    def __eq__(self, other):
        """Stage equality based on name"""
        if not isinstance(other, Stage):
            return False
        return self.name == other.name

    def add_task(self, task: Task) -> "Stage":
        """Add a task to this stage"""
        self.tasks[task.name] = task
        return self

    def add_substage(self, substage: "Stage") -> "Stage":
        """Add a substage"""
        substage.parent = self
        self.substages[substage.name] = substage
        return self

    def get_available_tasks(self, state: State) -> List[Task]:
        """Get all tasks in this stage. All tasks are always available."""
        return list(self.tasks.values())

    def can_transition_to(self, target_stage: str) -> bool:
        """Check if transition to target stage is allowed"""
        return target_stage in self.transitions

    def get_missing_prerequisites(
        self, state: State, source_state: Optional[State] = None, propagation_config: Optional[Any] = None
    ) -> List[str]:
        """
        Get missing prerequisites for entering this stage (Pydantic models only).

        Args:
            state: The global state to check against
            source_state: The source stage's local state (for transitions)
            propagation_config: State propagation config - "all", "none", or list of field names

        Returns:
            List of missing field names that won't be satisfied by state propagation
        """
        propagated_fields = set()
        if source_state is not None and propagation_config is not None:
            if propagation_config == "all":
                propagated_fields = set(source_state._data.keys())
            elif propagation_config == "none":
                propagated_fields = set()
            elif isinstance(propagation_config, list):
                propagated_fields = {field for field in propagation_config if source_state.has(field)}

        missing = []
        for prereq in self.prerequisites:
            for field_name in prereq.model_fields:
                if not state.has(field_name) and field_name not in propagated_fields:
                    missing.append(field_name)

        return missing


# Decorator
class stage:
    """
    Mark a class as a Stage. Methods with @task become tasks.

    Args:
        name: Stage name (defaults to class name)
        prerequisites: List of Pydantic constructs required to enter this stage

    Note: Transitions are defined in the @workflow decorator, not here!
    """

    def __init__(self, name: Optional[str] = None, prerequisites: Optional[List[Type]] = None):
        self.name = name
        self.prerequisites = prerequisites or []

    def __call__(self, cls: Type) -> Type:
        stage_name = self.name or cls.__name__.lower()
        stage_desc = inspect.getdoc(cls) or ""

        if isinstance(cls, Stage):
            raise TypeError(
                f"Invalid stage definition: Cannot use @stage decorator on a Stage object that has already been decorated.\n"
                f"The @stage decorator should only be applied once to a class.\n"
                f"Original stage name: '{cls.name}'\n"
            )

        from concierge.core.workflow import Workflow

        if isinstance(cls, Workflow):
            raise TypeError(
                f"Invalid stage definition: Cannot use @stage decorator on a Workflow object.\n"
                f"Stages and workflows are separate concepts - define them as separate classes.\n"
                f"Workflow name: '{cls.name}'\n"
            )

        stage_obj = Stage(name=stage_name, description=stage_desc, prerequisites=self.prerequisites)

        instance = cls()

        # Register tasks and validate
        task_count = 0
        for attr_name, attr_value in cls.__dict__.items():
            task_obj = getattr(attr_value, "_concierge_task", None)
            if task_obj is not None:
                task_obj.func = getattr(instance, attr_name)
                stage_obj.add_task(task_obj)
                task_count += 1

        # Warn if stage has no tasks (might be a configuration issue)
        if task_count == 0:
            import warnings

            warnings.warn(
                f"Stage '{stage_name}' (class '{cls.__name__}') has no @task methods defined. "
                f"Stages should contain at least one @task method to be useful.",
                UserWarning,
                stacklevel=2,
            )

        stage_obj._original_class = cls
        stage_obj._instance = instance
        return stage_obj
