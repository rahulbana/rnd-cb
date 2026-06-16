/**
 * ResultView renders the output of the agent pipeline: the plan, the final
 * code (with syntax highlighting and a copy button), an explanation, and the
 * reviewer's notes.
 */
import React, { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// Map our backend language labels to the highlighter's language identifiers.
const HIGHLIGHT_LANG = {
  Python: "python",
  JavaScript: "javascript",
  TypeScript: "typescript",
  Java: "java",
  C: "c",
  "C++": "cpp",
  "C#": "csharp",
  Go: "go",
  Rust: "rust",
  Ruby: "ruby",
  PHP: "php",
  Kotlin: "kotlin",
  Swift: "swift",
};

function ResultView({ result }) {
  const [copied, setCopied] = useState(false);

  if (!result) {
    return null;
  }

  const language = HIGHLIGHT_LANG[result.language] || "text";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      // Clipboard may be unavailable (e.g. non-secure context); ignore.
    }
  };

  return (
    <div className="result">
      <section className="card">
        <h2>Implementation plan</h2>
        <ol className="plan">
          {result.plan.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>{result.language} solution</h2>
          <button className="copy-btn" onClick={handleCopy}>
            {copied ? "Copied!" : "Copy code"}
          </button>
        </div>
        <SyntaxHighlighter
          language={language}
          style={oneDark}
          showLineNumbers
          wrapLongLines
        >
          {result.code}
        </SyntaxHighlighter>
      </section>

      {result.explanation && (
        <section className="card">
          <h2>How it works</h2>
          <p>{result.explanation}</p>
        </section>
      )}

      {result.review_notes && result.review_notes.length > 0 && (
        <section className="card">
          <h2>Reviewer notes</h2>
          <ul className="notes">
            {result.review_notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export default ResultView;
