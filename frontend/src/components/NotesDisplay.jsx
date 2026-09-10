import { useState } from "react";

function Section({ title, children, empty }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {empty ? <p className="muted">None identified.</p> : children}
    </div>
  );
}

export default function NotesDisplay({ notes }) {
  const [copied, setCopied] = useState(false);

  async function copyEmail() {
    await navigator.clipboard.writeText(notes.follow_up_email);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="results">
      <Section title="Summary">
        <p>{notes.summary}</p>
      </Section>

      <Section title="Participants" empty={!notes.participants?.length}>
        <div className="chips">
          {notes.participants.map((p, i) => (
            <span key={i} className="chip">{p}</span>
          ))}
        </div>
      </Section>

      <Section title="Decisions" empty={!notes.decisions?.length}>
        <ul>
          {notes.decisions.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>
      </Section>

      <Section title="Action Items" empty={!notes.action_items?.length}>
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>Owner</th>
              <th>Deadline</th>
            </tr>
          </thead>
          <tbody>
            {notes.action_items.map((a, i) => (
              <tr key={i}>
                <td>{a.task}</td>
                <td>{a.owner || "—"}</td>
                <td>{a.deadline || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Deadlines" empty={!notes.deadlines?.length}>
        <ul>
          {notes.deadlines.map((d, i) => (
            <li key={i}>
              <strong>{d.due}</strong> — {d.description}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Follow-up Email">
        <pre className="email">{notes.follow_up_email}</pre>
        <button className="secondary" onClick={copyEmail}>
          {copied ? "Copied!" : "Copy email"}
        </button>
      </Section>
    </section>
  );
}
