"""
Workflow: Blueprint definition for stages and transitions.
"""

import inspect
from enum import Enum
from typing import Dict, List, Optional, Type, Union

from concierge.core.stage import Stage
from concierge.core.state import State
from concierge.core.state_manager import get_state_manager


class StateTransfer(Enum):
    ALL = "all"
    NONE = "none"


class Workflow:
    """
    Workflow holds the blueprint: stages, tasks, transitions.
    Provides methods for task execution and transition validation.

    The Orchestrator maintains the cursor (current_stage) and delegates to Workflow.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.stages: Dict[str, Stage] = {}
        self.initial_stage: Optional[str] = None
        self.cursor: Optional[Stage] = None
        self._incoming_edges: Dict[str, List[str]] = {}
        self.state_propagation: Dict[tuple, Union[str, List[str]]] = {}

    def add_stage(self, stage: Stage, initial: bool = False) -> "Workflow":
        """Add a stage to the workflow"""
        self.stages[stage.name] = stage
        if initial or self.initial_stage is None:
            self.initial_stage = stage.name
        self._build_incoming_edges()
        return self

    def _build_incoming_edges(self):
        """Build reverse edge mapping for graph navigation"""
        self._incoming_edges = {name: [] for name in self.stages.keys()}
        for stage_name, stage in self.stages.items():
            for target in stage.transitions:
                if target in self._incoming_edges:
                    self._incoming_edges[target].append(stage_name)

    def initialize(self):
        """Initialize cursor to initial stage"""
        self._build_incoming_edges()
        roots = [name for name, incoming in self._incoming_edges.items() if not incoming]
        stage_name = roots[0] if roots else list(self.stages.keys())[0]
        self.cursor = self.stages[stage_name]

    def get_cursor(self) -> Stage:
        """Get current cursor position"""
        return self.cursor

    def get_next_stages(self) -> List[str]:
        """Get valid next stages from current cursor"""
        return self.cursor.transitions

    def get_previous_stages(self) -> List[str]:
        """Get stages that can transition to current cursor"""
        return self._incoming_edges.get(self.cursor.name, [])

    def get_stage_metadata(self, stage_name: str) -> dict:
        """Get metadata for a stage: tasks and transitions"""
        stage = self.get_stage(stage_name)
        return {
            "name": stage.name,
            "description": stage.description,
            "tasks": [{"name": t.name, "description": t.description} for t in stage.tasks.values()],
            "transitions": stage.transitions,
            "prerequisites": [p.__name__ for p in stage.prerequisites],
        }

    def get_stage(self, stage_name: str) -> Stage:
        """Get stage by name"""
        if stage_name not in self.stages:
            raise ValueError(f"Stage '{stage_name}' not found in workflow '{self.name}'")
        return self.stages[stage_name]

    async def call_task(self, stage_name: str, task_name: str, args: dict, session_id: str) -> dict:
        """Execute a task in a specific stage"""
        stage = self.get_stage(stage_name)

        if task_name not in stage.tasks:
            return {
                "type": "error",
                "message": f"Task '{task_name}' not found in stage '{stage.name}'",
                "available": list(stage.tasks.keys()),
            }

        task = stage.tasks[task_name]
        state_mgr = get_state_manager()

        try:
            stage_state_dict = await state_mgr.get_stage_state(session_id, stage_name)
            stage_state = State(stage_state_dict)

            result = await task.execute(stage_state, **args)

            await state_mgr.update_stage_state(session_id, stage_name, stage_state.data)

            return {"type": "task_result", "task": task_name, "result": result}
        except Exception as e:
            return {"type": "task_error", "task": task_name, "error": str(e)}

    def can_transition(self, from_stage: str, to_stage: str) -> bool:
        """Check if transition is valid"""
        stage = self.get_stage(from_stage)
        return stage.can_transition_to(to_stage)

    def validate_transition(self, from_stage: str, to_stage: str, global_state: State, source_state: State) -> dict:
        """Validate transition and check prerequisites"""
        if not self.can_transition(from_stage, to_stage):
            return {
                "valid": False,
                "error": f"Cannot transition from '{from_stage}' to '{to_stage}'",
                "allowed": self.get_stage(from_stage).transitions,
            }

        target = self.get_stage(to_stage)
        propagation_config = self.get_propagation_config(from_stage, to_stage)

        missing = target.get_missing_prerequisites(global_state, source_state, propagation_config)

        if missing:
            return {
                "valid": False,
                "reason": "missing_state",
                "error": f"Stage '{to_stage}' requires: {missing}",
                "missing": missing,
            }

        return {"valid": True}

    def transition_to(self, to_stage: str) -> Stage:
        """Transition cursor to new stage and return target stage"""
        from_stage = self.cursor
        target = self.get_stage(to_stage)
        self.cursor = target
        return target

    def get_propagation_config(self, from_stage: str, to_stage: str) -> Union[str, List[str]]:
        """Get state propagation config for a transition"""
        return self.state_propagation.get((from_stage, to_stage), "all")


# Decorator
class workflow:
    """
    Declarative workflow builder.

    @workflow(name="stock_exchange")
    class StockWorkflow:
        browse = BrowseStage
        transact = TransactStage
        portfolio = PortfolioStage

        transitions = {
            browse: [transact, portfolio],
            transact: [portfolio, browse],
            portfolio: [browse],
        }

        state_management = [
            (browse, transact, ["symbol", "quantity"]),
            (browse, portfolio, StateTransfer.ALL),
        ]
    """

    def __init__(self, name: Optional[str] = None, description: str = ""):
        self.name = name
        self.description = description

    def __call__(self, cls: Type) -> Type:
        """Apply decorator to class"""
        workflow_name = self.name or cls.__name__.lower()
        workflow_desc = self.description or inspect.getdoc(cls) or ""

        if isinstance(cls, Workflow):
            raise TypeError(
                f"Invalid workflow definition: Cannot use @workflow decorator on a Workflow object that has already been decorated.\n"
                f"The @workflow decorator should only be applied once to a class.\n"
                f"Original workflow name: '{cls.name}'\n"
            )

        if isinstance(cls, Stage):
            raise TypeError(
                f"Invalid workflow definition: Cannot use @workflow decorator on a Stage object.\n"
                f"Stages and workflows are separate concepts - define them as separate classes.\n"
                f"Stage name: '{cls.name}'\n"
            )

        workflow_obj = Workflow(name=workflow_name, description=workflow_desc)

        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and hasattr(attr_value, "_concierge_task"):
                raise TypeError(
                    f"Invalid workflow definition: '{attr_name}' uses @task decorator directly on workflow class '{cls.__name__}'.\n"
                    f"Tasks must be defined inside @stage classes, not directly in @workflow classes.\n"
                    f"Example:\n"
                    f"  @stage()\n"
                    f"  class MyStage:\n"
                    f"      @task()\n"
                    f"      def {attr_name}(self, state, ...):\n"
                    f"          ...\n"
                    f"  \n"
                    f"  @workflow(name='my_workflow')\n"
                    f"  class MyWorkflow:\n"
                    f"      my_stage = MyStage  # Reference the stage class\n"
                )

            if isinstance(attr_value, Stage):
                workflow_obj.add_stage(attr_value, initial=len(workflow_obj.stages) == 0)
            elif isinstance(attr_value, type) and attr_name not in ["transitions", "state_management"]:
                has_task_methods = any(
                    hasattr(getattr(attr_value, method_name, None), "_concierge_task")
                    for method_name in dir(attr_value)
                    if not method_name.startswith("_")
                )
                if has_task_methods:
                    raise TypeError(
                        f"Invalid workflow definition: '{attr_name}' in workflow '{cls.__name__}' has @task methods but is not decorated with @stage.\n"
                        f"Classes with @task methods must use the @stage decorator.\n"
                        f"Example:\n"
                        f"  @stage(name='{attr_name}')\n"
                        f"  class {attr_value.__name__}:\n"
                        f"      @task()\n"
                        f"      def my_task(self, state, ...):\n"
                        f"          ...\n"
                    )

        if hasattr(cls, "transitions"):
            for from_stage, to_stages in cls.transitions.items():
                workflow_obj.stages[from_stage.name].transitions = [ts.name for ts in to_stages]

        if hasattr(cls, "state_management"):
            for from_stage, to_stage, config in cls.state_management:
                cfg = config.value if isinstance(config, StateTransfer) else config
                workflow_obj.state_propagation[(from_stage.name, to_stage.name)] = cfg

        cls._workflow = workflow_obj

        # Lazy import to avoid circular dependency
        from concierge.core.registry import get_registry

        get_registry().register(workflow_obj)

        return cls
