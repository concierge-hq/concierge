"""Concierge REST API"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from concierge.core.registry import get_registry
from concierge.core.workflow import Workflow
from concierge.serving.manager import SessionManager


@dataclass
class APIContext:
    """API runtime context"""
    session_managers: Dict[str, SessionManager]
    tracker: Optional[Any] = None
    state_manager: Optional[Any] = None 


_context: Optional[APIContext] = None


def initialize_api(session_managers: Dict[str, SessionManager], tracker: Optional[Any] = None, state_manager: Optional[Any] = None):
    """Initialize API with runtime dependencies"""
    global _context
    _context = APIContext(session_managers=session_managers, tracker=tracker, state_manager=state_manager)


def get_context() -> APIContext:
    """Get API context"""
    if _context is None:
        raise RuntimeError("API not initialized")
    return _context


app = FastAPI(title="Concierge API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize state manager in Uvicorn's event loop"""
    context = get_context()
    await context.state_manager.initialize()
    print("[STARTUP] State manager initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Close state manager resources on shutdown"""
    context = get_context()
    await context.state_manager.close()
    print("[SHUTDOWN] State manager closed")


web_dist = Path(__file__).parent.parent.parent.parent / "web" / "dist"
print(f"[UI] Mounting web UI from: {web_dist}")
app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="static")
    
@app.get("/")
async def serve_ui():
    """Serve the web UI"""
    return FileResponse(str(web_dist / "index.html"))


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get platform statistics"""
    registry = get_registry()
    context = get_context()
    
    # Count workflows
    workflow_count = len(list(registry.list_workflows()))
    
    # TODO: Get real execution stats from tracker
    # For now, return mock data that can be replaced with real metrics
    return {
        "workflows": {
            "total": workflow_count,
            "active": workflow_count
        },
        "executions": {
            "total": 0,  # TODO: Query from tracker
            "success": 0,
            "failed": 0
        },
        "performance": {
            "avg_duration_ms": 0,  # TODO: Calculate from tracker
            "success_rate": 0.0
        }
    }


@app.get("/api/workflows")
async def list_workflows() -> Dict[str, Any]:
    """List all registered workflows"""
    registry = get_registry()
    workflows = []
    
    for metadata in registry.list_workflows():
        workflow = registry.get_workflow(metadata.name)
        workflows.append({
            "name": metadata.name,
            "description": metadata.description,
            "stages": metadata.stages,
            "initial_stage": workflow.initial_stage
        })
    
    return {"workflows": workflows}


@app.get("/api/workflows/{workflow_name}")
async def get_workflow_details(workflow_name: str) -> Dict[str, Any]:
    """Get complete workflow definition and graph structure"""
    registry = get_registry()
    
    if not registry.has_workflow(workflow_name):
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
    
    workflow = registry.get_workflow(workflow_name)
    
    stages = {}
    for stage_name, stage in workflow.stages.items():
        tasks = {
            task_name: {
                "name": task.name,
                "description": task.description
            }
            for task_name, task in stage.tasks.items()
        }
        stages[stage_name] = {
            "name": stage.name,
            "description": stage.description,
            "tasks": tasks,
            "transitions": stage.transitions
        }
    
    nodes = []
    edges = []
    stage_list = list(workflow.stages.values())
    for index, stage in enumerate(stage_list):
        nodes.append({
            "id": stage.name,
            "data": {
                "label": stage.name,
                "description": stage.description,
                "tasks": list(stage.tasks.keys()),
                "isInitial": stage.name == workflow.initial_stage
            },
            "position": {
                "x": (index % 3) * 250,
                "y": (index // 3) * 200
            }
        })
        for target_stage in stage.transitions:
            edges.append({
                "id": f"{stage.name}->{target_stage}",
                "source": stage.name,
                "target": target_stage
            })
    
    return {
        "name": workflow.name,
        "description": workflow.description,
        "stages": stages,
        "graph": {"nodes": nodes, "edges": edges}
    }


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """Get execution history for a session"""
    context = get_context()
    
    if context.tracker is None:
        raise HTTPException(
            status_code=503,
            detail="History tracking requires database configuration"
        )
    
    try:
        history = await context.tracker.get_session_history(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    steps = [
        {
            "sequence": step.sequence_number,
            "timestamp": step.timestamp.isoformat(),
            "action_type": step.action_type,
            "stage_name": step.stage_name,
            "task_name": step.task_name,
            "state_after": step.state_after,
            "duration_ms": step.duration_ms
        }
        for step in history
    ]
    
    return {
        "session_id": session_id,
        "step_count": len(steps),
        "steps": steps
    }


@app.get("/api/statistics")
async def get_statistics() -> Dict[str, Any]:
    """Get global statistics across all workflows"""
    context = get_context()
    registry = get_registry()
    
    active_session_count = sum(
        len(manager.get_active_sessions())
        for manager in context.session_managers.values()
    )
    
    workflow_list = list(registry.list_workflows())
    workflow_stats = []
    
    for metadata in workflow_list:
        stats = {"name": metadata.name}
        
        if context.tracker is not None:
            try:
                db_stats = await context.tracker.get_workflow_stats(metadata.name)
                stats.update(db_stats)
            except Exception:
                pass
        
        workflow_stats.append(stats)
    
    return {
        "total_workflows": len(workflow_list),
        "active_sessions": active_session_count,
        "workflows": workflow_stats
    }


@app.post("/execute")
async def execute_workflow(http_request: Request):
    """Execute workflow action (for LLM clients)"""
    context = get_context()
    
    body = await http_request.json()
    workflow_name = body.get("workflow_name")
    
    if not workflow_name:
        managers = context.session_managers
        if len(managers) == 1:
            workflow_name = list(managers.keys())[0]
        else:
            raise HTTPException(
                status_code=400,
                detail="workflow_name required when multiple workflows available"
            )
    
    session_manager = context.session_managers.get(workflow_name)
    if not session_manager:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
    
    session_id = http_request.headers.get("x-session-id")
    action = body.get("action")
    
    if not session_id:
        if action == "handshake":
            session_id = await session_manager.create_session()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Session ID required for action '{action}'. Send handshake first: {{'action': 'handshake', 'workflow_name': '{workflow_name}'}}"
            )
    else:
        if session_id not in session_manager.sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found. Send handshake to create new session."
            )
    
    try:
        result = await session_manager.handle_request(session_id, body)
    except Exception as e:
        import traceback
        print("\n" + "="*80)
        print(f"[EXECUTE ERROR] Workflow: {workflow_name} | Action: {action} | Session: {session_id}")
        print(f"[EXECUTE ERROR] Exception: {type(e).__name__}: {e}")
        print("-"*80)
        traceback.print_exc()
        print("="*80 + "\n")
        raise
    
    return Response(
        content=result,
        media_type="application/json",
        headers={"X-Session-Id": session_id}
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}
