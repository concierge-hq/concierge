CREATE TABLE IF NOT EXISTS workflow_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    workflow_id VARCHAR(255),
    workflow_name VARCHAR(255),
    current_stage VARCHAR(255),
    global_state JSONB DEFAULT '{}',
    stage_states JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    version INTEGER DEFAULT 1,
    duration_ms DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_deployments (
    workflow_id VARCHAR(255) PRIMARY KEY,
    workflow_name VARCHAR(255) NOT NULL,
    worker_host VARCHAR(255) NOT NULL,
    worker_port INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,
    canonical_name VARCHAR(255),
    description TEXT,
    git_url TEXT,
    user_id VARCHAR(255),
    protocol VARCHAR(16) DEFAULT 'aip'
);

CREATE TABLE IF NOT EXISTS communication_log (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    sequence_number INTEGER NOT NULL,
    direction VARCHAR(20) NOT NULL,
    payload JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comm_log_session ON communication_log(session_id);

CREATE TABLE IF NOT EXISTS state_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255),
    current_stage VARCHAR(255),
    global_state JSONB DEFAULT '{}',
    stage_states JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    user_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_state_history_session ON state_history(session_id);

CREATE TABLE IF NOT EXISTS hourly_stats (
    hour_bucket TIMESTAMP PRIMARY KEY,
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    total_duration_ms BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS benchmark_logs (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT,
    timestamp FLOAT,
    payload JSONB,
    stage TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_logs_session ON benchmark_logs(session_id);


CREATE TABLE IF NOT EXISTS llm_exchange_log (
    id SERIAL PRIMARY KEY,
    client_session_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    payload JSONB,
    raw_timestamp DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_exchange_session ON llm_exchange_log(client_session_id);
