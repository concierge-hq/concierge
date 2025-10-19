"""
Workflow: Blueprint definition for stages and transitions.
"""
from typing import Dict, Optional, Type, List, Union
import inspect

from concierge.core.stage import Stage
from concierge.core.state import State


class Workflow:
    """
    Workflow holds the blueprint: stages, tools, transitions.
    Provides methods for tool execution and transition validation.
    
    The Orchestrator maintains the cursor (current_stage) and delegates to Workflow.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.stages: Dict[str, Stage] = {}
        self.initial_stage: Optional[str] = None
    
    def add_stage(self, stage: Stage, initial: bool = False) -> 'Workflow':
        """Add a stage to the workflow"""
        self.stages[stage.name] = stage
        if initial or self.initial_stage is None:
            self.initial_stage = stage.name
        return self
    
    def get_stage(self, stage_name: str) -> Stage:
        """Get stage by name"""
        if stage_name not in self.stages:
            raise ValueError(f"Stage '{stage_name}' not found in workflow '{self.name}'")
        return self.stages[stage_name]
    
    async def call_tool(self, stage_name: str, tool_name: str, args: dict) -> dict:
        """Execute a tool in a specific stage"""
        stage = self.get_stage(stage_name)
        
        if tool_name not in stage.tools:
            return {
                "type": "error",
                "message": f"Tool '{tool_name}' not found in stage '{stage_name}'",
                "available": list(stage.tools.keys())
            }
        
        tool = stage.tools[tool_name]
        try:
            result = await tool.execute(stage.local_state, **args)
            return {
                "type": "tool_result",
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            return {
                "type": "tool_error",
                "tool": tool_name,
                "error": str(e)
            }
    
    def can_transition(self, from_stage: str, to_stage: str) -> bool:
        """Check if transition is valid"""
        stage = self.get_stage(from_stage)
        return stage.can_transition_to(to_stage)
    
    def validate_transition(self, from_stage: str, to_stage: str, global_state: State) -> dict:
        """Validate transition and check prerequisites"""
        if not self.can_transition(from_stage, to_stage):
            return {
                "valid": False,
                "error": f"Cannot transition from '{from_stage}' to '{to_stage}'",
                "allowed": self.get_stage(from_stage).transitions
            }
        
        target = self.get_stage(to_stage)
        missing = target.get_missing_prerequisites(global_state)
        
        if missing:
            return {
                "valid": False,
                "error": f"Stage '{to_stage}' requires: {missing}",
                "missing": missing
            }
        
        return {"valid": True}


# Decorator
class workflow:
    """
    Declarative workflow builder. Auto-discovers stage classes and transitions.
    
    Usage:
        @stage(name="browse")
        class BrowseStage:
            @tool()
            def search(...): ...
        
        @workflow(name="stock_exchange")
        class StockWorkflow:
            # Define stages (first = initial)
            browse = BrowseStage
            transact = TransactStage
            portfolio = PortfolioStage
            
            # Define transitions (semantic dict - uses class refs!)
            transitions = {
                browse: [transact, portfolio],     # From browse → transact or portfolio
                transact: [portfolio, browse],     # From transact → portfolio or browse
                portfolio: [browse]                # From portfolio → browse
            }
            
            # Also supports string-based dict:
            transitions = {
                "browse": ["transact", "portfolio"],
                "transact": ["portfolio", "browse"],
                "portfolio": ["browse"]
            }
    
    The decorator will:
    1. Find all @stage decorated classes
    2. Extract transitions dict (supports class refs or strings)
    3. Auto-register stages and wire transitions
    """
    
    def __init__(self, name: Optional[str] = None, description: str = ""):
        self.name = name
        self.description = description
    
    def __call__(self, cls: Type) -> Type:
        """Apply decorator to class"""
        workflow_name = self.name or cls.__name__.lower()
        workflow_desc = self.description or inspect.getdoc(cls) or ""
        
        workflow_obj = Workflow(name=workflow_name, description=workflow_desc)
        
        # Auto-discover stage classes (in order of definition)
        for attr_name, attr_value in cls.__dict__.items():
            if attr_name.startswith('_') or attr_name == 'transitions':
                continue
            
            stage_obj = getattr(attr_value, '_stage', None)
            if stage_obj is not None:
                # First stage becomes initial by default
                is_initial = len(workflow_obj.stages) == 0
                workflow_obj.add_stage(stage_obj, initial=is_initial)
        
        # Wire transitions (if defined)
        transitions_def = getattr(cls, 'transitions', None)
        if transitions_def and isinstance(transitions_def, dict):
            # Helper to extract stage name from either string or class
            def get_stage_name(key: Union[str, Type]) -> str:
                if isinstance(key, str):
                    return key
                # It's a class - extract the _stage.name
                return getattr(key, '_stage', None).name if hasattr(key, '_stage') else key.__name__.lower()
            
            # Process transitions
            for from_key, to_keys in transitions_def.items():
                from_name = get_stage_name(from_key)
                
                # Handle both single value and list
                if not isinstance(to_keys, list):
                    to_keys = [to_keys]
                
                to_names = [get_stage_name(k) for k in to_keys]
                
                if from_name in workflow_obj.stages:
                    workflow_obj.stages[from_name].transitions = to_names
        
        cls._workflow = workflow_obj
        return cls
