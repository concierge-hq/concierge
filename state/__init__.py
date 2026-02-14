import os

# Environment variable for state backend URL
STATE_URL = os.getenv("CONCIERGE_STATE_URL")


def get_default_backend():
    """Get state backend based on environment or default to in-memory."""
    if not STATE_URL:
        from concierge.state.memory import InMemoryBackend
        print("State backend: InMemoryBackend")
        return InMemoryBackend()
    
    if STATE_URL.startswith("postgresql://") or STATE_URL.startswith("postgres://"):
        from concierge.state.postgres import PostgresBackend
        # Mask password in log
        masked_url = STATE_URL.split("@")[-1] if "@" in STATE_URL else STATE_URL
        print(f"State backend: PostgresBackend ({masked_url})")
        return PostgresBackend(STATE_URL)
    
    raise ValueError(
        f"Unknown state backend URL scheme: {STATE_URL}. "
        "Supported: postgresql://, postgres://"
    )
