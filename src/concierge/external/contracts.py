"""Formal JSON contracts for Concierge - like Thrift IDL for JSON.

These define the exact structure of JSON inputs that Concierge accepts.
Examples are auto-generated from Field(examples=[...]) metadata.
"""
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from typing import Any, Literal, Type, TypeVar, get_type_hints

T = TypeVar('T', bound=BaseModel)


def _auto_example(model_cls: Type[T]) -> T:
    """Auto-generate example instance from Field(examples=[...]) metadata"""
    kwargs = {}
    
    for field_name, field_info in model_cls.model_fields.items():
        field_type = model_cls.model_fields[field_name].annotation
        if hasattr(field_type, '__args__') and len(field_type.__args__) == 1:
            kwargs[field_name] = field_type.__args__[0]
        elif field_info.examples and len(field_info.examples) > 0:
            kwargs[field_name] = field_info.examples[0]
        elif field_info.default is not None and field_info.default != {}:
            kwargs[field_name] = field_info.default
    
    return model_cls(**kwargs)


class TaskCall(BaseModel):
    """Contract for calling a task in the current stage
    
    Example:
        {"action": "method_call", "task": "search", "args": {"symbol": "AAPL"}}
    """
    action: Literal["method_call"] = Field(
        description="Action type identifier for task execution"
    )
    task: str = Field(
        description="Name of the task to invoke",
        examples=["search", "add_to_cart", "checkout"]
    )
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the task",
        examples=[
            {"symbol": "AAPL"},
            {"symbol": "GOOGL", "quantity": 10}
        ]
    )


class StageTransition(BaseModel):
    """Contract for transitioning to a different stage in the workflow
    
    Example:
        {"action": "stage_transition", "stage": "portfolio"}
    """
    action: Literal["stage_transition"] = Field(
        description="Action type identifier for stage transition"
    )
    stage: str = Field(
        description="Target stage name to transition to",
        examples=["portfolio", "checkout", "browse"]
    )


class TerminateSession(BaseModel):
    """Contract for ending the current session
    
    Example:
        {"action": "terminate_session", "reason": "completed"}
    """
    action: Literal["terminate_session"] = Field(
        description="Action type identifier for session termination"
    )
    reason: str | None = Field(
        default=None,
        description="Optional reason for termination",
        examples=["completed", "user_request", "timeout"]
    )


class StateInput(BaseModel):
    """Contract for providing state variables required for transitions
    
    Example:
        {"action": "state_input", "state_updates": {"username": "alice", "age": 28}}
    """
    action: Literal["state_input"] = Field(
        description="Action type identifier for state input"
    )
    state_updates: dict[str, Any] = Field(
        description="State variables as key-value pairs where key is the field name and value is the field value",
        examples=[
            {"username": "john_doe", "age": 25},
            {"symbol": "AAPL", "quantity": 10}
        ]
    )


ACTION_METHOD_CALL = TaskCall.model_fields["action"].annotation.__args__[0]
ACTION_STAGE_TRANSITION = StageTransition.model_fields["action"].annotation.__args__[0]
ACTION_TERMINATE_SESSION = TerminateSession.model_fields["action"].annotation.__args__[0]
ACTION_STATE_INPUT = StateInput.model_fields["action"].annotation.__args__[0]

# Auto-generated example instances from Field(examples=[...]) metadata
TASK_CALL_EXAMPLE = _auto_example(TaskCall)
STAGE_TRANSITION_EXAMPLE = _auto_example(StageTransition)
TERMINATE_SESSION_EXAMPLE = _auto_example(TerminateSession)
STATE_INPUT_EXAMPLE = _auto_example(StateInput)

