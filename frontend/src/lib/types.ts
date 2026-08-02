export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  /** Tool activity surfaced while the assistant was composing this reply. */
  tools?: ToolActivity[];
  /** True while tokens are still streaming into this message. */
  streaming?: boolean;
}

export interface ToolActivity {
  name: string;
  args?: Record<string, unknown>;
  status?: "running" | "success" | "error";
}

/** Discriminated union of the SSE events emitted by the backend. */
export type StreamEvent =
  | { type: "start"; model: string }
  | { type: "token"; content: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; status: string }
  | { type: "done" }
  | { type: "error"; message: string };
