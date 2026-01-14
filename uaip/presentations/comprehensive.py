"""Comprehensive Presentation - full context with stage, tasks, state, etc."""
import json
import asyncio
from uaip.presentations.base import Presentation
from uaip.external.contracts import (
    TaskCall, 
    StageTransition,
    ACTION_METHOD_CALL,
    ACTION_STAGE_TRANSITION
)
from uaip.core.state_manager import get_state_manager


class ComprehensivePresentation(Presentation):
    
    def render_text(self, orchestrator) -> str:
        """
        Render comprehensive response with full context.
        
        Fetches all metadata from orchestrator and formats it with the content.
        """
        workflow = orchestrator.workflow
        current_stage = orchestrator.get_current_stage()
        
        lines = [
            "=" * 80,
            "RESPONSE:",
            self.content,
            "",
            "=" * 80,
            "ADDITIONAL CONTEXT:",
            "",
            f"WORKFLOW: {workflow.name}",
            f"Description: {workflow.description}",
            "",
            "STRUCTURE:",
            self._format_stages_structure(workflow),
            "",
            f"CURRENT POSITION: {current_stage.name}",
            "",
            "CURRENT STATE:",
            self._format_current_state(orchestrator),
            "",
            "YOU MAY CHOOSE THE FOLLOWING ACTIONS:",
            "",
            "1. ACTION CALLS (Tasks):",
            self._format_tasks(current_stage),
            "",
            "2. STAGE CALLS (Transitions):",
            self._format_transitions(current_stage),
            "",
            "You must ONLY respond with a single JSON. Do not add comments or extra text.",
            "=" * 80,
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
    
    def _format_stages_structure(self, workflow) -> str:
        """Format the workflow stages structure"""
        stages_list = []
        for stage_name in workflow.stages.keys():
            stages_list.append(f"  - {stage_name}")
        return "\n".join(stages_list) if stages_list else "  (no stages)"
    
    def _format_current_state(self, orchestrator) -> str:
        """
        Format current state variables.
        State is cached in orchestrator after each operation.
        """
        stage_state = getattr(orchestrator, 'current_stage_state', {})
        return json.dumps(stage_state, indent=2)
    
    def _format_tasks(self, stage) -> str:
        """Format available tasks with descriptions and call format"""
        if not stage.tasks:
            return "  No tasks available"
        
        task_lines = []
        for task_name, task in stage.tasks.items():
            task_schema = task.to_schema()
            task_lines.append(f"  Task: {task_name}")
            task_lines.append(f"    Description: {task.description}")
            task_lines.append(f"    Call Format:")
            
            example_call = TaskCall(
                action=ACTION_METHOD_CALL,
                task=task_name,
                args=self._generate_example_args(task_schema["input_schema"])
            )
            task_lines.append(f"      {json.dumps(example_call.model_dump(), indent=6)}")
            task_lines.append("")
        
        return "\n".join(task_lines)
    
    def _format_transitions(self, stage) -> str:
        """Format available transitions with exact JSON format"""
        if not stage.transitions:
            return "  No transitions available"
        
        transition_lines = []
        for target_stage in stage.transitions:
            transition_lines.append(f"  Transition to: {target_stage}")
            
            transition_call = StageTransition(
                action=ACTION_STAGE_TRANSITION,
                stage=target_stage
            )
            transition_lines.append(f"    {json.dumps(transition_call.model_dump())}")
            transition_lines.append("")
        
        return "\n".join(transition_lines)
    
    def _generate_example_args(self, input_schema) -> dict:
        """Generate example arguments from input schema"""
        if not input_schema or "properties" not in input_schema:
            return {}
        
        example_args = {}
        for prop_name, prop_schema in input_schema.get("properties", {}).items():
            prop_type = prop_schema.get("type", "string")
            
            if prop_type == "string":
                example_args[prop_name] = f"<{prop_name}>"
            elif prop_type == "integer":
                example_args[prop_name] = 0
            elif prop_type == "number":
                example_args[prop_name] = 0.0
            elif prop_type == "boolean":
                example_args[prop_name] = True
            elif prop_type == "array":
                example_args[prop_name] = []
            elif prop_type == "object":
                example_args[prop_name] = {}
            else:
                example_args[prop_name] = f"<{prop_name}>"
        
        return example_args