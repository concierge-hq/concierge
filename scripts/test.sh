#!/bin/bash
# Run tests
cd "$(dirname "$0")/.."
PYTHONPATH=src pytest tests/ -v

