"""Server startup utilities - extracted from bin/server.py"""

import importlib
import importlib.util
import sys
from pathlib import Path

import uvicorn
import yaml

from concierge.core.postgres_state_manager import PostgreSQLStateManager
from concierge.core.registry import get_registry, register_workflow
from concierge.core.state_manager import (
    InMemoryStateManager,
    get_state_manager,
    initialize_state_manager,
)
from concierge.serving.api import app, initialize_api
from concierge.serving.manager import SessionManager


def start_server_from_config(config_path: str):
    """Start server by loading workflows from config file"""

    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text())
    config_dir = config_file.parent.resolve()

    state_mgr_type = config.get("server", {}).get("state_manager", "memory")
    if state_mgr_type == "postgres":
        db_config = config.get("database", {})
        state_mgr = PostgreSQLStateManager(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            database=db_config.get("name", "concierge"),
            user=db_config.get("user", "postgres"),
            password=db_config.get("password", ""),
        )
        print("[STATE] PostgreSQL")
    else:
        state_mgr = InMemoryStateManager()
        print("[STATE] In-Memory")

    initialize_state_manager(state_mgr)

    for idx, wf_config in enumerate(config.get("workflows", [])):
        workflow_path = config_dir / wf_config["path"]
        module_name = f"concierge_user_workflow_{idx}"
        spec = importlib.util.spec_from_file_location(module_name, workflow_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        WorkflowClass = getattr(module, wf_config["class"])
        register_workflow(WorkflowClass)
        print(f"[WORKFLOW] Registered: {WorkflowClass._workflow.name}")

    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8089)

    start_server(host=host, port=port, state_manager=state_mgr)


def start_server(host: str = None, port: int = None, state_manager=None):
    """Start server with registered workflows"""

    registry = get_registry()
    workflows = registry.list_workflows()

    session_managers = {w.name: SessionManager(registry.get_workflow(w.name)) for w in workflows}

    if state_manager is None:
        state_manager = get_state_manager()

    initialize_api(session_managers, tracker=None, state_manager=state_manager)

    print("=" * 60)
    print("Concierge Server")
    print(f"Workflows: {', '.join([w.name for w in workflows])}")
    print(f"Server: http://{host}:{port}")
    print("UI APIs: /api/workflows, /api/stats")
    print("LLM API: POST /execute")
    print("=" * 60)

    uvicorn.run(app, host=host, port=port)
