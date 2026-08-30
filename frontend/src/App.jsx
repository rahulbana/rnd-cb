import React, { useEffect, useState } from "react";
import IntakeForm from "./components/IntakeForm.jsx";
import PlanView from "./components/PlanView.jsx";
import { createPlan, listPlans, getPlan, deletePlan, getHealth } from "./api.js";

export default function App() {
  const [plan, setPlan] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  const refreshHistory = async () => {
    try {
      setHistory(await listPlans());
    } catch (e) {
      // Non-fatal; history is a convenience.
      console.warn("history load failed", e);
    }
  };

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
    refreshHistory();
  }, []);

  const handleSubmit = async (payload) => {
    setLoading(true);
    setError("");
    try {
      const result = await createPlan(payload);
      setPlan(result);
      refreshHistory();
    } catch (e) {
      setError(e.message || "Failed to generate plan");
    } finally {
      setLoading(false);
    }
  };

  const openPlan = async (id) => {
    setError("");
    try {
      setPlan(await getPlan(id));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(e.message);
    }
  };

  const removePlan = async (id) => {
    try {
      await deletePlan(id);
      if (plan?.plan_id === id) setPlan(null);
      refreshHistory();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>🥗 Diet Planner</h1>
        <p className="muted">
          Multi-agent pipeline: intake validation → nutrition calculation → meal
          planning → safety review.
          {health && (
            <span className={`pill ${health.llm_enabled ? "on" : "off"}`}>
              {health.llm_enabled ? `LLM: ${health.model}` : "LLM: fallback mode"}
            </span>
          )}
        </p>
      </header>

      <div className="layout">
        <aside>
          <IntakeForm onSubmit={handleSubmit} loading={loading} />
          {history.length > 0 && (
            <div className="card">
              <h3>Recent plans</h3>
              <ul className="history">
                {history.map((h) => (
                  <li key={h.plan_id}>
                    <button className="link" onClick={() => openPlan(h.plan_id)}>
                      #{h.plan_id} · {h.diet_type} · {Math.round(h.target_kcal)} kcal
                      {h.approved ? " ✓" : " ⚠"}
                    </button>
                    <button className="del" onClick={() => removePlan(h.plan_id)}>
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <main>
          {error && <div className="banner blocked">{error}</div>}
          {loading && <div className="card">Running the agent pipeline…</div>}
          {!loading && !plan && !error && (
            <div className="card muted">
              Fill in your details and generate a personalized diet plan.
            </div>
          )}
          <PlanView plan={plan} />
        </main>
      </div>

      <footer className="muted">
        For informational purposes only — not medical advice.
      </footer>
    </div>
  );
}
