"""
Construct: A fragment of state in Concierge.
"""
from typing import Type, TypeVar, Optional, Callable
from pydantic import BaseModel

T = TypeVar('T')


def construct(description: Optional[str] = None):
    """
    Mark a Pydantic BaseModel as a Concierge construct.
    
    A construct represents a fragment of state - a structured piece of data
    that can move through stages, be used as prerequisites, or define output schemas.
    
    Usage:
        from pydantic import BaseModel, Field
        from concierge.core import construct
        
        # Simple usage (uses docstring)
        @construct()
        class User(BaseModel):
            '''User information construct'''
            id: str = Field(description="User ID")
            email: str = Field(description="Email address")
        
        # With explicit description
        @construct(description="User authentication data")
        class User(BaseModel):
            id: str = Field(description="User ID")
            email: str = Field(description="Email address")
    
    Args:
        description: Optional description for the construct. 
                    If not provided, uses class docstring.
    
    The @construct decorator:
    - Validates the class is a Pydantic BaseModel
    - Marks it as a Concierge construct (for type checking)
    - Stores optional description (uses docstring as fallback)
    - Can be extended with additional optional arguments in the future
    """
    def decorator(cls: Type[T]) -> Type[T]:
        if not issubclass(cls, BaseModel):
            raise TypeError(
                f"@construct can only be applied to Pydantic BaseModel classes. "
                f"{cls.__name__} is not a BaseModel."
            )
        
        cls._is_construct = True
        cls._construct_name = cls.__name__
        cls._construct_description = description or cls.__doc__ or ""
        
        return cls
    
    return decorator


def is_construct(obj) -> bool:
    """Check if an object is a Concierge construct"""
    return hasattr(obj, '_is_construct') and obj._is_construct


def validate_construct(obj, name: str = "Object"):
    """Validate that an object is a construct, raise TypeError if not"""
    if not is_construct(obj):
        raise TypeError(
            f"{name} must be a @construct. "
            f"Apply @construct decorator to your Pydantic BaseModel."
        )

