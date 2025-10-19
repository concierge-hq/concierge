"""
Orchestrator: Core business logic for workflow execution.
"""
from typing import Optional
from dataclasses import dataclass, field

from concierge.core.state import State
from concierge.core.stage import Stage
from concierge.core.workflow import Workflow


@dataclass
class Orchestrator:
    """
    Orchestrator handles the core business logic of workflow execution.
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
        """Handle tool execution - delegates to workflow"""
        tool_name = action.get("tool")
        args = action.get("args", {})
        
        # Delegate to workflow
        result = await self.workflow.call_tool(self.current_stage, tool_name, args)
        
        # Track history
        if result["type"] == "tool_result":
            self.history.append({
                "action": "tool",
                "tool": tool_name,
                "args": args,
                "result": result["result"]
            })
        
        return result
    
    async def _handle_transition(self, action: dict, stage: Stage) -> dict:
        """Handle stage transition - delegates validation to workflow"""
        target_stage_name = action.get("stage")
        
        # Delegate validation to workflow
        validation = self.workflow.validate_transition(
            self.current_stage,
            target_stage_name,
            self.state
        )
        
        if not validation["valid"]:
            if "missing" in validation:
                return {
                    "type": "elicit_required",
                    "message": validation["error"],
                    "missing": validation["missing"]
                }
            return {
                "type": "error",
                "message": validation["error"],
                "allowed": validation.get("allowed", [])
            }
        
        # Perform transition (fresh isolated state for new stage)
        target = self.workflow.get_stage(target_stage_name)
        target.local_state = State()
        self.current_stage = target_stage_name
        self.history.append({
            "action": "transition",
            "from": stage.name,
            "to": target_stage_name
        })
        
        return {
            "type": "transitioned",
            "from": stage.name,
            "to": target_stage_name,
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

