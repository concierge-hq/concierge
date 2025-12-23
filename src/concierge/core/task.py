"""
Task: Represents a single executable action with state awareness.
"""
from typing import Dict, List, Callable, Tuple, Type, Any, Optional
from dataclasses import dataclass, field
import inspect

from pydantic import create_model
from pydantic_core import PydanticUndefined
from pydantic.fields import FieldInfo
from typing import Any, get_type_hints

from concierge.core.state import State
from concierge.core.construct import validate_construct
from concierge.core.types import DefaultConstruct


@dataclass
class Task:
    """
    A task represents a single action that can be performed.
    
    - Tasks return their output as a dict (or an empty dict)
    - State management is handled by the stage/workflow
    - Optional output construct for validation
    """
    name: str
    description: str
    func: Callable
    output: Optional[Type] = None  
    
    is_async: bool = field(default=False, init=False)
    output_schema: Optional[dict] = field(default=None, init=False)
    
    def __post_init__(self):
        """Detect if function is async and extract output schema"""
        self.is_async = inspect.iscoroutinefunction(self.func)
        
        if self.output is None:
            self.output = DefaultConstruct
        
        validate_construct(self.output, f"Task '{self.name}' output")
        
        self.output_schema = self.output.model_json_schema()
    
    async def execute(self, state: State, **kwargs) -> dict:
        """
        Execute the task with given state and arguments.
        Returns the task output as a dict (empty dict if None).
        
        Note: func can be either a regular function or a bound method.
        Bound methods already have 'self' bound, so no special handling needed.
        """
        if self.is_async:
            result = await self.func(state, **kwargs)
        else:
            result = self.func(state, **kwargs)
        return result

    def to_schema(self) -> dict:
        """Convert task to schema for LLM prompting using Pydantic"""
        
        hints = get_type_hints(self.func)
        fields = {}
        
        for param_name, param in inspect.signature(self.func).parameters.items():
            if param_name == 'self':
                continue
            
            param_type = hints.get(param_name, param.annotation)
            if hasattr(param_type, '__name__') and param_type.__name__ in ['State', 'Context']:
                continue
            
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else PydanticUndefined
            
            field_info = FieldInfo.from_annotated_attribute(annotation, default)
            fields[param_name] = (field_info.annotation, field_info)
        
        InputModel = create_model(f"{self.name}Input", **fields)
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": InputModel.model_json_schema()
        }


# Decorator  
class task:
    """
    Mark a method as a task. Task receives (state, **kwargs).
    
    Usage:
        @task()
        def simple_task(state, x: int) -> dict:
            return {"result": x}
        
        @task(description="Custom task description")
        def described_task(state, x: int) -> dict:
            return {"result": x}
        
        @task(output=MyConstruct)
        def typed_task(state, x: int) -> dict:
            return {"field": "value"}
    """
    
    def __init__(self, description: Optional[str] = None, output: Optional[Type] = None):
        """Initialize task decorator with optional description and output construct"""
        self.description = description
        self.output = output
    
    def __call__(self, func: Callable) -> Callable:
        """Apply decorator to function"""
        # Check if this is a classmethod or staticmethod (wrapped)
        if isinstance(func, classmethod):
            raise TypeError(
                f"Invalid task definition: @task decorator cannot be applied to @classmethod.\n"
                f"Tasks must be regular instance methods.\n"
                f"Example:\n"
                f"  @stage()\n"
                f"  class MyStage:\n"
                f"      @task()\n"
                f"      def my_task(self, state, ...):\n"
                f"          ...\n"
            )
        
        if isinstance(func, staticmethod):
            raise TypeError(
                f"Invalid task definition: @task decorator cannot be applied to @staticmethod.\n"
                f"Tasks must be regular instance methods.\n"
                f"Example:\n"
                f"  @stage()\n"
                f"  class MyStage:\n"
                f"      @task()\n"
                f"      def my_task(self, state, ...):\n"
                f"          ...\n"
            )
        
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        if not params or params[0] != 'self':
            raise TypeError(
                f"Invalid task definition: @task decorator can only be applied to instance methods.\n"
                f"The first parameter must be 'self'.\n"
                f"Found parameters: {params}\n"
                f"Example:\n"
                f"  @stage()\n"
                f"  class MyStage:\n"
                f"      @task()\n"
                f"      def {func.__name__}(self, state, ...):\n"
                f"          ...\n"
            )
        
        task_obj = Task(
            name=func.__name__,
            description=self.description or inspect.getdoc(func) or "",
            func=func,
            output=self.output
        )
        func._concierge_task = task_obj
        return func



