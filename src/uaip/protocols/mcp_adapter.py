"""
MCP Adapter - Exposes Concierge workflows via Model Context Protocol.

Key difference from AIP:
- MCP exposes ALL tasks as tools (flat list)
- AIP exposes only current stage tasks with stage navigation
"""
from typing import Any, Dict, List, Optional
from uaip.core.workflow import Workflow
from uaip.core.state import State
from uaip.core.state_manager import StateManager


def get_mcp_tools(workflow: Workflow) -> List[Dict[str, Any]]:
    """
    Get all workflow tasks as MCP-style tool definitions.
    
    Returns a flat list of all tools across all stages.
    """
    tools = []
    
    for stage_name, stage in workflow.stages.items():
        for task_name, task in stage.tasks.items():
            schema = task.to_schema()
            
            tools.append({
                "name": f"{stage_name}_{task_name}",
                "description": f"[{stage_name}] {task.description}",
                "inputSchema": schema.get("input_schema", {"type": "object", "properties": {}})
            })
    
    return tools


def get_mcp_tool_count(workflow: Workflow) -> int:
    """Count total tools exposed via MCP."""
    return sum(len(stage.tasks) for stage in workflow.stages.values())


async def execute_mcp_tool(
    workflow: Workflow, 
    tool_name: str, 
    arguments: Dict[str, Any],
    session_id: str,
    state_manager: StateManager
) -> Dict[str, Any]:
    """
    Execute an MCP tool call on the workflow using Global State.
    
    Tool name format: {stage_name}_{task_name}
    Stage names may contain underscores, so we match against known stages.
    """
    # Find the matching stage by trying each known stage as a prefix
    stage_name = None
    task_name = None
    for known_stage in workflow.stages.keys():
        prefix = f"{known_stage}_"
        if tool_name.startswith(prefix):
            stage_name = known_stage
            task_name = tool_name[len(prefix):]
            break
    
    if not stage_name or not task_name:
        return {"error": f"Invalid tool name format: {tool_name}"}
    
    stage = workflow.stages.get(stage_name)
    if not stage:
        return {"error": f"Stage not found: {stage_name}"}
    
    task = stage.tasks.get(task_name)
    if not task:
        return {"error": f"Task not found: {task_name}"}
    
    # 1. Load GLOBAL state (shared across all tools in MCP mode)
    try:
        global_data = await state_manager.get_global_state(session_id)
    except Exception:
        global_data = {}

    state = State(dict(global_data))  # Copy to avoid mutation issues
    
    try:
        # 2. Execute Task
        result = await task.execute(state, **arguments)
        
        # 3. Flush events to benchmark_logs immediately
        events = state.flush_events()
        if events:
            for e in events:
                e["stage"] = stage_name
            await state_manager.save_benchmark_logs(session_id, events)
        
        # 4. Save remaining state back to GLOBAL state
        await state_manager.update_global_state(session_id, state.data)
            
        return result or {}
    except Exception as e:
        return {"error": str(e)}

