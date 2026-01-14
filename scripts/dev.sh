#!/bin/bash
# Run development server with hot reload
cd "$(dirname "$0")/.."
PYTHONPATH=src python -m uvicorn uaip.serving.server:app --reload --port 8000

