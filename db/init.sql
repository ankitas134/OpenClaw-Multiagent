-- Enable UUID & pgvector extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Enums
DO $$ BEGIN
    CREATE TYPE team_role AS ENUM ('owner', 'admin', 'member');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE agent_status AS ENUM ('pending', 'starting', 'running', 'stopping', 'stopped', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE agent_visibility AS ENUM ('personal', 'team');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE document_visibility AS ENUM ('personal', 'team');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Teams Table
CREATE TABLE IF NOT EXISTS teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    created_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    context_md  TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Team Members Table
CREATE TABLE IF NOT EXISTS team_members (
    team_id   UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
    role      TEXT NOT NULL DEFAULT 'member',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (team_id, user_id)
);

-- Invites Table
CREATE TABLE IF NOT EXISTS invites (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     UUID REFERENCES teams(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',
    token       TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ
);

-- Agents Table
CREATE TABLE IF NOT EXISTS agents (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id        UUID REFERENCES teams(id) ON DELETE CASCADE,
    created_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    name           TEXT NOT NULL,
    config         JSONB NOT NULL DEFAULT '{}',
    container_id   TEXT,
    status         TEXT NOT NULL DEFAULT 'pending',
    visibility     TEXT NOT NULL DEFAULT 'personal',
    task_context   TEXT NOT NULL DEFAULT '',
    workspace_path TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at     TIMESTAMPTZ,
    stopped_at     TIMESTAMPTZ
);

-- Agent Runs Table
CREATE TABLE IF NOT EXISTS agent_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID REFERENCES agents(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent Messages Table
CREATE TABLE IF NOT EXISTS agent_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    sender      TEXT NOT NULL,
    text        TEXT NOT NULL,
    thread_id   TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Refresh Tokens Table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     UUID REFERENCES teams(id) ON DELETE SET NULL,
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id             UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    uploaded_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    visibility          TEXT NOT NULL DEFAULT 'team',
    filename            TEXT NOT NULL,
    mime_type           TEXT NOT NULL,
    size_bytes          INTEGER NOT NULL,
    storage_path        TEXT NOT NULL,
    extracted_text_path TEXT,
    extraction_status   TEXT NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Document Chunks Table with pgvector (384 dimensions for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS document_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(384)
);

-- Agent Documents Junction Table
CREATE TABLE IF NOT EXISTS agent_documents (
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, document_id)
);

-- Indexes for optimal performance and team-isolated queries
CREATE INDEX IF NOT EXISTS idx_agents_team_status ON agents(team_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_created ON agent_runs(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_agent ON agent_messages(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_documents_team ON documents(team_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON document_chunks(document_id);
