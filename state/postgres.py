"""PostgreSQL state backend - for multi-pod distributed deployments."""

import json
from contextlib import contextmanager
from typing import Any, Optional

from concierge.state.base import StateBackend


class PostgresBackend(StateBackend):
    """PostgreSQL-backed state storage. Tables must exist (see schema.sql)."""

    def __init__(self, database_url: str):
        from psycopg2 import pool

        self._pool = pool.ThreadedConnectionPool(
            minconn=1, maxconn=10, dsn=database_url
        )

    @contextmanager
    def _get_conn(self):
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def get_session_stage(self, session_id: str) -> Optional[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT stage FROM concierge_session_stages WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def set_session_stage(self, session_id: str, stage: str) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO concierge_session_stages (session_id, stage, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (session_id) 
                DO UPDATE SET stage = EXCLUDED.stage, updated_at = CURRENT_TIMESTAMP
            """,
                (session_id, stage),
            )

    def delete_session_stage(self, session_id: str) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM concierge_session_stages WHERE session_id = %s",
                (session_id,),
            )

    def get_state(self, session_id: str, key: str) -> Any:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM concierge_session_state WHERE session_id = %s AND key = %s",
                (session_id, key),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def set_state(self, session_id: str, key: str, value: Any) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO concierge_session_state (session_id, key, value, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (session_id, key) 
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """,
                (session_id, key, json.dumps(value)),
            )

    def clear_session(self, session_id: str) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM concierge_session_stages WHERE session_id = %s",
                (session_id,),
            )
            cur.execute(
                "DELETE FROM concierge_session_state WHERE session_id = %s",
                (session_id,),
            )
