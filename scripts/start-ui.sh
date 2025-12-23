#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

CONFIG_FILE="${CONFIG_FILE:-configs/default.yaml}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Parse YAML config and generate web config
python3 -c "
import yaml
import json

with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)

ui_config = config['ui']
web_config = {
    'API_BASE_URL': ui_config['api_url']
}

with open('web/src/config.ts', 'w') as f:
    f.write('// Auto-generated from configs/default.yaml\n')
    f.write(f\"export const API_BASE_URL = '{web_config['API_BASE_URL']}';\n\")

print(f\"UI Host:     {ui_config['host']}\")
print(f\"UI Port:     {ui_config['port']}\")
print(f\"API URL:     {ui_config['api_url']}\")
"

echo "=========================================="
echo "Starting Concierge Web UI"
echo "=========================================="
echo "Config:       $CONFIG_FILE"

cd web
exec npm run dev

