"""Content moderation for MCP tool inputs and outputs.

Intercepts tool calls (both arguments and results) and runs configurable
checks to block prompt injection, context poisoning, and data exfiltration
from upstream servers.

Provides basic deterministic checks (size limits, regex pattern matching)
with hooks for remote validation and pluggable scanners.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger("concierge.security")

DEFAULT_BLOCK_PATTERNS = [
    r"IGNORE\s+(ALL\s+)?PREVIOUS\s+INSTRUCTIONS",
    r"\[INST\]",
    r"\[/INST\]",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"BEGIN\s+SYSTEM\s+PROMPT",
    r"END\s+SYSTEM\s+PROMPT",
]


@dataclass
class ModerationConfig:
    enabled: bool = True
    max_size: int = 50_000
    block_patterns: List[str] = field(
        default_factory=lambda: list(DEFAULT_BLOCK_PATTERNS)
    )

    # Plumbing for future remote moderation endpoint
    remote_endpoint: Optional[str] = None
    remote_api_key: Optional[str] = None
    remote_timeout: float = 5.0

    # TODO: pluggable scanner interface (e.g. LLM Guard, Vigil)


class ContentModerator:
    """Checks text content for malicious patterns.

    Called by the proxy to filter both tool inputs and outputs.
    Returns (allowed, reason). The proxy decides what to do with it.
    """

    def __init__(self, config: ModerationConfig):
        self._config = config
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in config.block_patterns
        ]

    async def check(self, text: str) -> tuple[bool, Optional[str]]:
        """Check text content. Returns (allowed, reason)."""
        if len(text) > self._config.max_size:
            return (
                False,
                f"Content size ({len(text)}) exceeds limit ({self._config.max_size})",
            )

        for pattern in self._compiled_patterns:
            match = pattern.search(text)
            if match:
                return False, f"Blocked pattern detected: '{match.group()}'"

        # TODO: add more comprehensive moderation policies
        # - PII detection / redaction
        # - detect encoded payloads (base64 blobs, data URIs)
        # - detect suspicious URLs / external endpoints
        # - detect leaked credentials or API key patterns
        # - pluggable scanner integration (LLM Guard, Vigil, etc.)
        # - remote endpoint validation

        return True, None

    def serialize(self, obj: Any) -> str:
        """Convert arguments dict to string for scanning."""
        try:
            return json.dumps(obj, default=str)
        except (TypeError, ValueError):
            return str(obj)
