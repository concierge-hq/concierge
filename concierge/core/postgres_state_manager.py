"""
PostgreSQL-backed StateManager implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
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
        pool_max_size: int = 20
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
            raise ImportError(
                "PostgreSQLStateManager requires asyncpg. "
                "Install it with: pip install asyncpg"
            )
        
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self._pool: Optional[asyncpg.Pool] = None
    
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
                max_size=self.pool_max_size
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
                "PostgreSQLStateManager not initialized. "
                "Call await state_manager.initialize() before use."
            )
    
    def create_session(
        self,
        session_id: str,
        workflow_name: str,
        initial_stage: str
    ) -> None:
        """
        Create new workflow session (synchronous wrapper).
        Uses asyncio.run() to execute async operation.
        """
        import asyncio
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_session_async(session_id, workflow_name, initial_stage))
    
    async def create_session_async(
        self,
        session_id: str,
        workflow_name: str,
        initial_stage: str
    ) -> None:
        """Create new workflow session (idempotent)."""
        self._ensure_pool()
        
        existing = await self._pool.fetchval(
            "SELECT session_id FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if existing:
            return 
        
        await self._pool.execute(
            """
            INSERT INTO workflow_sessions 
                (session_id, workflow_name, current_stage, global_state, stage_states)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session_id,
            workflow_name,
            initial_stage,
            json.dumps({}),
            json.dumps({initial_stage: {}})
        )
        
        await self._snapshot(session_id)
    
    async def update_global_state(
        self,
        session_id: str,
        state_json: Dict[str, Any]
    ) -> None:
        """Update global state (merged)."""
        self._ensure_pool()
        
        current = await self._pool.fetchval(
            "SELECT global_state FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if current is None:
            raise ValueError(f"Session {session_id} not found")
        
        merged = {**current, **state_json}
        
        await self._pool.execute(
            """
            UPDATE workflow_sessions 
            SET global_state = $1, 
                updated_at = NOW(),
                version = version + 1
            WHERE session_id = $2
            """,
            json.dumps(merged),
            session_id
        )
        
        await self._snapshot(session_id)
    
    async def update_stage_state(
        self,
        session_id: str,
        stage_id: str,
        state_json: Dict[str, Any]
    ) -> None:
        """Update stage-specific state (merged)."""
        self._ensure_pool()
        
        row = await self._pool.fetchrow(
            "SELECT stage_states FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if row is None:
            raise ValueError(f"Session {session_id} not found")
        
        stage_states = row['stage_states']
        current_stage_state = stage_states.get(stage_id, {})
        merged_stage_state = {**current_stage_state, **state_json}
        stage_states[stage_id] = merged_stage_state
        
        await self._pool.execute(
            """
            UPDATE workflow_sessions 
            SET stage_states = $1,
                updated_at = NOW(),
                version = version + 1
            WHERE session_id = $2
            """,
            json.dumps(stage_states),
            session_id
        )
        
        await self._snapshot(session_id)
    
    async def update_current_stage(
        self,
        session_id: str,
        stage_id: str
    ) -> None:
        """Update current stage pointer."""
        self._ensure_pool()
        
        stage_states = await self._pool.fetchval(
            "SELECT stage_states FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if stage_states is None:
            raise ValueError(f"Session {session_id} not found")
        
        if stage_id not in stage_states:
            stage_states[stage_id] = {}
        
        await self._pool.execute(
            """
            UPDATE workflow_sessions 
            SET current_stage = $1,
                stage_states = $2,
                updated_at = NOW(),
                version = version + 1
            WHERE session_id = $3
            """,
            stage_id,
            json.dumps(stage_states),
            session_id
        )
        
        await self._snapshot(session_id)
    
    async def get_global_state(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Get current global state."""
        self._ensure_pool()
        
        state = await self._pool.fetchval(
            "SELECT global_state FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if state is None:
            raise ValueError(f"Session {session_id} not found")
        
        return dict(state)
    
    async def get_stage_state(
        self,
        session_id: str,
        stage_id: str
    ) -> Dict[str, Any]:
        """Get current stage-specific state."""
        self._ensure_pool()
        
        stage_states = await self._pool.fetchval(
            "SELECT stage_states FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if stage_states is None:
            raise ValueError(f"Session {session_id} not found")
        
        return dict(stage_states.get(stage_id, {}))
    
    async def get_state_history(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
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
            session_id
        )
        
        history = []
        for row in rows:
            history.append({
                "session_id": session_id,
                "workflow_name": row['workflow_name'],
                "current_stage": row['current_stage'],
                "global_state": row['global_state'],
                "stage_states": row['stage_states'],
                "version": row['version'],
                "timestamp": row['timestamp'].isoformat()
            })
        
        return history
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        self._ensure_pool()
        
        result = await self._pool.execute(
            "DELETE FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        await self._pool.execute(
            "DELETE FROM state_history WHERE session_id = $1",
            session_id
        )
        
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
            session_id
        )
        
        if row:
            await self._pool.execute(
                """
                INSERT INTO state_history 
                    (session_id, workflow_name, current_stage, global_state, stage_states, version)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                session_id,
                row['workflow_name'],
                row['current_stage'],
                json.dumps(row['global_state']),
                json.dumps(row['stage_states']),
                row['version']
            )

