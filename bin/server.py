import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.simple_stock import StockWorkflow

from concierge.core.registry import register_workflow
from concierge.server import start_server
from examples.zillow.workflow import ZillowWorkflow

# Example code, not invoked through concierge serve.
if __name__ == "__main__":
    register_workflow(StockWorkflow)
    register_workflow(ZillowWorkflow)

    start_server()
