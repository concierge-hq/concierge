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
    
    async def create_session(
        self,
        session_id: str,
        workflow_name: str,
        initial_stage: str,
        user_id: Optional[str] = None
    ) -> None:
        """Create new workflow session"""
        self._ensure_pool()
        
        existing = await self._pool.fetchval(
            "SELECT session_id FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if existing:
            raise ValueError(f"Session {session_id} already exists") 
        
        await self._pool.execute(
            """
            INSERT INTO workflow_sessions 
                (session_id, workflow_name, current_stage, global_state, stage_states, user_id)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
            """,
            session_id,
            workflow_name,
            initial_stage,
            self._dump_json({}),
            self._dump_json({initial_stage: {}}),
            user_id
        )
        
        await self._snapshot(session_id)
    
    async def save_benchmark_logs(self, session_id: str, logs: List[Dict[str, Any]]) -> None:
        """Save benchmark logs to dedicated table."""
        self._ensure_pool()
        
        await self._pool.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_logs (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT,
                timestamp FLOAT,
                payload JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_benchmark_logs_session ON benchmark_logs(session_id);
        """)
        
        if not logs:
            return

        records = [
            (
                session_id,
                log.get("type"),
                log.get("ts"),
                self._dump_json(log.get("payload"))
            )
            for log in logs
        ]
        
        await self._pool.executemany("""
            INSERT INTO benchmark_logs (session_id, event_type, timestamp, payload)
            VALUES ($1, $2, $3, $4::jsonb)
        """, records)
    
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
        
        stage_states = self._load_json(row['stage_states'])
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
            session_id
        )
        
        await self._snapshot(session_id)
    
    async def update_session_status(
        self,
        session_id: str,
        status: str
    ) -> None:
        """Update session status (running, completed, failed, cancelled)."""
        self._ensure_pool()
        
        result = await self._pool.execute(
            """
            UPDATE workflow_sessions 
            SET status = $1,
                updated_at = NOW()
            WHERE session_id = $2
            """,
            status,
            session_id
        )
        
        if result == "UPDATE 0":
            raise ValueError(f"Session {session_id} not found")
    
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
        
        return self._load_json(state)
    
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
        
        stage_states_dict = self._load_json(stage_states)
        return stage_states_dict.get(stage_id, {})

    async def get_all_stage_states(
        self,
        session_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get all stage states as dict of stage_name -> state_dict."""
        self._ensure_pool()
        
        stage_states = await self._pool.fetchval(
            "SELECT stage_states FROM workflow_sessions WHERE session_id = $1",
            session_id
        )
        
        if stage_states is None:
            raise ValueError(f"Session {session_id} not found")
        
        return self._load_json(stage_states)
    
    async def list_sessions(self, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent sessions ordered by last update time, optionally filtered by user_id."""
        self._ensure_pool()
        if limit <= 0:
            limit = 50

        rows = await self._pool.fetch(
            """
            SELECT session_id, workflow_name, current_stage, version,
                   created_at, updated_at, status, user_id
            FROM workflow_sessions
            WHERE ($1::text IS NULL OR user_id = $1 OR user_id = '' OR user_id IS NULL)
            ORDER BY updated_at DESC
            LIMIT $2
            """,
            user_id,
            limit
        )

        sessions = []
        for row in rows:
            sessions.append({
                "session_id": row["session_id"],
                "workflow_name": row["workflow_name"],
                "current_stage": row["current_stage"],
                "version": row["version"],
                "status": row["status"],
                "user_id": row["user_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            })
        return sessions
    
    async def log_communication(
        self,
        session_id: str,
        sequence_number: int,
        direction: str, 
        payload: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> None:
        """Log a request or response exchange for debugging."""
        self._ensure_pool()
        
        await self._pool.execute(
            """
            INSERT INTO communication_log 
                (session_id, sequence_number, direction, payload, user_id)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
            session_id,
            sequence_number,
            direction,
            self._dump_json(payload),
            user_id
        )
    
    async def get_communication_log(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all request/response exchanges for a session, optionally filtered by user_id."""
        self._ensure_pool()
        
        rows = await self._pool.fetch(
            """
            SELECT id, sequence_number, direction, payload, timestamp, user_id
            FROM communication_log
            WHERE session_id = $1
              AND ($2::text IS NULL OR user_id = $2 OR user_id = '' OR user_id IS NULL)
            ORDER BY sequence_number ASC, id ASC
            """,
            session_id,
            user_id
        )
        
        log = []
        for row in rows:
            log.append({
                "id": row["id"],
                "sequence_number": row["sequence_number"],
                "direction": row["direction"],
                "payload": self._load_json(row["payload"]),
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "user_id": row["user_id"],
            })
        return log
    
    async def get_state_history(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all historical states for a session, optionally filtered by user_id."""
        self._ensure_pool()
        
        rows = await self._pool.fetch(
            """
            SELECT 
                workflow_name,
                current_stage,
                global_state,
                stage_states,
                version,
                timestamp,
                user_id
            FROM state_history
            WHERE session_id = $1
              AND ($2::text IS NULL OR user_id = $2 OR user_id = '' OR user_id IS NULL)
            ORDER BY timestamp ASC
            """,
            session_id,
            user_id
        )
        
        history = []
        for row in rows:
            global_state = self._load_json(row['global_state'])
            stage_states = self._load_json(row['stage_states'])
            history.append({
                "session_id": session_id,
                "workflow_name": row['workflow_name'],
                "current_stage": row['current_stage'],
                "global_state": global_state,
                "stage_states": stage_states,
                "version": row['version'],
                "timestamp": row['timestamp'].isoformat(),
                "user_id": row['user_id']
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
            SELECT workflow_name, current_stage, global_state, stage_states, version, user_id
            FROM workflow_sessions
            WHERE session_id = $1
            """,
            session_id
        )
        
        if row:
            global_state = self._load_json(row['global_state'])
            stage_states = self._load_json(row['stage_states'])
            await self._pool.execute(
                """
                INSERT INTO state_history 
                    (session_id, workflow_name, current_stage, global_state, stage_states, version, user_id)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7)
                """,
                session_id,
                row['workflow_name'],
                row['current_stage'],
                self._dump_json(global_state),
                self._dump_json(stage_states),
                row['version'],
                row['user_id']
            )
    
    async def get_execution_stats(self, user_id: str) -> Dict[str, Any]:
        """Get execution statistics for dashboard (global, not per-user)."""
        row = await self._pool.fetchrow(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                   AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration_ms
            FROM workflow_sessions
            """
        )
        
        total = row['total'] or 0
        successful = row['successful'] or 0
        avg_duration = row['avg_duration_ms'] or 0
        
        success_rate = successful / total if total > 0 else 0.0
        
        return {
            "total": int(total),
            "success": int(successful),
            "success_rate": float(success_rate),
            "avg_duration_ms": float(avg_duration)
        }
    
    async def get_hourly_stats(self, hours: int = 24, user_id: str = None) -> List[Dict[str, Any]]:
        """Get hourly aggregated stats for trend analysis."""
        rows = await self._pool.fetch(
            """
            SELECT 
                hour_bucket,
                SUM(total_executions) as total_executions,
                SUM(successful_executions) as successful_executions,
                SUM(failed_executions) as failed_executions,
                SUM(total_duration_ms) as total_duration_ms
            FROM hourly_stats
            WHERE hour_bucket >= NOW() - INTERVAL '1 hour' * $1
            GROUP BY hour_bucket
            ORDER BY hour_bucket DESC
            """,
            hours
        )
        
        return [
            {
                "hour": row['hour_bucket'].isoformat(),
                "total_executions": int(row['total_executions'] or 0),
                "successful_executions": int(row['successful_executions'] or 0),
                "failed_executions": int(row['failed_executions'] or 0),
                "total_duration_ms": int(row['total_duration_ms'] or 0)
            }
            for row in rows
        ]
    
    async def get_trend_percentages(self, user_id: str) -> Dict[str, float]:
        """Calculate trend percentages based on actual session data."""
        # Get current stats from sessions
        current = await self._pool.fetchrow(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration
            FROM workflow_sessions
            """
        )
        
        # Get stats from 1 hour ago (sessions created before that)
        previous = await self._pool.fetchrow(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration
            FROM workflow_sessions
            WHERE created_at < NOW() - INTERVAL '1 hour'
            """
        )
        
        current_total = int(current['total'] or 0)
        current_successful = int(current['successful'] or 0)
        current_duration = float(current['avg_duration'] or 0)
        
        prev_total = int(previous['total'] or 0)
        prev_successful = int(previous['successful'] or 0)
        prev_duration = float(previous['avg_duration'] or 0)
        
        def calc_trend(current_val: float, previous_val: float) -> float:
            if previous_val == 0:
                return 100.0 if current_val > 0 else 0.0
            return ((current_val - previous_val) / previous_val) * 100
        
        # Calculate success rates
        current_rate = current_successful / current_total if current_total > 0 else 0
        prev_rate = prev_successful / prev_total if prev_total > 0 else 0
        
        # Success rate trend: absolute change in percentage points
        # e.g., was 100%, now 80% = -20 percentage points
        rate_change = (current_rate - prev_rate) * 100
        
        return {
            "executions_trend": calc_trend(current_total, prev_total),
            "success_rate_trend": rate_change,
            "duration_trend": calc_trend(current_duration, prev_duration)
        }

