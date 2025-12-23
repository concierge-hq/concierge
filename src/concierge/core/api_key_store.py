from __future__ import annotations

from datetime import datetime
import hashlib
import secrets
from typing import Any, Dict, List, Optional

from concierge.core.postgres_state_manager import PostgreSQLStateManager


class ApiKeyStore:
    """Persistent storage and generation of API keys."""

    def __init__(self, state_manager: PostgreSQLStateManager):
        self._state_manager = state_manager

    def _get_pool(self):
        pool = getattr(self._state_manager, "_pool", None)
        if pool is None:
            raise RuntimeError("PostgreSQLStateManager pool is not initialized")
        return pool

    async def create_api_key(self, user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Generate and persist a new API key for the given user."""
        if not user_id:
            raise ValueError("user_id is required")

        raw_key = f"ck_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        pool = self._get_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO concierge_api_keys (user_id, api_key_hash, name)
            VALUES ($1, $2, $3)
            RETURNING id, created_at
            """,
            user_id,
            key_hash,
            name,
        )

        created_at = row["created_at"] if row and row.get("created_at") else None
        created_iso = created_at.isoformat() if isinstance(created_at, datetime) else None

        return {
            "api_key": raw_key,
            "id": row["id"] if row else None,
            "created_at": created_iso,
            "name": name,
        }

    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Return metadata for API keys belonging to the user (without revealing secrets)."""
        pool = self._get_pool()
        rows = await pool.fetch(
            """
            SELECT id, name, created_at
            FROM concierge_api_keys
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )

        results: List[Dict[str, Any]] = []
        for row in rows:
            created_at = row.get("created_at")
            created_iso = created_at.isoformat() if isinstance(created_at, datetime) else None
            results.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "created_at": created_iso,
                }
            )
        return results
