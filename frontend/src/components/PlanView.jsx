import React, { useState } from "react";
import { downloadJSON, downloadMarkdown, downloadPDF } from "../download.js";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "curriculum", label: "Curriculum" },
  { id: "schedule", label: "Schedule" },
  { id: "resources", label: "Resources" },
  { id: "assessment", label: "Assessments" },
];

export default function PlanView({ plan, onReset }) {
  const [tab, setTab] = useState("overview");
  const { request: req } = plan;

  return (
    <div className="plan-wrap">
      <div className="card plan-header">
        <div>
          <h2>{plan.outline.title}</h2>
          <p className="plan-meta">
            Class {req.grade} · {req.subject} · {req.topic} · {req.duration_weeks}{" "}
            week(s) · ~{req.hours_per_week} hrs/week
          </p>
        </div>
        <div className="download-menu">
          <button className="btn" onClick={() => downloadMarkdown(plan)}>
            ⬇ Markdown
          </button>
          <button className="btn" onClick={() => downloadJSON(plan)}>
            ⬇ JSON
          </button>
          <button className="btn" onClick={() => downloadPDF()}>
            ⬇ PDF
          </button>
          <button className="btn btn-ghost" onClick={onReset}>
            ↺ New plan
          </button>
        </div>
      </div>

      <div className="tabs no-print">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? "tab-active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Interactive tabbed view — hidden when printing. */}
      <div className="card plan-body no-print">
        {tab === "overview" && <Overview plan={plan} />}
        {tab === "curriculum" && <Curriculum data={plan.curriculum} />}
        {tab === "schedule" && <Schedule data={plan.schedule} />}
        {tab === "resources" && <Resources data={plan.resources} />}
        {tab === "assessment" && <Assessments data={plan.assessment} />}
      </div>

      {/* Full plan — only rendered to the page when printing to PDF. */}
      <div className="card plan-body print-only">
        <Overview plan={plan} />
        <h3 className="print-h">📚 Curriculum</h3>
        <Curriculum data={plan.curriculum} />
        <h3 className="print-h">🗓️ Schedule</h3>
        <Schedule data={plan.schedule} />
        <h3 className="print-h">🔗 Resources</h3>
        <Resources data={plan.resources} />
        <h3 className="print-h">✅ Assessments</h3>
        <Assessments data={plan.assessment} />
      </div>
    </div>
  );
}

function Overview({ plan }) {
  return (
    <section className="section">
      <p className="lead">{plan.outline.overview}</p>
      {plan.outline.learning_goals?.length > 0 && (
        <>
          <h4>🎯 Learning Goals</h4>
          <ul>
            {plan.outline.learning_goals.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </>
      )}
      {plan.outline.prerequisites?.length > 0 && (
        <>
          <h4>📋 Prerequisites</h4>
          <ul>
            {plan.outline.prerequisites.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </>
      )}
      {plan.study_tips?.length > 0 && (
        <>
          <h4>💡 Study Tips</h4>
          <ul>
            {plan.study_tips.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Curriculum({ data }) {
  return (
    <section className="section">
      {data.modules.map((m, i) => (
        <div key={i} className="module">
          <h4>
            <span className="badge">Module {i + 1}</span> {m.title}
          </h4>
          {m.objectives?.length > 0 && (
            <ul>
              {m.objectives.map((o, j) => (
                <li key={j}>{o}</li>
              ))}
            </ul>
          )}
          {m.subtopics?.length > 0 && (
            <p className="chips">
              {m.subtopics.map((s, j) => (
                <span key={j} className="chip">
                  {s}
                </span>
              ))}
            </p>
          )}
        </div>
      ))}
    </section>
  );
}

function Schedule({ data }) {
  return (
    <section className="section">
      {data.weeks.map((w, i) => (
        <div key={i} className="week">
          <h4>
            <span className="badge">Week {w.week_number}</span> {w.focus}
          </h4>
          <ul className="sessions">
            {w.sessions.map((s, j) => (
              <li key={j}>
                <strong>{s.day}</strong>
                <span className="duration">{s.duration_minutes} min</span>
                <span>{s.activity}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

function Resources({ data }) {
  return (
    <section className="section resource-grid">
      {data.resources.map((r, i) => (
        <div key={i} className="resource-card">
          <span className="resource-type">{r.type}</span>
          <h5>
            {r.link ? (
              <a href={r.link} target="_blank" rel="noreferrer">
                {r.title}
              </a>
            ) : (
              r.title
            )}
          </h5>
          <p>{r.description}</p>
        </div>
      ))}
    </section>
  );
}

function Assessments({ data }) {
  return (
    <section className="section">
      {data.assessments.map((a, i) => (
        <div key={i} className="assessment">
          <h4>
            <span className="badge badge-alt">{a.type}</span> {a.title}
          </h4>
          <p>{a.description}</p>
          {a.sample_questions?.length > 0 && (
            <ol className="questions">
              {a.sample_questions.map((q, j) => (
                <li key={j}>{q}</li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </section>
  );
}
