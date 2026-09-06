import { useEffect, useState } from "react";
import { getProviders, getHealth } from "../lib/api-client";

/**
 * Phase 1 scaffold. The full enterprise app (auth, chat, documents, admin,
 * analytics) is built in Phase 8. This screen only proves the frontend is
 * wired to the API and reads the live provider configuration.
 */
export function App() {
  const [health, setHealth] = useState<string>("checking…");
  const [providers, setProviders] = useState<Record<string, string>>({});

  useEffect(() => {
    getHealth()
      .then((h) => setHealth(h.status))
      .catch(() => setHealth("unreachable"));
    getProviders()
      .then(setProviders)
      .catch(() => setProviders({}));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "3rem auto" }}>
      <h1>Multi-Document RAG Platform</h1>
      <p>Phase 1 skeleton — ports &amp; adapters core.</p>
      <p>
        API health: <strong>{health}</strong>
      </p>
      <h2>Active adapters (live wiring)</h2>
      <ul>
        {Object.entries(providers).map(([port, impl]) => (
          <li key={port}>
            <code>{port}</code>: {impl}
          </li>
        ))}
      </ul>
    </main>
  );
}
