"""
Workflow: Main orchestrator managing stages and state transitions.
"""
from typing import Dict, Optional
from dataclasses import dataclass, field

from concierge.core.state import State
from concierge.core.tool import Tool
from concierge.core.stage import Stage


class Workflow:
    """
    Main workflow orchestrator managing stages and state transitions.
    This is the core engine that brings everything together.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.stages: Dict[str, Stage] = {}
        self.initial_stage: Optional[str] = None
        self.sessions: Dict[str, 'WorkflowSession'] = {}
    
    def add_stage(self, stage: Stage, initial: bool = False) -> 'Workflow':
        """Add a stage to the workflow"""
        self.stages[stage.name] = stage
        if initial or self.initial_stage is None:
            self.initial_stage = stage.name
        return self
    
    def create_session(self, session_id: Optional[str] = None) -> 'WorkflowSession':
        """Create a new workflow session"""
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        session = WorkflowSession(self, session_id)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional['WorkflowSession']:
        """Get existing session by ID"""
        return self.sessions.get(session_id)


@dataclass
class WorkflowSession:
    """
    A single execution session of a workflow.
    Maintains state and handles interactions.
    """
    workflow: Workflow
    session_id: str
    current_stage: str = field(init=False)
    state: State = field(default_factory=State)
    history: list = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize session with workflow's initial stage"""
        self.current_stage = self.workflow.initial_stage or list(self.workflow.stages.keys())[0]
        self.state = State()
        self.history = []
    
    def get_current_stage(self) -> Stage:
        """Get current stage object"""
        return self.workflow.stages[self.current_stage]
    
    async def process_action(self, action: dict) -> dict:
        """
        Process an action from the LLM.
        Returns response to send back.
        """
        action_type = action.get("action")
        stage = self.get_current_stage()
        
        if action_type == "tool":
            return await self._handle_tool_action(action, stage)
        elif action_type == "transition":
            return await self._handle_transition(action, stage)
        elif action_type == "elicit":
            return self._handle_elicitation(action)
        elif action_type == "respond":
            return {"type": "response", "message": action.get("message", "")}
        else:
            return {"type": "error", "message": f"Unknown action type: {action_type}"}
    
    async def _handle_tool_action(self, action: dict, stage: Stage) -> dict:
        """Handle tool execution"""
        tool_name = action.get("tool")
        args = action.get("args", {})
        
        if tool_name not in stage.tools:
            return {
                "type": "error",
                "message": f"Tool '{tool_name}' not found in stage '{stage.name}'",
                "available": list(stage.tools.keys())
            }
        
        tool = stage.tools[tool_name]
        
        # Execute tool with stage-local state (elicitation handled by LLM, not pre-checked)
        try:
            result = await tool.execute(stage.local_state, **args)
            self.history.append({"action": "tool", "tool": tool_name, "args": args, "result": result})
            
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
    
    async def _handle_transition(self, action: dict, stage: Stage) -> dict:
        """Handle stage transition"""
        target_stage = action.get("stage")
        
        if not stage.can_transition_to(target_stage):
            return {
                "type": "error",
                "message": f"Cannot transition from '{stage.name}' to '{target_stage}'",
                "allowed": stage.transitions
            }
        
        target = self.workflow.stages.get(target_stage)
        if not target:
            return {
                "type": "error",
                "message": f"Stage '{target_stage}' not found"
            }
        
        # Check prerequisites
        missing = target.get_missing_prerequisites(self.state)
        if missing:
            return {
                "type": "elicit_required",
                "message": f"Stage '{target_stage}' requires: {missing}",
                "missing": missing
            }
        
        # Perform transition
        self.current_stage = target_stage
        self.history.append({"action": "transition", "from": stage.name, "to": target_stage})
        
        return {
            "type": "transitioned",
            "from": stage.name,
            "to": target_stage,
            "prompt": target.generate_prompt(target.local_state)
        }
    
    def _handle_elicitation(self, action: dict) -> dict:
        """Handle request for user input"""
        return {
            "type": "elicit",
            "field": action.get("field"),
            "message": action.get("message", f"Please provide: {action.get('field')}")
        }
    
    def get_session_info(self) -> dict:
        """Get current session information"""
        stage = self.get_current_stage()
        return {
            "session_id": self.session_id,
            "workflow": self.workflow.name,
            "current_stage": self.current_stage,
            "available_tools": [t.name for t in stage.tools.values()],
            "can_transition_to": stage.transitions,
            "state_summary": {
                construct: len(data) if isinstance(data, (list, dict, str)) else 1 
                for construct, data in self.state.data.items()
            },
            "history_length": len(self.history)
        }
