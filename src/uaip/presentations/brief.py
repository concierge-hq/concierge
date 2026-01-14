"""Brief Presentation - minimal response with just result and current state."""
import json
import asyncio
from uaip.presentations.base import Presentation
from uaip.core.state_manager import get_state_manager


class BriefPresentation(Presentation):
    
    def render_text(self, orchestrator) -> str:
        """
        Render brief response with just the result and current state.
        
        Used for task calls and actions after handshake to save tokens.
        """
        current_stage = orchestrator.get_current_stage()
        
        lines = [
            self.content,
            "",
            f"Current stage: {current_stage.name}",
            f"State: {self._format_current_state(orchestrator)}",
            f"Available tasks: {self._format_available_tasks(current_stage)}",
            f"Available transitions: {self._format_available_transitions(current_stage)}",
        ]
        
        return "\n".join(lines)
    
    def render_json(self, orchestrator) -> dict:
        """
        Render response as structured JSON for LLM tool calling.
        Returns tasks and transitions as tools.
        """
        workflow = orchestrator.workflow
        current_stage = orchestrator.get_current_stage()
        
        tools = []
        for task_name, task in current_stage.tasks.items():
            tools.append(task.to_schema())
        
        if current_stage.transitions:
            stage_descriptions = {}
            for target_stage_name in current_stage.transitions:
                target_stage = workflow.get_stage(target_stage_name)
                stage_descriptions[target_stage_name] = target_stage.description
            
            tools.append({
                "name": "transition_stage",
                "description": f"Move to a different stage in the workflow. Available stages: {', '.join(current_stage.transitions)}",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target_stage": {
                            "type": "string",
                            "enum": current_stage.transitions,
                            "description": "The stage to transition to. " + "; ".join(
                                [f"{name}: {stage_descriptions[name]}" for name in current_stage.transitions]
                            )
                        }
                    },
                    "required": ["target_stage"]
                }
            })
        
        tools.append({
            "name": "terminate_session",
            "description": "End the current session",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for ending the session"
                    }
                },
                "required": []
            }
        })
        
        return {
            "content": self.content,
            "tools": tools
        }
    
    def _format_current_state(self, orchestrator) -> str:
        """
        Format current state variables.
        State is cached in orchestrator after each operation.
        """
        stage_state = getattr(orchestrator, 'current_stage_state', {})
        return json.dumps(stage_state)
    
    def _format_available_tasks(self, stage) -> str:
        """List available task names"""
        if not stage.tasks:
            return "none"
        return ", ".join(stage.tasks.keys())
    
    def _format_available_transitions(self, stage) -> str:
        """List available transition targets"""
        if not stage.transitions:
            return "none"
        return ", ".join(stage.transitions)

