"""Stage message communication."""
import json
from concierge.communications.base import Communications
from concierge.communications.messages import (
    STAGE_MESSAGE,
    TASK_CALL_FORMAT,
    TASK_CALL_EXAMPLE_JSON,
    STAGE_TRANSITION_FORMAT,
    STAGE_TRANSITION_EXAMPLE_JSON,
    TERMINATE_SESSION_FORMAT,
    TERMINATE_SESSION_EXAMPLE_JSON
)
from concierge.core.stage import Stage
from concierge.core.workflow import Workflow
from concierge.core.state import State


class StageMessage(Communications):
    """Message for stage execution context"""
    
    def _build_tasks_section(self, stage: Stage) -> str:
        """Build detailed tasks section with descriptions and arguments"""
        if not stage.tasks:
            return "None"
        
        tasks_lines = []
        for task in stage.tasks.values():
            schema = task.to_schema()
            input_schema = schema.get("input_schema", {})
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])
            
            params = []
            for param_name, param_info in properties.items():
                if param_name in ['self', 'state']:
                    continue
                
                param_type = param_info.get("type", "any")
                is_required = param_name in required
                param_str = f"{param_name}: {param_type}"
                if not is_required:
                    param_str += " (optional)"
                params.append(param_str)
            
            params_str = ", ".join(params) if params else ""
            task_line = f"  • {task.name}({params_str})"
            if task.description:
                task_line += f" - {task.description}"
            tasks_lines.append(task_line)
            
            for param_name, param_info in properties.items():
                if param_name in ['self', 'state']:
                    continue
                
                param_desc = param_info.get("description", "")
                examples = param_info.get("examples", [])
                
                detail_parts = []
                if param_desc:
                    detail_parts.append(param_desc)
                if examples:
                    examples_str = ", ".join(f'"{ex}"' if isinstance(ex, str) else str(ex) for ex in examples[:3])
                    detail_parts.append(f"e.g., {examples_str}")
                
                if detail_parts:
                    tasks_lines.append(f"      - {param_name}: {' - '.join(detail_parts)}")
        
        return "\n".join(tasks_lines)
    
    def render(self, stage: Stage, workflow: Workflow, state: State) -> str:
        """Render stage message with available actions"""
        stage_index = list(workflow.stages.keys()).index(stage.name) + 1
        
        return STAGE_MESSAGE.format(
            workflow_name=workflow.name,
            workflow_description=workflow.description or "",
            current_stage=stage.name,
            stage_index=stage_index,
            total_stages=len(workflow.stages),
            stage_description=stage.description,
            available_tasks=self._build_tasks_section(stage),
            next_stages=', '.join(stage.transitions) if stage.transitions else 'None',
            previous_stages='None', 
            state=json.dumps(state.data, indent=2),
            task_call_format=TASK_CALL_FORMAT,
            task_call_example=TASK_CALL_EXAMPLE_JSON,
            stage_transition_format=STAGE_TRANSITION_FORMAT,
            stage_transition_example=STAGE_TRANSITION_EXAMPLE_JSON,
            terminate_session_format=TERMINATE_SESSION_FORMAT,
            terminate_session_example=TERMINATE_SESSION_EXAMPLE_JSON
        )

