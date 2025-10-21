"""Message templates - pure strings with placeholders.

Format and examples extracted from external/contracts.py
"""
import json
from concierge.external.contracts import (
    ToolCall,
    StageTransition,
    TerminateSession,
    TOOL_CALL_EXAMPLE,
    STAGE_TRANSITION_EXAMPLE,
    TERMINATE_SESSION_EXAMPLE
)


def _format_schema_simple(model_cls) -> str:
    """Generate simple format string from Pydantic schema"""
    schema = model_cls.model_json_schema()
    format_dict = {}
    
    for field_name, field_info in schema.get("properties", {}).items():
        if "const" in field_info:
            format_dict[field_name] = field_info["const"]
        else:
            field_type = field_info.get("type", "string")
            if field_type == "object":
                format_dict[field_name] = "{...}"
            elif field_type == "string":
                format_dict[field_name] = f"<{field_name}>"
            else:
                format_dict[field_name] = f"<{field_name}>"
    
    return json.dumps(format_dict)


# Generate format (schema) and example for each contract
TOOL_CALL_FORMAT = _format_schema_simple(ToolCall)
TOOL_CALL_EXAMPLE_JSON = TOOL_CALL_EXAMPLE.model_dump_json()

STAGE_TRANSITION_FORMAT = _format_schema_simple(StageTransition)
STAGE_TRANSITION_EXAMPLE_JSON = STAGE_TRANSITION_EXAMPLE.model_dump_json()

TERMINATE_SESSION_FORMAT = _format_schema_simple(TerminateSession)
TERMINATE_SESSION_EXAMPLE_JSON = TERMINATE_SESSION_EXAMPLE.model_dump_json()


HANDSHAKE_MESSAGE = """Welcome to {app_name} powered by Concierge.
{app_description}

Available workflows ({workflow_count}):
{workflows_list}

What would you like to do?
Respond with JSON:
{{
  "action": "select_workflow",
  "workflow_id": "workflow_name"
}}"""


STAGE_MESSAGE = """Workflow: {workflow_name}
Stage: {current_stage} (step {stage_index} of {total_stages})
Description: {stage_description}

Available tools:
{available_tools}

Next stages: {next_stages}
Previous stages: {previous_stages}

Current state:
{state}

What would you like to do?

1. Call a tool
Format: {tool_call_format}
Example: {tool_call_example}

2. Transition to another stage
Format: {stage_transition_format}
Example: {stage_transition_example}

3. End session
Format: {terminate_session_format}
Example: {terminate_session_example}"""


TRANSITION_RESULT_MESSAGE = """Successfully transitioned from '{from_stage}' to '{to_stage}'.

{stage_message}"""


TOOL_RESULT_MESSAGE = """Tool '{tool_name}' executed successfully.

Result:
{result}

{stage_message}"""


ERROR_MESSAGE = """Error: {message}

{context}"""

