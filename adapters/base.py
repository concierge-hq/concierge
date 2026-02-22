"""
Base Server Adapter Protocol

Defines the interface that Concierge needs from any MCP server implementation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.types import Tool, Resource
    from starlette.applications import Starlette


class ToolManagerProtocol(Protocol):
    """Protocol for tool manager interface."""

    def list_tools(self) -> List["Tool"]:
        """Return all registered tools."""
        ...

    @property
    def _tools(self) -> Dict[str, Any]:
        """Get tools dict."""
        ...

    @_tools.setter
    def _tools(self, value: Dict[str, Any]) -> None:
        """Set tools dict."""
        ...


class MCPServerProtocol(Protocol):
    """Protocol for low-level MCP server interface."""

    def list_tools(self) -> Callable:
        """Decorator to override list_tools handler."""
        ...

    def list_resources(self) -> Callable:
        """Decorator to override list_resources handler."""
        ...

    @property
    def request_handlers(self) -> Dict[Any, Callable]:
        """Get request handlers dict."""
        ...


class ServerAdapter(Protocol):
    """
    Protocol defining what Concierge needs from any MCP server.

    This abstraction allows Concierge to work with both:
    - FastMCP (high-level, decorator-based)
    - mcp.server.Server (low-level, manual registration)
    """

    @property
    def _tool_manager(self) -> ToolManagerProtocol:
        """Access to tool manager for listing/modifying tools."""
        ...

    @property
    def _mcp_server(self) -> MCPServerProtocol:
        """Access to low-level MCP server for handler overrides."""
        ...

    def tool(self, **kwargs) -> Callable:
        """Decorator to register a tool."""
        ...

    async def list_tools(self) -> List["Tool"]:
        """List all registered tools."""
        ...

    async def list_resources(self) -> List["Resource"]:
        """List all registered resources."""
        ...

    def run(self, *args, **kwargs) -> Any:
        """Run the server."""
        ...

    def streamable_http_app(self) -> "Starlette":
        """Get Starlette app for HTTP transport."""
        ...
