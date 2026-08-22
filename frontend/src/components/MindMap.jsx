import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "dark" });

let idCounter = 0;

// Renders Mermaid `mindmap` source into an inline SVG.
export default function MindMap({ code }) {
  const ref = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!code) return;
    let cancelled = false;
    const id = `mindmap-${idCounter++}`;
    setError(null);

    mermaid
      .render(id, code)
      .then(({ svg }) => {
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || "Failed to render mind map.");
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (error) {
    return (
      <div className="error">
        <p>Could not render the mind map.</p>
        <details>
          <summary>Show diagram source</summary>
          <pre>{code}</pre>
        </details>
      </div>
    );
  }

  return <div className="mindmap" ref={ref} />;
}
