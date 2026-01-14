"""UAIP endpoint definitions."""
from dataclasses import dataclass
from typing import Dict

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from uaip.core.registry import get_registry
from uaip.core.state_manager import StateManager
from uaip.serving.manager import SessionManager


@dataclass
class EndpointContext:
    """Endpoint runtime context."""
    session_managers: Dict[str, SessionManager]
    state_manager: StateManager


def create_uaip_app(
    context: EndpointContext,
    title: str = "UAIP Server",
    version: str = "0.1.0"
) -> FastAPI:
    """Create FastAPI app with UAIP endpoints."""
    app = FastAPI(title=title, version=version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    def _get_session_manager(workflow_name: str) -> SessionManager:
        """Get session manager for workflow."""
        if workflow_name not in context.session_managers:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
        return context.session_managers[workflow_name]
    
    @app.get("/")
    async def root():
        """Server info."""
        return {
            "protocol": "UAIP",
            "version": version
        }
    
    @app.get("/api/workflows/{workflow_name}")
    async def get_workflow_detail(workflow_name: str):
        """Get workflow schema."""
        registry = get_registry()
        
        if not registry.has_workflow(workflow_name):
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
        
        workflow = registry.get_workflow(workflow_name)
        
        stages = {}
        for stage_name, stage in workflow.stages.items():
            stages[stage_name] = {
                "name": stage.name,
                "description": stage.description,
                "tasks": {
                    task_name: {
                        "name": task.name,
                        "description": task.description,
                        "parameters": task.to_schema().get("input_schema", {})
                    }
                    for task_name, task in stage.tasks.items()
                },
                "transitions": stage.transitions
            }
        
        return {
            "name": workflow.name,
            "description": workflow.description,
            "initial_stage": workflow.initial_stage,
            "stages": stages
        }
    
    @app.post("/initialize")
    async def initialize(request: Request):
        """Initialize a session. Returns session_id."""
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        
        workflow_name = body.get("workflow_name")
        if not workflow_name:
            raise HTTPException(status_code=400, detail="Missing 'workflow_name'")
        
        session_manager = _get_session_manager(workflow_name)
        
        registry = get_registry()
        workflow = registry.get_workflow(workflow_name)
        workflow.initialize()
        
        session_id = await session_manager.create_session()
        
        response = JSONResponse(content={
            "session_id": session_id,
            "workflow": workflow_name,
            "initial_stage": workflow.initial_stage
        })
        response.headers["X-Session-Id"] = session_id
        return response
    
    @app.post("/execute")
    async def execute(request: Request):
        """Execute an action. Requires X-Session-Id header."""
        session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
        
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        
        workflow_name = body.get("workflow_name")
        if not workflow_name:
            raise HTTPException(status_code=400, detail="Missing 'workflow_name'")
        
        session_manager = _get_session_manager(workflow_name)
        
        if session_id not in session_manager.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
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
        
        result = await session_manager.handle_request(session_id, message)
        
        return Response(
            content=result,
            media_type="application/json",
            headers={"X-Session-Id": session_id}
        )
    
    return app
