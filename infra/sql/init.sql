CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Incidents
CREATE TABLE incidents (
    id           TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'DETECTING',
    service      TEXT NOT NULL,
    anomaly_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at  TIMESTAMPTZ,
    root_cause   TEXT,
    plan_id      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Every envelope stored here for full traceability
CREATE TABLE event_trace (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    envelope_id TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    source      TEXT NOT NULL,
    target      TEXT NOT NULL,
    payload     JSONB NOT NULL,
    trace       JSONB NOT NULL DEFAULT '[]',
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_event_trace_incident ON event_trace(incident_id);
CREATE INDEX idx_event_trace_type     ON event_trace(event_type);

-- Runbook vector memory
CREATE TABLE runbooks (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title      TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    affected   TEXT[] NOT NULL DEFAULT '{}',
    resolution TEXT NOT NULL,
    steps      JSONB NOT NULL DEFAULT '[]',
    outcome    TEXT NOT NULL DEFAULT 'resolved',
    source     TEXT NOT NULL DEFAULT 'manual',
    embedding  vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_runbooks_embedding ON runbooks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- Approval queue
CREATE TABLE approvals (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id  TEXT NOT NULL,
    plan_id      TEXT NOT NULL,
    plan_json    JSONB NOT NULL,
    reason       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    approver     TEXT,
    note         TEXT,
    expires_at   TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded_at TIMESTAMPTZ
);

CREATE INDEX idx_approvals_pending ON approvals(status) WHERE status = 'pending';

-- Saga state for executor
CREATE TABLE saga_state (
    incident_id   TEXT PRIMARY KEY,
    plan_id       TEXT NOT NULL,
    steps_json    JSONB NOT NULL,
    current_step  INT NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'running',
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
