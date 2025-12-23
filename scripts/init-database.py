#!/usr/bin/env python3
"""Database initialization script for Concierge."""

import os
import subprocess
import sys
from pathlib import Path

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "concierge")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")

SCRIPTS_DIR = Path(__file__).parent
SCHEMA_FILE = SCRIPTS_DIR / "init-schema.sql"


def run_psql(sql_or_file: str, is_file: bool = False) -> bool:
    """Run psql command. Returns True on success."""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    cmd = ["psql", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-d", DB_NAME]
    cmd += ["-f", sql_or_file] if is_file else ["-c", sql_or_file]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"Error: {result.stderr}")
        return False
    return True


def main():
    print(f"Concierge DB Setup: {DB_NAME}@{DB_HOST}:{DB_PORT} (user: {DB_USER})")
    
    # Test connection
    if not run_psql("SELECT 1"):
        print(f"ERROR: Cannot connect to database")
        print(f"Ensure PostgreSQL is running and database '{DB_NAME}' exists")
        sys.exit(1)
    
    # Apply schema
    if not SCHEMA_FILE.exists():
        print(f"ERROR: Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)
    
    print(f"Applying schema from {SCHEMA_FILE.name}...")
    if not run_psql(str(SCHEMA_FILE), is_file=True):
        print("ERROR: Failed to apply schema")
        sys.exit(1)
    
    print("Verifying tables...")
    run_psql("\\dt")
    
    print("\n✓ Database initialized successfully!")


if __name__ == "__main__":
    main()
