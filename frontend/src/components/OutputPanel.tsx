import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { StructuredSummary } from "../types";

interface Props {
  status: string;
  meta: string;
  markdown: string;
  structured: StructuredSummary | null;
  error: string | null;
  streaming: boolean;
}

function Section({ title, items }: { title: string; items: string[] }) {
  return (
    <>
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="placeholder">None.</p>
      )}
    </>
  );
}

export function OutputPanel({
  status,
  meta,
  markdown,
  structured,
  error,
  streaming,
}: Props) {
  let body: React.ReactNode;
  if (error) {
    body = <p className="error">{error}</p>;
  } else if (structured) {
    body = (
      <>
        <h2>{structured.title || "Untitled"}</h2>
        <p>{structured.summary}</p>
        <Section title="Key Points" items={structured.keyPoints} />
        <Section title="Decisions" items={structured.decisions} />
        <Section title="Action Items" items={structured.actionItems} />
        <Section title="Entities" items={structured.entities} />
      </>
    );
  } else if (markdown) {
    body = (
      <>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        {streaming && <span className="cursor" />}
      </>
    );
  } else {
    body = <p className="placeholder">Your summary will appear here.</p>;
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Summary</h2>
        <div className="output-meta">{meta}</div>
      </div>
      <div className="status-line">{status}</div>
      <article className="output">{body}</article>
    </section>
  );
}
