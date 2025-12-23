#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONFIG_FILE="${CONFIG_FILE:-configs/default.yaml}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

read -r ROUTER_HOST ROUTER_PORT DB_HOST DB_PORT DB_USER <<< $(python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(
    config['router']['host'],
    config['router']['port'],
    config['database']['host'],
    config['database']['port'],
    config['database']['user']
)
")

DB_NAME="concierge_router"

echo "=========================================="
echo "Starting Concierge Router"
echo "=========================================="
echo "Config:       $CONFIG_FILE"
echo "Host:         $ROUTER_HOST"
echo "Port:         $ROUTER_PORT"
echo "Database:     $DB_NAME @ $DB_HOST:$DB_PORT (router-specific)"
echo "=========================================="
echo ""

export PYTHONPATH=workers
export DB_HOST="$DB_HOST"
export DB_PORT="$DB_PORT"
export DB_NAME="$DB_NAME"
export DB_USER="$DB_USER"

exec python3 -m uvicorn router.main:app --host "$ROUTER_HOST" --port "$ROUTER_PORT"
