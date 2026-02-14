CREATE TABLE IF NOT EXISTS concierge_session_stages (
    session_id TEXT PRIMARY KEY,
    stage TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS concierge_session_state (
    session_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, key)
);

CREATE INDEX IF NOT EXISTS idx_session_state_session 
ON concierge_session_state(session_id);
