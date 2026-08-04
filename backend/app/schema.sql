-- Schema for the desktop AI coding agent (FastAPI backend).
CREATE TABLE IF NOT EXISTS conversations (
  id           UUID PRIMARY KEY,
  title        TEXT NOT NULL DEFAULT 'New conversation',
  project_path TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id              UUID PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
  content         TEXT NOT NULL DEFAULT '',
  tool_calls      JSONB,
  tool_call_id    TEXT,
  name            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
  ON messages (conversation_id, created_at);
