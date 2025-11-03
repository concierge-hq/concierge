"""Centralized configuration for Concierge"""
import yaml
from pathlib import Path

_config_path = Path(__file__).parent.parent.parent / "configs" / "default.yaml"
_config = yaml.safe_load(_config_path.read_text())

SERVER_HOST = _config["server"]["host"]
SERVER_PORT = _config["server"]["port"]

DB_HOST = _config["database"]["host"]
DB_PORT = _config["database"]["port"]
DB_NAME = _config["database"]["name"]
DB_USER = _config["database"]["user"]
DB_PASSWORD = _config["database"]["password"]

SERVICES = _config["services"]

