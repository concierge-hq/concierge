"""
Shared tool definitions for the MySQL migration example.
"""

from __future__ import annotations

import random
import time
from typing import Annotated

from concierge.core.sharable import Sharable


def register_tools(server):
    """Register all 9 MySQL migration tools on the given Concierge server."""

    @server.tool()
    def preflight_check() -> dict:
        """Check MySQL cluster health, replication lag, and disk space."""
        return {
            "status": "healthy",
            "replication_lag_ms": random.randint(0, 120),
            "disk_free_gb": round(random.uniform(80, 200), 1),
            "active_connections": server.get_state("connections", 148),
            "version": "8.0.36",
        }

    @server.tool()
    def drain_connections() -> dict:
        """Gracefully drain all active MySQL connections before migration."""
        server.set_state("drained", True)
        server.set_state("connections", 0)
        return {
            "status": "drained",
            "connections_terminated": 148,
            "remaining_connections": 0,
        }

    @server.tool()
    def create_backup(database: str) -> dict:
        """Create a full logical backup (mysqldump) of the target database."""
        backup_id = f"bkp-{database}-{int(time.time())}"
        server.set_state("backup_id", backup_id)
        return {
            "status": "completed",
            "backup_id": backup_id,
            "database": database,
            "size_mb": round(random.uniform(200, 900), 1),
            "duration_seconds": round(random.uniform(10, 60), 1),
        }

    @server.tool()
    def validate_backup(backup_id: Annotated[str, Sharable()]) -> dict:
        """Validate the integrity of a MySQL backup by restoring to a scratch instance."""
        if server.get_state("backup_id") != backup_id:
            return {"status": "error", "reason": f"unknown backup: {backup_id}"}
        server.set_state("backup_valid", True)
        return {
            "status": "valid",
            "backup_id": backup_id,
            "tables_checked": 47,
            "checksum_match": True,
        }

    @server.tool()
    def apply_migration(migration_file: str) -> dict:
        """Execute the SQL migration script against the database."""
        if not server.get_state("drained"):
            return {
                "status": "error",
                "reason": "database is not drained — unsafe to migrate",
            }
        if not server.get_state("backup_valid"):
            return {
                "status": "error",
                "reason": "no validated backup exists — refusing to migrate",
            }
        server.set_state("migration_applied", True)
        return {
            "status": "applied",
            "migration_file": migration_file,
            "statements_executed": random.randint(3, 15),
            "duration_seconds": round(random.uniform(1, 8), 1),
        }

    @server.tool()
    def run_smoke_tests() -> dict:
        """Run post-migration smoke tests against key tables and queries."""
        if not server.get_state("migration_applied"):
            return {"status": "error", "reason": "migration has not been applied yet"}
        passed = random.choice([True, True, True, False])
        server.set_state("smoke_passed", passed)
        return {
            "status": "passed" if passed else "failed",
            "tests_run": 12,
            "tests_passed": 12 if passed else 9,
            "tests_failed": 0 if passed else 3,
            "duration_seconds": round(random.uniform(4, 18), 1),
        }

    @server.tool()
    def undrain_connections() -> dict:
        """Re-enable new client connections to the MySQL cluster."""
        server.set_state("drained", False)
        server.set_state("connections", random.randint(30, 80))
        return {
            "status": "connections_restored",
            "active_connections": server.get_state("connections"),
        }

    @server.tool()
    def notify_stakeholders(channel: str, message: Annotated[str, Sharable()]) -> dict:
        """Send a notification to the team about migration status."""
        return {
            "status": "sent",
            "channel": channel,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    @server.tool()
    def finalize_migration() -> dict:
        """Mark the migration as complete and clean up temporary artifacts."""
        server.set_state("finalized", True)
        return {
            "status": "finalized",
            "migration_applied": server.get_state("migration_applied"),
            "smoke_passed": server.get_state("smoke_passed"),
            "backup_retained": True,
            "backup_id": server.get_state("backup_id"),
        }
