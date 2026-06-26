// Runtime configuration, sourced from Vite env vars (VITE_*) with sensible
// defaults. In dev, apiBase is empty so requests hit the Vite proxy (/api ->
// backend). In production set VITE_API_BASE to the backend origin.
export const config = {
  apiBase: import.meta.env.VITE_API_BASE ?? "",
  defaultSubqueries: Number(import.meta.env.VITE_DEFAULT_SUBQUERIES ?? 4),
};
