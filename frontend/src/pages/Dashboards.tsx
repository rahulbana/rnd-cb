import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Dashboard } from "../api/types";
import { Empty, ErrorText, Spinner } from "../components/ui";

export default function Dashboards() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setDashboards(await api.listDashboards());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Dashboards</h1>
        <p className="muted">Every dashboard you can access.</p>
      </div>

      <ErrorText message={error} />

      {loading ? (
        <Spinner />
      ) : dashboards.length === 0 ? (
        <Empty>You don't have access to any dashboards yet.</Empty>
      ) : (
        <div className="grid-cards">
          {dashboards.map((d) => (
            <Link key={d.id} to={`/dashboards/${d.id}`} className="tile">
              <h3>{d.name}</h3>
              <p className="muted small">{d.description || "No description"}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
