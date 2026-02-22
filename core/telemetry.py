"""
Concierge Metrics - Optional telemetry for deployed MCP servers
Enabled via CONCIERGE_PROJECT_ID and CONCIERGE_AUTH_TOKEN env vars
"""

from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from collections import deque
from typing import Optional

import httpx

PROJECT_ID = os.getenv("CONCIERGE_PROJECT_ID")
AUTH_TOKEN = os.getenv("CONCIERGE_AUTH_TOKEN")
API_URL = os.getenv("CONCIERGE_API_URL", "https://getconcierge.app")
ENABLED = bool(PROJECT_ID and AUTH_TOKEN)


@dataclass
class MCPEvent:
    project_id: str
    session_id: str
    event_type: str
    resource_name: Optional[str] = None
    duration_ms: Optional[int] = None
    is_error: bool = False
    error_message: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ConciergeMetrics:
    def __init__(self):
        self.queue: "deque[MCPEvent]" = deque(maxlen=1000)
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def track(self, event_type: str, **kwargs) -> None:
        if not ENABLED:
            return
        self.queue.append(
            MCPEvent(
                project_id=PROJECT_ID,
                session_id=kwargs.pop("session_id", "unknown"),
                event_type=event_type,
                **kwargs,
            )
        )

    async def flush(self) -> None:
        if not ENABLED or not self.queue:
            return
        events = [asdict(self.queue.popleft()) for _ in range(len(self.queue))]
        if not events:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{API_URL}/analytics/events",
                    json={"events": events},
                    headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                )
        except Exception:
            pass  # Best effort, drop on failure

    async def _loop(self) -> None:
        while self._running:
            await asyncio.sleep(5.0)
            try:
                await self.flush()
            except Exception:
                pass

    def start(self) -> None:
        if not ENABLED or self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._loop())
        except RuntimeError:
            pass

    def ensure_started(self) -> None:
        """Called from request handlers to ensure background task is running."""
        if not ENABLED or self._task is not None:
            return
        try:
            loop = asyncio.get_running_loop()
            self._running = True
            self._task = loop.create_task(self._loop())
        except RuntimeError:
            pass

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        await self.flush()


metrics = ConciergeMetrics()
