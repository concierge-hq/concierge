-- PostgreSQL schema for Concierge StateManager

CREATE TABLE IF NOT EXISTS workflow_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    workflow_name VARCHAR(255) NOT NULL,
    current_stage VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',
    global_state JSONB DEFAULT '{}',
    stage_states JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS state_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255),
    current_stage VARCHAR(255),
    global_state JSONB,
    stage_states JSONB,
    version INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_state_history_session ON state_history(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_sessions_workflow ON workflow_sessions(workflow_name);
CREATE INDEX IF NOT EXISTS idx_workflow_sessions_updated ON workflow_sessions(updated_at);

