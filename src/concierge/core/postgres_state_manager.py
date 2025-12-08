"""
PostgreSQL-backed StateManager implementation.
"""

import json
from typing import Any, Dict, List, Optional

import asyncpg

from concierge.core.state_manager import StateManager


class PostgreSQLStateManager(StateManager):
    """PostgreSQL-backed state manager for production use."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "concierge",
        user: str = "postgres",
        password: str = "",
        pool_min_size: int = 10,
        pool_max_size: int = 20,
    ):
        """
        Initialize PostgreSQL state manager.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            pool_min_size: Minimum connection pool size
            pool_max_size: Maximum connection pool size

        Raises:
            ImportError: If asyncpg is not installed
        """
        if asyncpg is None:
            raise ImportError("PostgreSQLStateManager requires asyncpg. Install it with: pip install asyncpg")

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self._pool: Optional[asyncpg.Pool] = None

    @staticmethod
    def _load_json(data: str | None) -> Dict[str, Any]:
        """Parse JSON string from Postgres into mutable dict."""
        return json.loads(data) if data else {}

    @staticmethod
    def _dump_json(data: Dict[str, Any]) -> str:
        """Serialize dict to JSON string for Postgres jsonb columns."""
        return json.dumps(data or {})

    async def initialize(self):
        """Initialize database connection pool. Call this before using the manager."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=self.pool_min_size,
                max_size=self.pool_max_size,
            )

    async def close(self):
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _ensure_pool(self):
        """Ensure pool is initialized."""
        if self._pool is None:
            raise RuntimeError(
                "PostgreSQLStateManager not initialized. Call await state_manager.initialize() before use."
            )

    async def create_session(self, session_id: str, workflow_name: str, initial_stage: str) -> None:
        """Create new workflow session"""
        self._ensure_pool()

        existing = await self._pool.fetchval(
            "SELECT session_id FROM workflow_sessions WHERE session_id = $1", session_id
        )

        if existing:
            raise ValueError(f"Session {session_id} already exists")

        await self._pool.execute(
            """
            INSERT INTO workflow_sessions
                (session_id, workflow_name, current_stage, global_state, stage_states)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
            """,
            session_id,
            workflow_name,
            initial_stage,
            self._dump_json({}),
            self._dump_json({initial_stage: {}}),
        )

        await self._snapshot(session_id)

    async def update_global_state(self, session_id: str, state_json: Dict[str, Any]) -> None:
        """Update global state (merged)."""
        self._ensure_pool()

        current = await self._pool.fetchval(
            "SELECT global_state FROM workflow_sessions WHERE session_id = $1", session_id
        )

        if current is None:
            raise ValueError(f"Session {session_id} not found")

        current_dict = self._load_json(current)
        merged = {**current_dict, **state_json}

        await self._pool.execute(
            """
            UPDATE workflow_sessions
            SET global_state = $1::jsonb,
                updated_at = NOW(),
                version = version + 1
            WHERE session_id = $2
            """,
            self._dump_json(merged),
            session_id,
        )

        await self._snapshot(session_id)

    async def update_stage_state(self, session_id: str, stage_id: str, state_json: Dict[str, Any]) -> None:
        """Update stage-specific state (merged)."""
        self._ensure_pool()

        row = await self._pool.fetchrow("SELECT stage_states FROM workflow_sessions WHERE session_id = $1", session_id)

        if row is None:
            raise ValueError(f"Session {session_id} not found")

        stage_states = self._load_json(row["stage_states"])
        current_stage_state = stage_states.get(stage_id, {})
        merged_stage_state = {**current_stage_state, **state_json}
        stage_states[stage_id] = merged_stage_state

        await self._pool.execute(
            """
            UPDATE workflow_sessions 
            SET stage_states = $1::jsonb,
                updated_at = NOW(),
                version = version + 1
            WHERE session_id = $2
            """,
            self._dump_json(stage_states),
            session_id,
        )

        await self._snapshot(session_id)

    async def update_current_stage(self, session_id: str, stage_id: str) -> None:
        """Update current stage pointer."""
        self._ensure_pool()

        stage_states = await self._pool.fetchval(
            "SELECT stage_states FROM workflow_sessions WHERE session_id = $1", session_id
        )

        if stage_states is None:
            raise ValueError(f"Session {session_id} not found")

        stage_states = self._load_json(stage_states)

        if stage_id not in stage_states:
            stage_states[stage_id] = {}

        await self._pool.execute(
            """
            UPDATE workflow_sessions 
            SET current_stage = $1,
                stage_states = $2::jsonb,
                updated_at = NOW(),
                version = version + 1
            WHERE session_id = $3
            """,
            stage_id,
            self._dump_json(stage_states),
            session_id,
        )

        await self._snapshot(session_id)

    async def get_global_state(self, session_id: str) -> Dict[str, Any]:
        """Get current global state."""
        self._ensure_pool()

        state = await self._pool.fetchval(
            "SELECT global_state FROM workflow_sessions WHERE session_id = $1", session_id
        )

        if state is None:
            raise ValueError(f"Session {session_id} not found")

        return self._load_json(state)

    async def get_stage_state(self, session_id: str, stage_id: str) -> Dict[str, Any]:
        """Get current stage-specific state."""
        self._ensure_pool()

        stage_states = await self._pool.fetchval(
            "SELECT stage_states FROM workflow_sessions WHERE session_id = $1", session_id
        )

        if stage_states is None:
            raise ValueError(f"Session {session_id} not found")

        stage_states_dict = self._load_json(stage_states)
        return stage_states_dict.get(stage_id, {})

    async def get_state_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all historical states for a session."""
        self._ensure_pool()

        rows = await self._pool.fetch(
            """
            SELECT 
                workflow_name,
                current_stage,
                global_state,
                stage_states,
                version,
                timestamp
            FROM state_history
            WHERE session_id = $1
            ORDER BY timestamp ASC
            """,
            session_id,
        )

        history = []
        for row in rows:
            global_state = self._load_json(row["global_state"])
            stage_states = self._load_json(row["stage_states"])
            history.append(
                {
                    "session_id": session_id,
                    "workflow_name": row["workflow_name"],
                    "current_stage": row["current_stage"],
                    "global_state": global_state,
                    "stage_states": stage_states,
                    "version": row["version"],
                    "timestamp": row["timestamp"].isoformat(),
                }
            )

        return history

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        self._ensure_pool()

        result = await self._pool.execute("DELETE FROM workflow_sessions WHERE session_id = $1", session_id)

        await self._pool.execute("DELETE FROM state_history WHERE session_id = $1", session_id)

        return result != "DELETE 0"

    async def _snapshot(self, session_id: str):
        """Take a snapshot of current state for history."""
        self._ensure_pool()

        row = await self._pool.fetchrow(
            """
            SELECT workflow_name, current_stage, global_state, stage_states, version
            FROM workflow_sessions
            WHERE session_id = $1
            """,
            session_id,
        )

        if row:
            global_state = self._load_json(row["global_state"])
            stage_states = self._load_json(row["stage_states"])
            await self._pool.execute(
                """
                INSERT INTO state_history 
                    (session_id, workflow_name, current_stage, global_state, stage_states, version)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
                """,
                session_id,
                row["workflow_name"],
                row["current_stage"],
                self._dump_json(global_state),
                self._dump_json(stage_states),
                row["version"],
            )
