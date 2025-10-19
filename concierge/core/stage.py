"""
Stage: Represents a logical grouping of tools and state.
"""
from typing import Dict, List, Optional, Callable, Type, Any
from dataclasses import dataclass, field
import inspect

from concierge.core.state import State
from concierge.core.construct import is_construct, validate_construct
from concierge.core.tool import Tool, tool


@dataclass
class Context:
    """Context holds global state and metadata."""
    global_state: State = field(default_factory=State)


@dataclass
class Stage:
    """
    A stage represents a logical grouping of tools and state.
    Analogous to a page in a web application.
    
    Each stage has its own local state that is shared by all tools within the stage.
    """
    name: str
    description: str
        
    # Components
    tools: Dict[str, Tool] = field(default_factory=dict)
    
    # Stage-local state (shared by all tools in this stage)
    local_state: State = field(default_factory=State)
    
    # Navigation
    transitions: List[str] = field(default_factory=list)  # Valid next stages
    prerequisites: List[Type] = field(default_factory=list)  # Constructs defining required state

    # Hierarchy
    substages: Dict[str, 'Stage'] = field(default_factory=dict)
    parent: Optional['Stage'] = None
    
    def __post_init__(self):
        """Validate prerequisites are constructs and initialize local state"""
        for prereq in self.prerequisites:
            validate_construct(prereq, f"Stage '{self.name}' prerequisite {prereq.__name__}")
    
    def add_tool(self, tool: Tool) -> 'Stage':
        """Add a tool to this stage"""
        self.tools[tool.name] = tool
        return self
    
    def add_substage(self, substage: 'Stage') -> 'Stage':
        """Add a substage"""
        substage.parent = self
        self.substages[substage.name] = substage
        return self
    
    def get_available_tools(self, state: State) -> List[Tool]:
        """Get all tools in this stage. All tools are always available."""
        return list(self.tools.values())
    
    def can_transition_to(self, target_stage: str) -> bool:
        """Check if transition to target stage is allowed"""
        return target_stage in self.transitions
    
    def get_missing_prerequisites(self, state: State) -> List[str]:
        """Get missing prerequisites for entering this stage (Pydantic models only)"""
        
        missing = []
        for prereq in self.prerequisites:
            for field_name in prereq.model_fields:
                if not state.has(field_name):
                    missing.append(field_name)
        return missing
    
    def generate_prompt(self, state: State, include_tools: bool = True) -> str:
        """Generate LLM prompt for this stage"""
        prompt_parts = [
            f"You are in the '{self.name}' stage.",
            f"Description: {self.description}",
            ""
        ]
        
        # Add current state context
        if state.data:
            prompt_parts.append("Current State:")
            for construct_name, construct_data in state.data.items():
                if construct_data:
                    prompt_parts.append(f"  {construct_name}: {construct_data}")
            prompt_parts.append("")
        
        # Add available tools
        if include_tools and self.tools:
            prompt_parts.append("Available Tools:")
            for tool in self.tools.values():
                prompt_parts.append(f"  - {tool.name}: {tool.description}")
            prompt_parts.append("")
            
            prompt_parts.append("To use a tool, respond with:")
            prompt_parts.append('{"action": "tool", "tool": "tool_name", "args": {...}}')
            prompt_parts.append("")
        
        # Add transition options
        if self.transitions:
            prompt_parts.append(f"You can transition to: {', '.join(self.transitions)}")
            prompt_parts.append('To transition: {"action": "transition", "stage": "stage_name"}')
            prompt_parts.append("")
        
        # Add elicitation option
        prompt_parts.append("Need user input? Respond with:")
        prompt_parts.append('{"action": "elicit", "field": "field_name", "message": "Your question"}')
        prompt_parts.append("")
        
        # Add completion option
        prompt_parts.append("To respond to user:")
        prompt_parts.append('{"action": "respond", "message": "Your response"}')
        
        return "\n".join(prompt_parts)


# Decorator
class stage:
    """
    Mark a class as a Stage. Methods with @tool become tools.
    
    Args:
        name: Stage name (defaults to class name)
        prerequisites: List of Pydantic constructs required to enter this stage
    
    Note: Transitions are defined in the @workflow decorator, not here!
    """
    
    def __init__(
        self,
        name: Optional[str] = None,
        prerequisites: Optional[List[Type]] = None
    ):
        self.name = name
        self.prerequisites = prerequisites or []
    
    def __call__(self, cls: Type) -> Type:
        stage_name = self.name or cls.__name__.lower()
        stage_desc = inspect.getdoc(cls) or ""
        
        stage_obj = Stage(
            name=stage_name,
            description=stage_desc,
            prerequisites=self.prerequisites
        )
        
        instance = cls()
        
        for attr_name, attr_value in cls.__dict__.items():
            tool_obj = getattr(attr_value, '_concierge_tool', None)
            if tool_obj is not None:
                tool_obj.func = getattr(instance, attr_name)
                stage_obj.add_tool(tool_obj)
        
        cls._stage = stage_obj
        cls._instance = instance
        return cls

