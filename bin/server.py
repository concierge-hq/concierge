import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from concierge.serving.api import app, initialize_api
from concierge.serving.manager import SessionManager
from concierge.core.registry import get_registry
from concierge.config import SERVER_HOST, SERVER_PORT

from examples.simple_stock import StockWorkflow
from examples.zillow.workflow import ZillowWorkflow

if __name__ == "__main__":
    registry = get_registry()
    workflows = registry.list_workflows()
        
    session_managers = {
        w.name: SessionManager(registry.get_workflow(w.name))
        for w in workflows
    }
    
    initialize_api(session_managers, tracker=None)
    
    print(f"   Listening: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"   UI APIs: /api/workflows, /api/statistics")
    print(f"   LLM API: POST /execute")
    print()
    
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)

