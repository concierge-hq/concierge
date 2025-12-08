"""
Built-in constructs for common use cases.
"""

from typing import Any

from pydantic import BaseModel, Field

from concierge.core.construct import construct


@construct(description="Empty placeholder for tasks that don't return specific data")
class DefaultConstruct(BaseModel):
    """
    Default construct - empty placeholder for tasks that don't return specific data.
    Use this when your task doesn't need to return structured output.
    """

    pass


@construct(description="Single-value result for tasks that return one piece of data")
class SimpleResultConstruct(BaseModel):
    """
    Simple result construct - single field for returning any value.
    Use this for tasks that return a single result without complex structure.
    """

    result: Any = Field(description="The result value returned by the task. Can be any type.")
