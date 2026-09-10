import React from "react";
import Editor from "react-simple-code-editor";
import { highlight, languages } from "prismjs/components/prism-core";
import "prismjs/components/prism-clike";
import "prismjs/components/prism-c";
import "prismjs/components/prism-cpp";
import "prismjs/components/prism-python";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-typescript";
import "prismjs/components/prism-java";
import "prismjs/components/prism-go";
import "prismjs/components/prism-rust";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

// Map our detected language names to Prism grammar keys.
const GRAMMAR = {
  Python: "python",
  JavaScript: "javascript",
  TypeScript: "typescript",
  Java: "java",
  "C++": "cpp",
  C: "c",
  Go: "go",
  Rust: "rust",
  SQL: "sql",
};

export default function CodeEditor({ code, onChange, language }) {
  const grammarKey = GRAMMAR[language] || "javascript";
  const grammar = languages[grammarKey] || languages.javascript;

  return (
    <div className="editor-shell">
      <Editor
        value={code}
        onValueChange={onChange}
        highlight={(c) => highlight(c, grammar, grammarKey)}
        padding={16}
        textareaId="code-input"
        placeholder="Paste or type your code here…"
        className="code-editor"
        style={{
          fontFamily:
            '"Fira Code", "JetBrains Mono", "SF Mono", Menlo, monospace',
          fontSize: 14,
          lineHeight: 1.6,
        }}
      />
    </div>
  );
}
