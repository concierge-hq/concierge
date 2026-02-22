"""
Concierge Server Adapters

Provides a unified interface for different MCP server implementations:
- FastMCP (default, full-featured)
- Raw mcp.server.Server (bare-metal)
"""

from __future__ import annotations

from concierge.adapters.base import ServerAdapter
from concierge.adapters.fastmcp_adapter import FastMCPAdapter
from concierge.adapters.raw_server_adapter import RawServerAdapter

__all__ = ["ServerAdapter", "FastMCPAdapter", "RawServerAdapter"]
