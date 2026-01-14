#!/bin/bash
# Build package for PyPI
cd "$(dirname "$0")/.."
rm -rf dist build *.egg-info
python -m build

