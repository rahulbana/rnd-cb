// Mirrors backend app/schemas/events.py::EventType — the SSE wire contract.
export const EVENT_TYPES = {
  RUN_START: "run_start",
  NODE_START: "node_start",
  NODE_END: "node_end",
  TOOL_CALL: "tool_call",
  TOOL_RESULT: "tool_result",
  TOOL_ERROR: "tool_error",
  SUBQUERIES: "subqueries",
  SOURCE: "source",
  TOKEN: "token",
  REPORT: "report",
  STATS: "stats",
  DONE: "done",
  ERROR: "error",
};

// Events shown in the activity timeline (excludes data-only events like
// subqueries/source/token/report which drive their own panels).
export const TIMELINE_EVENT_TYPES = [
  EVENT_TYPES.RUN_START,
  EVENT_TYPES.NODE_START,
  EVENT_TYPES.NODE_END,
  EVENT_TYPES.TOOL_CALL,
  EVENT_TYPES.TOOL_RESULT,
  EVENT_TYPES.TOOL_ERROR,
];

export const NODE_LABELS = {
  plan_queries: "🧭 Plan",
  search: "🌐 Search",
  synthesize: "✍️ Synthesize",
};
