from typing import Any, Dict
from fastmcp import FastMCP

from uaip.core.state import State


_mcp_state: Dict[str, Any] = {}
def create_mcp_server(workflow) -> FastMCP:
    mcp = FastMCP(workflow.name)
    
    for stage_name, stage in workflow.stages.items():
        for task_name, task in stage.tasks.items():
            _register_tool(mcp, stage_name, task_name, task)
    
    return mcp


def _register_tool(mcp: FastMCP, stage_name: str, task_name: str, task) -> None:
    # Get the original bound method and wrap it
    original_func = task.func
    
    # Create a proper wrapper with correct signature by using exec
    # This is the only reliable way to dynamically create typed signatures
    import inspect
    from typing import get_type_hints
    
    sig = inspect.signature(original_func)
    params = []
    param_names = []
    
    for name, param in sig.parameters.items():
        if name in ('self', 'state'):
            continue
        param_names.append(name)
        
        # Get annotation string
        if param.annotation != inspect.Parameter.empty:
            ann = param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)
        else:
            ann = 'str'
        
        # Get default
        if param.default != inspect.Parameter.empty:
            params.append(f"{name}: {ann} = {repr(param.default)}")
        else:
            params.append(f"{name}: {ann}")
    
    params_str = ", ".join(params)
    args_str = ", ".join([f"{n}={n}" for n in param_names])
    
    # Build the function code
    func_code = f'''
async def {stage_name}_{task_name}({params_str}) -> dict:
    """{task.description or ''}"""
    global _mcp_state
    state = State(_mcp_state)
    result = await task.execute(state, {args_str})
    _mcp_state.update(state.data)
    return result or {{"status": "ok"}}
'''
    
    # Execute to create the function
    local_vars = {'task': task, 'State': State, '_mcp_state': _mcp_state}
    exec(func_code, local_vars)
    tool_func = local_vars[f"{stage_name}_{task_name}"]
    
    # Register with FastMCP
    mcp.tool(name=f"{stage_name}_{task_name}", description=task.description)(tool_func)
