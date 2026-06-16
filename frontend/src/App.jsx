import React, { useState } from "react";
import StudyPlanForm from "./components/StudyPlanForm.jsx";
import AgentTimeline from "./components/AgentTimeline.jsx";
import PlanView from "./components/PlanView.jsx";
import { streamStudyPlan } from "./api.js";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);
  const [statuses, setStatuses] = useState({});
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (request) => {
    setLoading(true);
    setError(null);
    setPlan(null);
    setAgents([]);
    setStatuses({});

    try {
      await streamStudyPlan(request, {
        onInit: ({ agents }) => {
          setAgents(agents);
          // The planner starts working immediately.
          setStatuses({ planner: "working" });
        },
        onAgentDone: ({ agent }) => {
          setStatuses((prev) => {
            const next = { ...prev, [agent]: "done" };
            // When the planner finishes, the specialists begin working.
            const specialists = [
              "curriculum_agent",
              "scheduler_agent",
              "resources_agent",
              "assessment_agent",
              "quiz_agent",
            ];
            if (agent === "planner") {
              for (const id of specialists) {
                if (next[id] !== "done") next[id] = "working";
              }
            }
            // When all specialists are done, the compiler is working.
            if (specialists.every((id) => next[id] === "done")) {
              if (next.compiler !== "done") next.compiler = "working";
            }
            return next;
          });
        },
        onComplete: ({ plan }) => {
          setPlan(plan);
          setLoading(false);
        },
        onError: (err) => {
          setError(err.message);
          setLoading(false);
        },
      });
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const reset = () => {
    setPlan(null);
    setAgents([]);
    setStatuses({});
    setError(null);
  };

  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <header className="hero no-print">
        <div className="hero-inner">
          <span className="hero-badge">✨ Powered by multi-agent AI</span>
          <h1>
            <span className="logo">📘 StudyForge</span>
          </h1>
          <p className="tagline">
            A multi-agent AI that designs personalised study plans for students
            in classes 5–12 — any subject, any topic.
          </p>
          <div className="hero-pills">
            <span>🎯 Any subject &amp; topic</span>
            <span>🎓 Classes 5–12</span>
            <span>📝 Quiz &amp; case studies</span>
            <span>⬇ Markdown · JSON · PDF</span>
          </div>
        </div>
      </header>

      <main className="container">
        {!plan && (
          <div className="layout">
            <div className="col">
              <StudyPlanForm onSubmit={handleSubmit} loading={loading} />
            </div>
            <div className="col">
              {agents.length > 0 ? (
                <AgentTimeline agents={agents} statuses={statuses} />
              ) : (
                <div className="card intro no-print">
                  <h3>How it works</h3>
                  <ol className="how">
                    <li>
                      <strong>Lead Planner</strong> designs your plan and
                      delegates to specialist agents.
                    </li>
                    <li>
                      <strong>Curriculum, Scheduler, Resources &amp;
                      Assessment</strong> agents work in parallel.
                    </li>
                    <li>
                      <strong>Lead Coach</strong> assembles everything into one
                      downloadable plan.
                    </li>
                  </ol>
                </div>
              )}
              {error && <div className="card error">⚠️ {error}</div>}
            </div>
          </div>
        )}

        {plan && <PlanView plan={plan} onReset={reset} />}
      </main>

      <footer className="footer no-print">
        Built with React · FastAPI · LangGraph · LangChain · OpenAI
      </footer>
    </div>
  );
}
