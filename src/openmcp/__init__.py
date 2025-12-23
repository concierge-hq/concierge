from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, List

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from openmcp.backends.search_backend import SearchBackend
from openmcp.backends.vanilla_backend import VanillaBackend
from openmcp.core.widget import Widget


class ProviderType(Enum):
    PLAIN = "plain"
    SEARCH = "search"


PROVIDER_REGISTRY = {
    ProviderType.PLAIN: VanillaBackend,
    ProviderType.SEARCH: SearchBackend,
}


class Config:
    def __init__(self, max_results=5, provider_type=ProviderType.PLAIN, model=None):
        self.max_results = max_results
        self.provider_type = provider_type
        self.model = model


class OpenMCP:

    def __init__(self, server, *, config=Config(), **fastmcp_kwargs):
        if isinstance(server, FastMCP):
            self._server = server
        else:
            self._server = FastMCP(server, **fastmcp_kwargs)
        self._config = config
        self._widgets: List[Widget] = []
        self._pending_resources: List[types.Resource] = []

        provider_cls = PROVIDER_REGISTRY[config.provider_type]
        self._provider = provider_cls()
        self._provider.initialize(config)

    def _get_widget_meta(self, w: Widget) -> dict:
        return {
            "openai/outputTemplate": w.uri,
            "openai/widgetAccessible": w.widget_accessible,
            "openai/toolInvocation/invoking": w.invoking,
            "openai/toolInvocation/invoked": w.invoked,
        }

    def _setup_resource_handler(self) -> None:
        original_list_resources = self._server.list_resources
        widget_resources = self._pending_resources

        async def _list_all_resources() -> List[types.Resource]:
            fastmcp_resources = await original_list_resources()
            return fastmcp_resources + widget_resources

        self._server._mcp_server.list_resources()(_list_all_resources)

    def _setup_read_resource_handler(self) -> None:
        widgets_by_uri = {w.uri: w for w in self._widgets}

        original_handler = self._server._mcp_server.request_handlers.get(
            types.ReadResourceRequest
        )

        async def _read_resource_with_meta(
            req: types.ReadResourceRequest,
        ) -> types.ServerResult:
            uri_str = str(req.params.uri)
            widget = widgets_by_uri.get(uri_str)

            if widget:
                if widget.html:
                    text = widget.html
                elif widget.html_file:
                    text = Path(widget.html_file).read_text()
                else:
                    raise ValueError(f"Widget {widget.name}: no html content")

                contents = [
                    types.TextResourceContents(
                        uri=widget.uri,
                        mimeType=widget.mime_type,
                        text=text,
                        _meta=self._get_widget_meta(widget),
                    )
                ]
                return types.ServerResult(types.ReadResourceResult(contents=contents))

            if original_handler:
                return await original_handler(req)

            raise ValueError(f"Unknown resource: {uri_str}")

        self._server._mcp_server.request_handlers[
            types.ReadResourceRequest
        ] = _read_resource_with_meta

    def _finalize(self):
        """Setup all handlers. Called before run() or streamable_http_app()."""
        if getattr(self, "_finalized", False):
            return
        self._finalized = True

        tools = self._server._tool_manager.list_tools()
        self._provider.index_tools(tools)

        replacement_tools = self._provider.serve_tools()
        if replacement_tools is not None:
            self._server._tool_manager._tools.clear()
            for tool_fn in replacement_tools:
                self._server.tool()(tool_fn)

        self._setup_resource_handler()
        self._setup_read_resource_handler()

    def run(self, *args, **kwargs):
        self._finalize()
        return self._server.run(*args, **kwargs)

    def streamable_http_app(self, *args, **kwargs):
        self._finalize()
        return self._server.streamable_http_app(*args, **kwargs)

    def widget(
        self,
        uri: str,
        html: str | None = None,
        html_file: str | None = None,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        invoking: str = "Loading...",
        invoked: str = "Done",
        annotations: dict | None = None,
    ) -> Callable:

        def decorator(fn: Callable) -> Callable:
            w = Widget(
                html=html,
                html_file=html_file,
                name=name or fn.__name__,
                title=title,
                description=description or fn.__doc__,
                uri=uri,
                invoking=invoking,
                invoked=invoked,
                annotations=annotations,
            )
            self._widgets.append(w)
            self._pending_resources.append(
                types.Resource(
                    uri=w.uri,
                    name=w.name,
                    title=w.title,
                    description=w.description,
                    mimeType=w.mime_type,
                    _meta=self._get_widget_meta(w),
                )
            )

            @wraps(fn)
            async def wrapped(*args, **kwargs) -> types.CallToolResult:
                result = await fn(*args, **kwargs)
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=w.invoked)],
                    structuredContent=result,
                    _meta={
                        "openai/toolInvocation/invoking": w.invoking,
                        "openai/toolInvocation/invoked": w.invoked,
                    },
                )

            self._server.tool(
                name=w.name,
                title=w.title,
                description=w.description,
                annotations=w.annotations,
                meta={
                    "openai/outputTemplate": w.uri,
                    "openai/widgetAccessible": w.widget_accessible,
                    "openai/toolInvocation/invoking": w.invoking,
                    "openai/toolInvocation/invoked": w.invoked,
                },
            )(wrapped)

            return fn

        return decorator

    def __getattr__(self, name):
        return getattr(self._server, name)
