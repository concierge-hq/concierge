"""UAIP server for Workflow.run()."""
from uaip.core.workflow import Workflow
from uaip.core.state_manager import InMemoryStateManager, initialize_state_manager
from uaip.serving.manager import SessionManager
from uaip.serving.endpoints import EndpointContext, create_uaip_app


def create_app(workflow: Workflow, title: str = None):
    """Create a UAIP server for a workflow."""
    state_manager = InMemoryStateManager()
    initialize_state_manager(state_manager)
    workflow.initialize()
    
    session_manager = SessionManager(workflow, state_manager=state_manager)
    context = EndpointContext(
        session_managers={workflow.name: session_manager},
        state_manager=state_manager
    )
    
    return create_uaip_app(
        context=context,
        title=title or f"UAIP: {workflow.name}",
        version="0.1.0"
    )


def run(
    workflow: Workflow,
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "info"
) -> None:
    """Run a UAIP workflow server."""
    import uvicorn

    def dim(s): return f"\033[2m{s}\033[0m"
    def cyan(s): return f"\033[36m{s}\033[0m"
    def bold(s): return f"\033[1m{s}\033[0m"
    
    app = create_app(workflow)
    
    print()
    print(f"{bold('UAIP Server')}: {cyan(workflow.name)}")
    print(f"  • {cyan(f'http://{host}:{port}')}")
    print("  • POST /initialize   (create session)")
    print("  • POST /execute      (method_call, stage_transition)")
    print(f"  {dim('Press Ctrl+C to stop')}")
    print()
    
    uvicorn.run(app, host=host, port=port, log_level=log_level)
