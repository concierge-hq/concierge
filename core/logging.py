"""Concierge structured logging.

Provides JSON-formatted log output with MCP request context attribution.
Enabled via CONCIERGE_LOG_FORMAT=structured or programmatically via
ConciergeLogger.configure().

Usage:
    from concierge.core.logging import ConciergeLogger

    # Auto-configured from env vars
    ConciergeLogger.configure()

    # Or explicitly
    ConciergeLogger.configure(format="structured", level="DEBUG")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from typing import Optional


class LogFormat:
    PLAIN = "plain"
    STRUCTURED = "structured"


class RequestContext:
    """Async-safe request context for log attribution.

    Uses ContextVar so each concurrent async task sees its own values.
    """

    _tool: ContextVar[str] = ContextVar("concierge_log_tool", default="")
    _method: ContextVar[str] = ContextVar("concierge_log_method", default="")

    @classmethod
    def set(cls, tool: Optional[str] = None, method: Optional[str] = None):
        if tool is not None:
            cls._tool.set(tool)
        if method is not None:
            cls._method.set(method)

    @classmethod
    def clear(cls):
        cls._tool.set("")
        cls._method.set("")

    @classmethod
    def get_tool(cls) -> str:
        return cls._tool.get("")

    @classmethod
    def get_method(cls) -> str:
        return cls._method.get("")


class _ContextFilter(logging.Filter):
    """Enriches log records with MCP session, client, tool, and pod metadata."""

    def __init__(self, server_id: str = "", pod: str = ""):
        super().__init__()
        self._server_id = server_id
        self._pod = pod

    def filter(self, record):
        record.session_id = ""
        record.client_name = ""
        record.tool_name = RequestContext.get_tool()
        record.mcp_method = RequestContext.get_method()
        record.pod = self._pod
        record.server_id = self._server_id

        try:
            from mcp.server.lowlevel.server import request_ctx

            ctx = request_ctx.get()
            if ctx and ctx.request:
                record.session_id = ctx.request.headers.get("mcp-session-id", "")
            if (
                ctx
                and ctx.session
                and ctx.session.client_params
                and ctx.session.client_params.clientInfo
            ):
                record.client_name = ctx.session.client_params.clientInfo.name
        except Exception:
            pass

        return True


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON with context fields."""

    def format(self, record):
        entry = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "session": record.session_id,
            "client": record.client_name,
            "tool": record.tool_name,
            "method": record.mcp_method,
            "pod": record.pod,
            "server_id": record.server_id,
            "msg": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1]:
            entry["msg"] += "\n" + self.formatException(record.exc_info)

        return json.dumps({k: v for k, v in entry.items() if v}, default=str)


class _LogStream:
    """Captures stdout/stderr writes and routes them through Python logging.

    Detects log level prefixes (e.g. 'INFO:', 'ERROR:', 'WARNING:') in the
    message and uses the appropriate level instead of the default.
    """

    _LEVEL_MAP = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __init__(self, logger: logging.Logger, default_level: int):
        self._logger = logger
        self._default_level = default_level

    def write(self, msg: str):
        stripped = msg.strip()
        if not stripped:
            return
        level = self._default_level
        for prefix, lvl in self._LEVEL_MAP.items():
            if stripped.startswith(prefix + ":") or stripped.startswith(prefix + " "):
                level = lvl
                break
        self._logger.log(level, stripped)

    def flush(self):
        pass

    def isatty(self):
        return False


class ConciergeLogger:
    """Configures structured logging for Concierge MCP servers.

    When format is 'structured', all log output (including from third-party
    libraries like httpx, uvicorn, and mcp) is emitted as single-line JSON
    with MCP request context (session ID, client, tool name, pod).

    When format is 'plain' (default), logging is unchanged.
    """

    _configured = False

    @classmethod
    def configure(
        cls,
        format: Optional[str] = None,
        level: Optional[str] = None,
    ):
        """Configure the logging system.

        Args:
            format: 'structured' for JSON output, 'plain' for default.
                    Defaults to CONCIERGE_LOG_FORMAT env var, then 'plain'.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
                   Defaults to CONCIERGE_LOG_LEVEL env var, then 'INFO'.
        """
        if cls._configured:
            return

        log_format = format or os.getenv("CONCIERGE_LOG_FORMAT", LogFormat.PLAIN)
        if log_format != LogFormat.STRUCTURED:
            return

        log_level = level or os.getenv("CONCIERGE_LOG_LEVEL", "INFO")
        server_id = os.getenv("CONCIERGE_PROJECT_ID", "")
        pod = os.getenv("HOSTNAME", "")

        root = logging.getLogger()
        root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        root.handlers.clear()

        handler = logging.StreamHandler(stream=sys.__stdout__)
        handler.addFilter(_ContextFilter(server_id=server_id, pod=pod))
        handler.setFormatter(_JSONFormatter())
        root.addHandler(handler)

        sys.stdout = _LogStream(logging.getLogger("stdout"), logging.INFO)
        sys.stderr = _LogStream(logging.getLogger("stderr"), logging.ERROR)

        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

        cls._configured = True


class Heartbeat:
    """Periodic heartbeat logger for liveness visibility.

    Emits a structured log line at a configurable interval so that log
    streams never appear dead during idle periods.

    Configuration:
        CONCIERGE_HEARTBEAT_INTERVAL: Seconds between heartbeats (default 60, 0 to disable).

    Usage:
        Called automatically from Concierge.streamable_http_app() / run().
        Must be called from within a running asyncio event loop.
    """

    _task: Optional[asyncio.Task] = None
    _start_time: float = 0
    _logger = logging.getLogger("concierge.heartbeat")

    @classmethod
    def start(cls):
        """Start the heartbeat background task. Safe to call multiple times."""
        if cls._task is not None:
            return

        interval = int(os.getenv("CONCIERGE_HEARTBEAT_INTERVAL", "60"))
        if interval <= 0:
            return

        cls._start_time = time.monotonic()
        cls._task = asyncio.get_running_loop().create_task(cls._run(interval))

    @classmethod
    async def _run(cls, interval: int):
        while True:
            await asyncio.sleep(interval)
            cls._logger.info("alive | uptime=%s", cls._format_uptime())

    @classmethod
    def _format_uptime(cls) -> str:
        secs = int(time.monotonic() - cls._start_time)
        if secs < 120:
            return f"{secs}s"
        if secs < 7200:
            return f"{secs // 60}m"
        hours, remainder = divmod(secs, 3600)
        return f"{hours}h{remainder // 60}m"
