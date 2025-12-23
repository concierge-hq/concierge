"""Language Engine: Parses JSON input and routes to orchestrator."""
import json
from concierge.core.workflow import Workflow
from concierge.core.actions import MethodCallAction, StageTransitionAction
from concierge.core.results import Result, TaskResult, TransitionResult, ErrorResult, StateInputRequiredResult, StateUpdateResult
from concierge.core.state_manager import get_state_manager
from concierge.engine.orchestrator import Orchestrator
from concierge.presentations import ComprehensivePresentation
from concierge.external.contracts import (
    ACTION_METHOD_CALL,
    ACTION_STAGE_TRANSITION,
    ACTION_STATE_INPUT,
    ACTION_TERMINATE_SESSION
)
from concierge.communications import (
    TaskResultMessage,
    TransitionResultMessage,
    ErrorMessage,
    StateInputRequiredMessage,
    StateUpdateMessage
)


class LanguageEngine:
    """
    Language engine that receives JSON input and routes to orchestrator.
    Handles parsing, execution, and message formatting.
    Creates and manages its own orchestrator instance.
    """
    
    def __init__(self, workflow: Workflow, session_id: str, user_id: str = None, output_format: str = "json"):
        """
        Initialize language engine.
        
        Args:
            workflow: Workflow to execute
            session_id: Unique session identifier
            user_id: User identifier for multi-user support
            output_format: Output format - "text" or "json" (default: "text")
        """
        self.workflow = workflow
        self.session_id = session_id
        self.user_id = user_id
        self.orchestrator = Orchestrator(workflow, session_id)
        self.output_format = output_format
    
    def get_initial_message(self) -> str:
        """Get initial handshake message for new session"""
        result = StateUpdateResult(
            message="Session started successfully.",
            presentation_type=ComprehensivePresentation
        )
        return self._format_state_update(result)
    
    def get_error_message(self, error_text: str) -> str:
        """Format an error message"""
        return json.dumps({"error": error_text})
    
    def get_termination_message(self, session_id: str) -> str:
        """Format a termination message"""
        return json.dumps({"status": "terminated", "session_id": session_id})
    
    async def process(self, llm_json: dict) -> str:
        """
        Process LLM JSON input and return formatted message.
        Handles all exceptions internally.
        
        Expected formats:
        - {"action": "handshake"}
        - {"action": "method_call", "task": "task_name", "args": {...}}
        - {"action": "stage_transition", "stage": "stage_name"}
        - {"action": "state_input", "state_updates": {"field1": "value1", ...}}
        - {"action": "terminate_session", "reason": "optional_reason"}
        """
        try:
            action_type = llm_json.get("action")
            
            if action_type == "handshake":
                return self.get_initial_message()
            
            elif action_type == ACTION_METHOD_CALL:
                action = MethodCallAction(
                    task_name=llm_json["task"],
                    args=llm_json.get("args", {})
                )
                result = await self.orchestrator.execute_method_call(action)
                if isinstance(result, TaskResult):
                    return self._format_task_result(result)
                return self._format_error_result(result)
            
            elif action_type == ACTION_STAGE_TRANSITION:
                action = StageTransitionAction(
                    target_stage=llm_json["stage"]
                )
                result = await self.orchestrator.execute_stage_transition(action)
                if isinstance(result, TransitionResult):
                    return self._format_transition_result(result)
                elif isinstance(result, StateInputRequiredResult):
                    return self._format_state_input_required(result)
                return self._format_error_result(result)
            
            elif action_type == ACTION_STATE_INPUT:
                state_data = llm_json.get("state_updates", {})
                await self.orchestrator.populate_state(state_data)
                result = StateUpdateResult(
                    message="State populated successfully.",
                    presentation_type=ComprehensivePresentation
                )
                return self._format_state_update(result)
            
            elif action_type == ACTION_TERMINATE_SESSION:
                state_mgr = get_state_manager()
                await state_mgr.update_session_status(self.session_id, 'completed')
                return self.get_termination_message(self.session_id)
            
            else:
                return self._format_error_result(ErrorResult(
                    message=f"Unknown action type: {action_type}",
                    presentation_type=ComprehensivePresentation
                ))
        except Exception as e:
            print(f"[LANGUAGE ENGINE] Error in session {self.session_id}: {e}")
            import traceback
            traceback.print_exc()
            
            state_mgr = get_state_manager()
            await state_mgr.update_session_status(self.session_id, 'failed')
            return self.get_error_message(str(e))
    
    def _render(self, presentation):
        """Render presentation based on output_format"""
        if self.output_format == "json":
            result_dict = presentation.render_json(self.orchestrator)
            return json.dumps(result_dict)
        return presentation.render_text(self.orchestrator)
    
    def _format_task_result(self, result: TaskResult):
        """Format task execution result with current stage context"""
        content = TaskResultMessage().render(result)
        presentation = result.presentation_type(content)
        return self._render(presentation)
    
    def _format_transition_result(self, result: TransitionResult):
        """Format transition result with new stage context"""
        content = TransitionResultMessage().render(result)
        presentation = result.presentation_type(content)
        return self._render(presentation)
    
    def _format_error_result(self, result: ErrorResult):
        """Format error message"""
        content = ErrorMessage().render(result)
        presentation = result.presentation_type(content)
        return self._render(presentation)
    
    def _format_state_input_required(self, result: StateInputRequiredResult):
        """Format state input required message"""
        content = StateInputRequiredMessage().render(result)
        presentation = result.presentation_type(content)
        return self._render(presentation)
    
    def _format_state_update(self, result: StateUpdateResult):
        """Format state update message"""
        content = StateUpdateMessage().render(result)
        presentation = result.presentation_type(content)
        return self._render(presentation)

