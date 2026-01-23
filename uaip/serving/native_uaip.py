"""Native UAIP protocol routes."""
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from uaip.core.registry import get_registry


def register_routes(app: FastAPI, context) -> None:
    """Register UAIP protocol routes on the app."""
    
    @app.get("/")
    async def root():
        """Server info."""
        return {
            "protocol": "UAIP",
            "version": "0.1.0",
            "workflow": context.workflow_name
        }
    
    @app.post("/initialize")
    async def initialize():
        """Initialize a new session. Returns session_id and the first available tool."""
        registry = get_registry()
        workflow = registry.get_workflow(context.workflow_name)
        workflow.initialize()
        
        session_id = await context.session_manager.create_session()
        
        # Get only the first task from initial stage
        initial_stage = workflow.get_stage(workflow.initial_stage)
        first_task = list(initial_stage.tasks.values())[0]
        
        response = JSONResponse(content={
            "session_id": session_id,
            "workflow": context.workflow_name,
            "stage": workflow.initial_stage,
            "tool": first_task.to_schema()
        })
        response.headers["X-Session-Id"] = session_id
        return response
    
    @app.post("/execute")
    async def execute(request: Request):
        """Execute an action. Requires X-Session-Id header."""
        session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
        
        if session_id not in context.session_manager.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        
        action = body.get("action")
        if not action:
            raise HTTPException(status_code=400, detail="Missing 'action'")
        
        message = {"action": action}
        
        if action == "method_call":
            if not body.get("task"):
                raise HTTPException(status_code=400, detail="Missing 'task'")
            message["task"] = body["task"]
            message["args"] = body.get("args", {})
        
        elif action == "stage_transition":
            if not body.get("stage"):
                raise HTTPException(status_code=400, detail="Missing 'stage'")
            message["stage"] = body["stage"]
        
        elif action == "state_input":
            message["state_updates"] = body.get("state_updates", {})
        
        result = await context.session_manager.handle_request(session_id, message)
        
        return Response(
            content=result,
            media_type="application/json",
            headers={"X-Session-Id": session_id}
        )
