"""
FastMCP Adapter

Thin wrapper around FastMCP that implements the ServerAdapter protocol.
This is essentially a pass-through - FastMCP already has all the features we need.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool, Resource
    from starlette.applications import Starlette


class FastMCPAdapter:
    """
    Adapter for FastMCP servers.
    
    FastMCP already provides all the interfaces Concierge needs,
    so this adapter is mostly a pass-through.
    """
    
    def __init__(self, server: "FastMCP"):
        self._server = server
    
    @property
    def _tool_manager(self):
        """Delegate to FastMCP's tool manager."""
        return self._server._tool_manager
    
    @property
    def _mcp_server(self):
        """Delegate to FastMCP's internal MCP server."""
        return self._server._mcp_server
    
    def tool(self, **kwargs) -> Callable:
        """Delegate to FastMCP's tool decorator."""
        return self._server.tool(**kwargs)
    
    async def list_tools(self) -> List["Tool"]:
        """Delegate to FastMCP's list_tools."""
        return await self._server.list_tools()
    
    async def list_resources(self) -> List["Resource"]:
        """Delegate to FastMCP's list_resources."""
        return await self._server.list_resources()
    
    def run(self, *args, **kwargs) -> Any:
        """Delegate to FastMCP's run method."""
        return self._server.run(*args, **kwargs)
    
    def streamable_http_app(self) -> "Starlette":
        """Delegate to FastMCP's streamable_http_app."""
        return self._server.streamable_http_app()
    
    def __getattr__(self, name: str) -> Any:
        """Forward any other attribute access to the underlying FastMCP server."""
        return getattr(self._server, name)
