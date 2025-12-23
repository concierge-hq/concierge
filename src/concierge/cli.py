"""
Compatibility CLI entry point that forwards to the worker CLI implementation.

The `concierge` console script that setuptools installs still points at
`concierge.cli:cli`. After the recent refactor the actual click commands live
in `services.worker.cli`. Importing and re-exporting the `cli` group here keeps
the existing entry point working without duplicating the implementation.
"""

from services.worker.cli import cli as worker_cli

cli = worker_cli

__all__ = ["cli"]

