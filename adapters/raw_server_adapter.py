"""
Raw Server Adapter

Provides a FastMCP-compatible interface for raw mcp.server.Server instances.
This allows Concierge to work with bare-metal MCP servers like fathom-mcp.
"""
from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
from collections.abc import AsyncIterator
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, get_type_hints

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool as MCPTool, TextContent, Resource
from starlette.applications import Starlette
from starlette.routing import Mount


def _build_schema_from_function(fn: Callable, description: Optional[str] = None) -> dict:
    """
    Build JSON Schema from function signature.
    
    This replicates FastMCP's schema generation logic.
    """
    sig = inspect.signature(fn)
    
    # Try to get type hints
    try:
        hints = get_type_hints(fn)
    except Exception:
        hints = {}
    
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Skip 'self', 'cls', 'ctx', 'context' parameters
        if param_name in ('self', 'cls', 'ctx', 'context'):
            continue
        
        param_type = hints.get(param_name, Any)
        param_schema = _type_to_json_schema(param_type)
        
        # Add description from docstring if available
        properties[param_name] = param_schema
        
        # Required if no default value
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    
    schema = {
        "type": "object",
        "properties": properties,
    }
    
    if required:
        schema["required"] = required
    
    return schema


def _type_to_json_schema(python_type: Any) -> dict:
    """Convert Python type to JSON Schema."""
    # Handle None/NoneType
    if python_type is type(None):
        return {"type": "null"}
    
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    
    if python_type in type_map:
        return type_map[python_type]
    
    # Handle typing module types
    origin = getattr(python_type, '__origin__', None)
    args = getattr(python_type, '__args__', ())
    
    if origin is list:
        result = {"type": "array"}
        if args:
            result["items"] = _type_to_json_schema(args[0])
        return result
    
    if origin is dict:
        return {"type": "object"}
    
    # Handle Optional (Union with None)
    if origin is type(Optional[str]):  # Union
        # Filter out NoneType
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _type_to_json_schema(non_none_args[0])
    
    # Default to string for unknown types
    return {"type": "string"}


class ToolEntry:
    """Represents a registered tool with its handler and metadata."""
    
    def __init__(
        self,
        name: str,
        fn: Callable,
        description: Optional[str] = None,
        title: Optional[str] = None,
        parameters: Optional[dict] = None,
        annotations: Optional[dict] = None,
        meta: Optional[dict] = None,
    ):
        self.name = name
        self.fn = fn
        self.title = title or name.replace("_", " ").title()
        self.description = description or fn.__doc__ or ""
        self.parameters = parameters or _build_schema_from_function(fn, description)
        self.annotations = annotations or {}
        self.meta = meta or {}
        self.output_schema = None
        self.icons = None
    
    def to_mcp_tool(self) -> MCPTool:
        """Convert to MCP Tool type."""
        return MCPTool(
            name=self.name,
            description=self.description,
            inputSchema=self.parameters,
            _meta=self.meta if self.meta else None,
        )
    
    async def run(self, arguments: dict) -> Any:
        """Execute the tool handler."""
        result = self.fn(**arguments)
        if asyncio.iscoroutine(result):
            result = await result
        return result


class ToolManagerShim:
    """
    Shim that provides FastMCP-like tool manager interface.
    
    This allows Concierge to use the same code paths for both
    FastMCP and raw Server instances.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
    
    def list_tools(self) -> List[ToolEntry]:
        """Return all registered tools."""
        return list(self._tools.values())
    
    def add_tool(self, entry: ToolEntry) -> None:
        """Add a tool to the registry."""
        self._tools[entry.name] = entry
    
    def get_tool(self, name: str) -> Optional[ToolEntry]:
        """Get a tool by name."""
        return self._tools.get(name)


class MCPServerShim:
    """
    Shim that provides access to raw Server's handlers.
    
    Adapts raw Server's decorator-based API to look like FastMCP's internal API.
    """
    
    def __init__(self, server: Server, tool_manager: ToolManagerShim):
        self._server = server
        self._tool_manager = tool_manager
        self._list_tools_override: Optional[Callable] = None
        self._list_resources_override: Optional[Callable] = None
        self._resources: List[Resource] = []
        
        # Setup the core handlers
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Register core handlers with the raw Server."""
        tool_manager = self._tool_manager
        shim = self
        
        @self._server.list_tools()
        async def _list_tools_handler() -> List[MCPTool]:
            # If there's an override, use it
            if shim._list_tools_override:
                return await shim._list_tools_override()
            # Otherwise, return our managed tools
            return [entry.to_mcp_tool() for entry in tool_manager.list_tools()]
        
        @self._server.call_tool()
        async def _call_tool_handler(name: str, arguments: dict) -> List[TextContent]:
            entry = tool_manager.get_tool(name)
            if not entry:
                raise ValueError(f"Unknown tool: {name}")
            
            result = await entry.run(arguments)
            
            # Handle different return types
            if isinstance(result, list) and result and isinstance(result[0], TextContent):
                return result
            if isinstance(result, TextContent):
                return [result]
            if isinstance(result, dict):
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            if isinstance(result, str):
                return [TextContent(type="text", text=result)]
            
            # Default: convert to string
            return [TextContent(type="text", text=str(result))]
        
        @self._server.list_resources()
        async def _list_resources_handler() -> List[Resource]:
            if shim._list_resources_override:
                return await shim._list_resources_override()
            return shim._resources
    
    @property
    def request_handlers(self) -> Dict[Any, Callable]:
        """Access raw Server's request handlers."""
        return self._server.request_handlers
    
    def list_tools(self) -> Callable:
        """
        Return a decorator that registers a list_tools override.
        
        This mimics FastMCP's _mcp_server.list_tools() behavior.
        """
        def decorator(fn: Callable) -> Callable:
            self._list_tools_override = fn
            return fn
        return decorator
    
    def list_resources(self) -> Callable:
        """
        Return a decorator that registers a list_resources override.
        
        This mimics FastMCP's _mcp_server.list_resources() behavior.
        """
        def decorator(fn: Callable) -> Callable:
            self._list_resources_override = fn
            return fn
        return decorator


class RawServerAdapter:
    """
    Adapter for raw mcp.server.Server instances.
    
    Provides a FastMCP-compatible interface so Concierge can work
    with bare-metal MCP servers without modification.
    """
    
    def __init__(self, server: Server):
        self._raw_server = server
        self._tool_manager = ToolManagerShim()
        self._mcp_server = MCPServerShim(server, self._tool_manager)
    
    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        title: Optional[str] = None,
        annotations: Optional[dict] = None,
        meta: Optional[dict] = None,
        **kwargs,
    ) -> Callable:
        """
        Decorator to register a tool.
        
        Mimics FastMCP's @server.tool() decorator.
        """
        def decorator(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            tool_desc = description or fn.__doc__ or ""
            
            entry = ToolEntry(
                name=tool_name,
                fn=fn,
                description=tool_desc,
                title=title,
                annotations=annotations,
                meta=meta,
            )
            
            self._tool_manager.add_tool(entry)
            
            @wraps(fn)
            async def wrapped(*args, **kw):
                result = fn(*args, **kw)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            
            return wrapped
        
        return decorator
    
    async def list_tools(self) -> List[MCPTool]:
        """
        List all registered tools (direct access).
        
        NOTE: This does NOT use the handler override. The override is only for
        MCP protocol responses. This method is for internal queries (e.g., by
        Concierge's _setup_staged_tools which captures 'original_list_tools').
        """
        return [entry.to_mcp_tool() for entry in self._tool_manager.list_tools()]
    
    async def list_resources(self) -> List[Resource]:
        """
        List all registered resources (direct access).
        
        NOTE: This does NOT use the handler override for the same reason as list_tools.
        """
        return self._mcp_server._resources
    
    def run(self, *args, **kwargs) -> Any:
        """Run the raw server."""
        return self._raw_server.run(*args, **kwargs)
    
    def streamable_http_app(self) -> Starlette:
        """
        Build a Starlette app for HTTP transport.
        
        Uses StreamableHTTPSessionManager like fathom-mcp does.
        """
        session_manager = StreamableHTTPSessionManager(app=self._raw_server)
        
        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            async with session_manager.run():
                yield
        
        routes = [
            Mount("/mcp", app=session_manager.handle_request),
        ]
        
        return Starlette(routes=routes, lifespan=lifespan)
    
    def __getattr__(self, name: str) -> Any:
        """Forward any other attribute access to the raw server."""
        return getattr(self._raw_server, name)
