"""UAIP endpoint factory."""
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from uaip.core.state_manager import StateManager
from uaip.serving.manager import SessionManager
from uaip.serving import native_uaip


@dataclass
class EndpointContext:
    """Endpoint runtime context."""
    session_manager: SessionManager  # Single workflow per server
    state_manager: StateManager
    workflow_name: str  # For display/docs only


def create_uaip_app(
    context: EndpointContext,
    title: str = "UAIP Server",
    version: str = "0.1.0"
) -> FastAPI:
    """Create FastAPI app with UAIP routes."""
    app = FastAPI(title=title, version=version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    native_uaip.register_routes(app, context)
    
    return app
