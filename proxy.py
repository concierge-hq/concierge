"""Upstream MCP server proxy with per-session connection management.

Uses MCP ClientSession for upstream communication, spawned in dedicated
asyncio tasks to avoid anyio cancel scope conflicts with the MCP server's
internal task management.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import (
    Tool as MCPTool,
    CallToolResult,
    Resource,
    ResourceTemplate,
    Prompt,
    GetPromptResult,
    ReadResourceResult,
    ServerNotification,
    ToolListChangedNotification,
    ResourceListChangedNotification,
    PromptListChangedNotification,
    ResourceUpdatedNotification,
)

logger = logging.getLogger("concierge.proxy")


class UpstreamConnection:
    """A single MCP client connection to one upstream server.

    The ClientSession is spawned in its own asyncio.Task (outside anyio's
    structured concurrency) so its internal task groups never nest inside
    the MCP server's request-handler cancel scopes.
    """

    def __init__(self, url: str, notification_callback=None):
        self.url = url
        self._session: Optional[ClientSession] = None
        self._task: Optional[asyncio.Task] = None
        self._ready = asyncio.Event()
        self._initialized = False
        self._notification_callback = notification_callback

    async def _run(self) -> None:
        """Background task that maintains the MCP client session."""
        try:
            async with streamable_http_client(self.url) as (
                read,
                write,
                _get_session_id,
            ):
                async with ClientSession(
                    read,
                    write,
                    message_handler=self._handle_upstream_message,
                ) as session:
                    await session.initialize()
                    self._session = session
                    self._initialized = True
                    self._ready.set()
                    # Block forever — keeps the session alive until cancelled
                    await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Upstream connection to {self.url} failed: {e}")
            self._ready.set()  # Unblock waiters even on failure
        finally:
            self._session = None
            self._initialized = False

    async def _handle_upstream_message(self, message) -> None:
        """Handle messages from upstream, forwarding notifications to client."""
        if isinstance(message, Exception):
            logger.warning(f"Upstream {self.url} stream error: {message}")
            return
        if isinstance(message, ServerNotification) and self._notification_callback:
            root = message.root
            if isinstance(
                root,
                (
                    ToolListChangedNotification,
                    ResourceListChangedNotification,
                    PromptListChangedNotification,
                    ResourceUpdatedNotification,
                ),
            ):
                try:
                    await self._notification_callback(message, self.url)
                except Exception as e:
                    logger.error(f"Failed to forward notification from {self.url}: {e}")

    @property
    def connected(self) -> bool:
        return self._initialized and self._session is not None

    async def connect(self) -> None:
        self._ready = asyncio.Event()
        self._task = asyncio.create_task(self._run())
        await self._ready.wait()

    async def disconnect(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._session = None
        self._initialized = False

    # ── forwarding methods ──────────────────────────────────────────

    async def list_tools(self) -> List[MCPTool]:
        result = await self._session.list_tools()
        return list(result.tools)

    async def call_tool(self, name: str, arguments: dict) -> CallToolResult:
        if not self._session:
            raise ValueError(f"Not connected to {self.url}")
        return await self._session.call_tool(name, arguments)

    async def list_resources(self) -> List[Resource]:
        result = await self._session.list_resources()
        return list(result.resources)

    async def read_resource(self, uri: str) -> ReadResourceResult:
        from pydantic import AnyUrl

        return await self._session.read_resource(AnyUrl(uri))

    async def list_resource_templates(self) -> List[ResourceTemplate]:
        result = await self._session.list_resource_templates()
        return list(result.resourceTemplates)

    async def list_prompts(self) -> List[Prompt]:
        result = await self._session.list_prompts()
        return list(result.prompts)

    async def get_prompt(
        self, name: str, arguments: Optional[dict] = None
    ) -> GetPromptResult:
        return await self._session.get_prompt(name, arguments=arguments)


class SessionState:
    """Per-session upstream connections and routing maps."""

    def __init__(self):
        self.conns: Dict[str, UpstreamConnection] = {}
        self.tool_to_conn: Dict[str, UpstreamConnection] = {}
        self.tool_to_upstream_name: Dict[str, str] = {}
        self.resource_to_conn: Dict[str, UpstreamConnection] = {}
        self.prompt_to_conn: Dict[str, UpstreamConnection] = {}
        self.prompt_to_upstream_name: Dict[str, str] = {}
        self._server_session = None  # ServerSession for forwarding notifications

    async def _forward_notification(
        self, notification: ServerNotification, source_url: str
    ) -> None:
        """Forward an upstream notification to the connected client."""
        if not self._server_session:
            logger.debug(f"No server session to forward notification from {source_url}")
            return
        try:
            await self._server_session.send_notification(notification)
            logger.debug(
                f"Forwarded {notification.root.__class__.__name__} from {source_url}"
            )
        except Exception as e:
            # Write stream closed = client disconnected; stop retrying
            self._server_session = None
            logger.debug(
                f"Client disconnected, clearing server session (was forwarding from {source_url}): {e}"
            )


class SessionPool:
    """Per-client-session pool of upstream connections and routing state."""

    def __init__(self, upstream_urls: List[str]):
        self.upstream_urls = upstream_urls
        self._sessions: Dict[str, SessionState] = {}

    def _get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState()
        return self._sessions[session_id]

    async def get_session_state(self, session_id: str) -> SessionState:
        state = self._get_or_create(session_id)
        # Only connect URLs that have never been connected for this session.
        # If a connection drops, we do NOT silently reconnect — a new connection
        # would create a new upstream session, losing all prior state. Let the
        # tool call fail explicitly so the caller knows the connection is gone.
        needs = [u for u in self.upstream_urls if u not in state.conns]
        if not needs:
            return state

        async def _try_connect(url: str):
            import time as _time

            start = _time.time()
            conn = UpstreamConnection(
                url, notification_callback=state._forward_notification
            )
            try:
                await asyncio.wait_for(conn.connect(), timeout=600)
                elapsed = _time.time() - start
                if conn.connected:
                    state.conns[url] = conn
                    logger.info(f"Connected {url} in {elapsed:.1f}s")
                else:
                    logger.warning(f"Failed {url} after {elapsed:.1f}s (not connected)")
                    await conn.disconnect()
            except BaseException as e:
                elapsed = _time.time() - start
                logger.warning(
                    f"Failed {url} after {elapsed:.1f}s: {type(e).__name__}: {e}"
                )
                try:
                    await conn.disconnect()
                except BaseException:
                    pass

        batch_size = 15
        for i in range(0, len(needs), batch_size):
            batch = needs[i : i + batch_size]
            logger.info(
                f"Connecting batch {i // batch_size + 1}: {len(batch)} upstreams..."
            )
            tasks = [asyncio.ensure_future(_try_connect(u)) for u in batch]
            await asyncio.shield(asyncio.gather(*tasks, return_exceptions=True))
        logger.info(f"All batches done. Connected: {len(state.conns)}/{len(needs)}")
        return state

    async def cleanup_session(self, session_id: str) -> None:
        state = self._sessions.pop(session_id, None)
        if state:
            for conn in state.conns.values():
                await conn.disconnect()

    async def cleanup_all(self) -> None:
        for session_id in list(self._sessions.keys()):
            await self.cleanup_session(session_id)


def _extract_result_text(result: CallToolResult) -> str:
    parts = []
    for content in result.content or []:
        if hasattr(content, "text"):
            parts.append(content.text)
    return "\n".join(parts)


def install_proxy_handlers(concierge_instance) -> None:
    """Install protocol-level handlers that forward to upstream servers."""
    upstream_urls = concierge_instance._upstream_servers
    if not upstream_urls:
        return

    pool = SessionPool(upstream_urls)
    concierge_instance._proxy_pool = pool

    server = concierge_instance._server
    handlers = server._mcp_server.request_handlers
    from mcp.server.lowlevel.server import request_ctx
    import mcp.types as types

    def _get_session_id() -> str:
        ctx = request_ctx.get()
        if ctx.request and hasattr(ctx.request, "headers"):
            return ctx.request.headers.get("mcp-session-id", "default")
        return "default"

    async def _get_state() -> SessionState:
        ctx = request_ctx.get()
        state = await pool.get_session_state(_get_session_id())
        state._server_session = ctx.session
        return state

    original_list_tools = handlers.get(types.ListToolsRequest)
    tool_patches = concierge_instance._tool_patches

    def _apply_patches(tool: MCPTool) -> None:
        for patch in tool_patches:
            if patch["tool_name"] != tool.name:
                continue
            pt = patch["patch_type"]
            val = patch["value"]
            if pt == "tool_description":
                tool.description = val
            elif pt == "param_description":
                param = patch["param_name"]
                props = tool.inputSchema.get("properties", {})
                if param in props:
                    props[param]["description"] = val
            elif pt == "param_required":
                param = patch["param_name"]
                req = tool.inputSchema.setdefault("required", [])
                if param not in req:
                    req.append(param)
            elif pt == "param_enum":
                param = patch["param_name"]
                props = tool.inputSchema.get("properties", {})
                if param in props:
                    props[param]["enum"] = val

    async def _handle_list_tools(req: types.ListToolsRequest) -> types.ServerResult:
        local_tools = []
        if original_list_tools:
            local_result = await original_list_tools(req)
            local_tools = local_result.root.tools

        state = await _get_state()
        upstream_tools: List[MCPTool] = []

        for url, conn in state.conns.items():
            try:
                tools = await conn.list_tools()
                for tool in tools:
                    if tool_patches:
                        _apply_patches(tool)
                    upstream_tools.append(tool)
                    state.tool_to_conn[tool.name] = conn
                    state.tool_to_upstream_name[tool.name] = tool.name
            except Exception as e:
                logger.error(f"Failed to list tools from {url}: {e}")

        return types.ServerResult(
            types.ListToolsResult(tools=local_tools + upstream_tools)
        )

    handlers[types.ListToolsRequest] = _handle_list_tools

    original_call_tool = handlers.get(types.CallToolRequest)

    moderator = concierge_instance._moderator

    async def _moderate(content, tool_name: str) -> Optional[types.ServerResult]:
        if not moderator:
            return None
        text = moderator.serialize(content) if not isinstance(content, str) else content
        allowed, reason = await moderator.check(text)
        if allowed:
            return None
        return types.ServerResult(
            CallToolResult(
                content=[
                    types.TextContent(
                        type="text", text=f"[BLOCKED] '{tool_name}': {reason}"
                    )
                ],
                isError=True,
            )
        )

    async def _handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        name = req.params.name
        arguments = req.params.arguments or {}

        state = await _get_state()
        conn = state.tool_to_conn.get(name)
        if conn:
            blocked = await _moderate(arguments, name)
            if blocked:
                return blocked

            upstream_name = state.tool_to_upstream_name.get(name, name)
            result = await conn.call_tool(upstream_name, arguments)

            blocked = await _moderate(_extract_result_text(result), name)
            return blocked if blocked else types.ServerResult(result)

        if original_call_tool:
            return await original_call_tool(req)

        raise ValueError(f"Unknown tool: {name}")

    handlers[types.CallToolRequest] = _handle_call_tool

    original_list_resources = handlers.get(types.ListResourcesRequest)

    async def _handle_list_resources(
        req: types.ListResourcesRequest,
    ) -> types.ServerResult:
        local_resources = []
        if original_list_resources:
            local_result = await original_list_resources(req)
            local_resources = local_result.root.resources

        state = await _get_state()
        upstream_resources: List[Resource] = []

        for url, conn in state.conns.items():
            try:
                resources = await conn.list_resources()
                for r in resources:
                    upstream_resources.append(r)
                    state.resource_to_conn[str(r.uri)] = conn
            except Exception as e:
                logger.error(f"Failed to list resources from {url}: {e}")

        return types.ServerResult(
            types.ListResourcesResult(resources=local_resources + upstream_resources)
        )

    handlers[types.ListResourcesRequest] = _handle_list_resources

    original_read_resource = handlers.get(types.ReadResourceRequest)

    async def _handle_read_resource(
        req: types.ReadResourceRequest,
    ) -> types.ServerResult:
        uri_str = str(req.params.uri)

        state = await _get_state()
        conn = state.resource_to_conn.get(uri_str)
        if conn:
            result = await conn.read_resource(uri_str)
            return types.ServerResult(result)

        if original_read_resource:
            return await original_read_resource(req)

        raise ValueError(f"Unknown resource: {uri_str}")

    handlers[types.ReadResourceRequest] = _handle_read_resource

    original_list_prompts = handlers.get(types.ListPromptsRequest)

    async def _handle_list_prompts(req: types.ListPromptsRequest) -> types.ServerResult:
        local_prompts = []
        if original_list_prompts:
            local_result = await original_list_prompts(req)
            local_prompts = local_result.root.prompts

        state = await _get_state()
        upstream_prompts = []

        for url, conn in state.conns.items():
            try:
                prompts = await conn.list_prompts()
                for p in prompts:
                    upstream_prompts.append(p)
                    state.prompt_to_conn[p.name] = conn
                    state.prompt_to_upstream_name[p.name] = p.name
            except Exception as e:
                logger.error(f"Failed to list prompts from {url}: {e}")

        return types.ServerResult(
            types.ListPromptsResult(prompts=local_prompts + upstream_prompts)
        )

    handlers[types.ListPromptsRequest] = _handle_list_prompts

    original_get_prompt = handlers.get(types.GetPromptRequest)

    async def _handle_get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
        name = req.params.name
        arguments = req.params.arguments

        state = await _get_state()
        conn = state.prompt_to_conn.get(name)
        if conn:
            upstream_name = state.prompt_to_upstream_name.get(name, name)
            result = await conn.get_prompt(upstream_name, arguments=arguments)
            return types.ServerResult(result)

        if original_get_prompt:
            return await original_get_prompt(req)

        raise ValueError(f"Unknown prompt: {name}")

    handlers[types.GetPromptRequest] = _handle_get_prompt

    logger.info(f"Proxy handlers installed for {len(upstream_urls)} upstream server(s)")
