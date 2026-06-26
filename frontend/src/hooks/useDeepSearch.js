// Encapsulates a deep-search run: streaming, state, and event reduction.
// Components consume the returned state and call start()/cancel().
import { useCallback, useReducer, useRef } from "react";

import { streamSearch } from "../api/searchApi";
import { EVENT_TYPES, TIMELINE_EVENT_TYPES } from "../constants/events";

const initialState = {
  running: false,
  events: [],
  subqueries: [],
  sources: [],
  report: "",
  stats: null,
  error: null,
};

function applyEvent(state, ev) {
  const next = { ...state };

  if (TIMELINE_EVENT_TYPES.includes(ev.type)) {
    next.events = [...state.events, ev];
  }

  switch (ev.type) {
    case EVENT_TYPES.SUBQUERIES:
      next.subqueries = ev.subqueries || [];
      break;
    case EVENT_TYPES.SOURCE:
      if (!state.sources.some((s) => s.url === ev.source.url)) {
        next.sources = [...state.sources, ev.source];
      }
      break;
    case EVENT_TYPES.TOKEN:
      next.report = state.report + ev.text;
      break;
    case EVENT_TYPES.REPORT:
      if (ev.report) next.report = ev.report;
      if (ev.sources) next.sources = ev.sources;
      break;
    case EVENT_TYPES.STATS:
      next.stats = {
        durationMs: ev.duration_ms,
        subqueries: ev.subqueries,
        sources: ev.sources,
        reportChars: ev.report_chars,
      };
      break;
    case EVENT_TYPES.ERROR:
      next.error = ev.error;
      next.running = false;
      break;
    default:
      break;
  }
  return next;
}

function reducer(state, action) {
  switch (action.type) {
    case "START":
      return { ...initialState, running: true };
    case "EVENT":
      return applyEvent(state, action.event);
    case "FAIL":
      return { ...state, error: action.error, running: false };
    case "STOP":
      return { ...state, running: false };
    default:
      return state;
  }
}

export function useDeepSearch() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef(null);

  const start = useCallback(async (query, numSubqueries) => {
    if (!query.trim() || abortRef.current) return;
    dispatch({ type: "START" });

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      for await (const event of streamSearch({
        query,
        numSubqueries,
        signal: controller.signal,
      })) {
        dispatch({ type: "EVENT", event });
      }
    } catch (e) {
      if (e.name !== "AbortError") dispatch({ type: "FAIL", error: e.message });
    } finally {
      dispatch({ type: "STOP" });
      abortRef.current = null;
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    dispatch({ type: "STOP" });
  }, []);

  return { ...state, start, cancel };
}
