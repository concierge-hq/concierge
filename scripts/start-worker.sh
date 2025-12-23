# Concierge V0.2
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONFIG_FILE="${CONFIG_FILE:-configs/default.yaml}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Parse YAML config using Python
read -r WORKER_HOST WORKER_PORT DB_HOST DB_PORT DB_NAME DB_USER STATE_MGR <<< $(python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(
    config['worker']['host'],
    config['worker']['port'],
    config['database']['host'],
    config['database']['port'],
    config['database']['name'],
    config['database']['user'],
    config['worker']['state_manager']
)
")

echo "=========================================="
echo "Starting Concierge Worker"
echo "=========================================="
echo "Config:       $CONFIG_FILE"
echo "Host:         $WORKER_HOST"
echo "Port:         $WORKER_PORT"
echo "State:        $STATE_MGR"
echo "Database:     $DB_NAME @ $DB_HOST:$DB_PORT"
echo "=========================================="
echo ""

export PYTHONPATH=workers
export DB_HOST="$DB_HOST"
export DB_PORT="$DB_PORT"
export DB_NAME="$DB_NAME"
export DB_USER="$DB_USER"

exec python3 -u bin/server.py
