import React, { useState } from "react";

import { config } from "../../config";

export default function SearchBox({ onSubmit, running, onCancel }) {
  const [query, setQuery] = useState("");
  const [n, setN] = useState(config.defaultSubqueries);

  const submit = (e) => {
    e.preventDefault();
    onSubmit(query, n);
  };

  return (
    <form className="search-box" onSubmit={submit}>
      <input
        type="text"
        placeholder="Ask anything… e.g. 'What are the latest advances in solid-state batteries?'"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={running}
      />
      <label className="subq-control" title="Number of sub-queries">
        sub-queries
        <input
          type="number"
          min="1"
          max="10"
          value={n}
          onChange={(e) => setN(Number(e.target.value))}
          disabled={running}
        />
      </label>
      {running ? (
        <button type="button" className="btn cancel" onClick={onCancel}>
          Stop
        </button>
      ) : (
        <button type="submit" className="btn">
          Research
        </button>
      )}
    </form>
  );
}
