from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from concierge.core.postgres_state_manager import PostgreSQLStateManager


class GitDeploymentStore:
    """Persistence layer for Git-based workflow deployments."""

    def __init__(self, state_manager: PostgreSQLStateManager):
        self._state_manager = state_manager

    def _get_pool(self):
        pool = getattr(self._state_manager, "_pool", None)
        if pool is None:
            raise RuntimeError("PostgreSQLStateManager pool is not initialized")
        return pool

    async def create_deployment(
        self,
        *,
        workspace: str,
        workflow_name: str,
        repo_url: str,
        branch: Optional[str],
        status: str,
    ) -> Dict[str, Any]:
        pool = self._get_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO concierge_git_deployments (
                workspace,
                workflow_name,
                repo_url,
                branch,
                status
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, created_at
            """,
            workspace,
            workflow_name,
            repo_url,
            branch,
            status,
        )
        created_at = row["created_at"] if row and row.get("created_at") else None
        created_iso = created_at.isoformat() if isinstance(created_at, datetime) else None
        return {
            "id": row["id"] if row else None,
            "workspace": workspace,
            "workflow_name": workflow_name,
            "status": status,
            "created_at": created_iso,
        }

    async def update_status(
        self,
        deployment_id: int,
        *,
        status: str,
        artifact_path: Optional[str] = None,
        commit_sha: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        pool = self._get_pool()
        await pool.execute(
            """
            UPDATE concierge_git_deployments
            SET status = $1,
                artifact_path = COALESCE($2, artifact_path),
                commit_sha = COALESCE($3, commit_sha),
                error_message = $4,
                updated_at = NOW()
            WHERE id = $5
            """,
            status,
            artifact_path,
            commit_sha,
            error_message,
            deployment_id,
        )

    async def get_deployment(self, deployment_id: int) -> Optional[Dict[str, Any]]:
        pool = self._get_pool()
        row = await pool.fetchrow(
            """
            SELECT id, workspace, workflow_name, repo_url, branch, status,
                   artifact_path, commit_sha, error_message,
                   created_at, updated_at
            FROM concierge_git_deployments
            WHERE id = $1
            """,
            deployment_id,
        )
        if row is None:
            return None
        created_at = row.get("created_at")
        updated_at = row.get("updated_at")
        return {
            "id": row.get("id"),
            "workspace": row.get("workspace"),
            "workflow_name": row.get("workflow_name"),
            "repo_url": row.get("repo_url"),
            "branch": row.get("branch"),
            "status": row.get("status"),
            "artifact_path": row.get("artifact_path"),
            "commit_sha": row.get("commit_sha"),
            "error_message": row.get("error_message"),
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else None,
            "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
        }

