"""
Orchestrator: Core business logic for workflow execution.
"""
from dataclasses import dataclass, field
from typing import Optional

from uaip.core.state import State
from uaip.core.stage import Stage
from uaip.core.workflow import Workflow
from uaip.core.actions import Action, MethodCallAction, StageTransitionAction
from uaip.core.results import Result, TaskResult, TransitionResult, ErrorResult, StateInputRequiredResult
from uaip.presentations import ComprehensivePresentation, BriefPresentation, StateInputPresentation
from uaip.external.contracts import ACTION_METHOD_CALL, ACTION_STAGE_TRANSITION
from uaip.core.state_manager import get_state_manager


@dataclass
class Orchestrator:
    """
    Orchestrator handles the core business logic of workflow execution.
    State is managed via state_manager, not stored here.
    """
    workflow: Workflow
    session_id: str
    history: list = field(default_factory=list)
    pending_transition: Optional[str] = None
    
    def __post_init__(self):
        """Initialize orchestrator (session already created by SessionManager)"""
        self.history = []
        self.pending_transition = None
        self.required_state_fields = []
        self.last_task_result = None  # Store for render_json
        self.did_auto_transition = False  # Track if we moved to a new stage 
    
    def get_current_stage(self) -> Stage:
        """Get current stage object"""
        return self.workflow.get_cursor()
    
    async def execute_method_call(self, action: MethodCallAction) -> Result:
        """Execute a method call action"""
        stage = self.get_current_stage()
        
        result = await self.workflow.call_task(stage.name, action.task_name, action.args, self.session_id)
        
        if result["type"] == "task_result":
            self.history.append({
                "action": ACTION_METHOD_CALL,
                "task": action.task_name,
                "args": action.args,
                "result": result["result"]
            })
            
            state_mgr = get_state_manager()
            self.current_stage_state = await state_mgr.get_stage_state(self.session_id, stage.name)
            
            # Store for render_json
            self.last_task_result = result["result"]
            self.did_auto_transition = False  # Reset before checking
            
            # Auto-transition to next stage with state propagation
            if len(stage.transitions) == 1:
                next_stage = stage.transitions[0]
                
                # Propagate state from current stage to next stage
                propagation_config = self.workflow.get_propagation_config(stage.name, next_stage)
                if propagation_config != "none":
                    source_state_dict = await state_mgr.get_stage_state(self.session_id, stage.name)
                    
                    if propagation_config == "all":
                        state_to_transfer = source_state_dict
                    elif isinstance(propagation_config, list):
                        state_to_transfer = {k: v for k, v in source_state_dict.items() if k in propagation_config}
                    else:
                        state_to_transfer = {}
                    
                    if state_to_transfer:
                        await state_mgr.update_stage_state(self.session_id, next_stage, state_to_transfer)
                
                self.workflow.transition_to(next_stage)
                self.did_auto_transition = True
            
            return TaskResult(
                task_name=action.task_name,
                result=result["result"],
                presentation_type=ComprehensivePresentation
            )
        else:
            return ErrorResult(
                message=result.get("message", result.get("error", "Unknown error")),
                presentation_type=ComprehensivePresentation
            )
    
    async def execute_stage_transition(self, action: StageTransitionAction) -> Result:
        """Execute a stage transition action"""
        stage = self.get_current_stage()
        
        # Get current states for validation
        state_mgr = get_state_manager()
        global_state_dict = await state_mgr.get_global_state(self.session_id)
        source_state_dict = await state_mgr.get_stage_state(self.session_id, stage.name)
        
        global_state = State(global_state_dict)
        source_state = State(source_state_dict)
        
        validation = self.workflow.validate_transition(
            stage.name,
            action.target_stage,
            global_state,
            source_state
        )
        
        if not validation["valid"]:
            if validation.get("reason") == "missing_state":
                self.pending_transition = action.target_stage
                self.required_state_fields = validation["missing"] 
                return StateInputRequiredResult(
                    target_stage=action.target_stage,
                    message=f"To transition to '{action.target_stage}', please provide: {', '.join(validation['missing'])}",
                    required_fields=validation["missing"],
                    presentation_type=StateInputPresentation  
                )
            else:
                return ErrorResult(
                    message=validation["error"],
                    allowed=validation.get("allowed"),
                    presentation_type=ComprehensivePresentation
                )
        
        target = self.workflow.transition_to(action.target_stage)
        self.pending_transition = None
        
        state_mgr = get_state_manager()
        propagation_config = self.workflow.get_propagation_config(stage.name, action.target_stage)
        
        if propagation_config != "none":
            source_state_dict = await state_mgr.get_stage_state(self.session_id, stage.name)
            
            if propagation_config == "all":
                state_to_transfer = source_state_dict
            elif isinstance(propagation_config, list):
                state_to_transfer = {
                    key: value for key, value in source_state_dict.items()
                    if key in propagation_config
                }
            else:
                state_to_transfer = {}
            
            if state_to_transfer:
                await state_mgr.update_stage_state(
                    self.session_id,
                    action.target_stage,
                    state_to_transfer
                )
        
        # Update current stage in state_manager
        await state_mgr.update_current_stage(self.session_id, action.target_stage)
        
        self.history.append({
            "action": ACTION_STAGE_TRANSITION,
            "from": stage.name,
            "to": action.target_stage
        })
        
        return TransitionResult(
            from_stage=stage.name,
            to_stage=action.target_stage,
            presentation_type=ComprehensivePresentation
        )
    
    async def populate_state(self, state_data: dict) -> None:
        """
        Store provided state in current stage's state via state_manager.
        User will manually request transition again after this.
        """
        current_stage = self.get_current_stage()
        state_mgr = get_state_manager()
        await state_mgr.update_stage_state(
            self.session_id,
            current_stage.name,
            state_data
        )
        
        # Clear required state fields after providing
        self.required_state_fields = []
    
    async def get_session_info(self) -> dict:
        """Get current session information"""
        stage = self.get_current_stage()
        state_mgr = get_state_manager()
        global_state = await state_mgr.get_global_state(self.session_id)
        
        return {
            "session_id": self.session_id,
            "workflow": self.workflow.name,
            "current_stage": stage.name,
            "available_tasks": [t.name for t in stage.tasks.values()],
            "can_transition_to": stage.transitions,
            "state_summary": {
                construct: len(data) if isinstance(data, (list, dict, str)) else 1 
                for construct, data in global_state.items()
            },
            "history_length": len(self.history)
        }

