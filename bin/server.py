import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "workers"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from concierge.server import start_server_from_config

# Example code, not invoked through concierge serve.
if __name__ == "__main__":
    config_file = Path(__file__).parent.parent / "configs" / "default.yaml"
    start_server_from_config(str(config_file))

