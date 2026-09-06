export interface User {
  id: string;
  email: string;
  role: string;
  org_id: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface DocumentOut {
  id: string;
  org_id: string;
  owner_id: string;
  filename: string;
  mime_type: string;
  checksum: string;
  storage_uri: string;
  status: string;
}

export interface JobOut {
  id: string;
  document_id: string;
  stage: string;
  progress: number;
  status: string;
  error: string | null;
  retries: number;
}

export interface IngestAccepted {
  document: DocumentOut;
  job: JobOut | null;
  deduped: boolean;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  page: number | null;
  heading_path: string | null;
  score: number | null;
}

export interface Conversation {
  id: string;
  title: string;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  provider: string | null;
  citations: Citation[];
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
}
