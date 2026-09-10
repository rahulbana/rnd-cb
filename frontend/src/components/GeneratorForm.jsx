import React, { useState } from "react";

const QUESTION_TYPES = [
  { value: "mcq", label: "Multiple Choice" },
  { value: "true_false", label: "True / False" },
  { value: "short_answer", label: "Short Answer" },
];

const DIFFICULTIES = ["easy", "medium", "hard"];

export default function GeneratorForm({ onGenerate, loading }) {
  const [topic, setTopic] = useState("Python Functions");
  const [difficulty, setDifficulty] = useState("medium");
  const [types, setTypes] = useState(["mcq"]);
  const [num, setNum] = useState(5);

  function toggleType(value) {
    setTypes((prev) =>
      prev.includes(value) ? prev.filter((t) => t !== value) : [...prev, value]
    );
  }

  function submit(e) {
    e.preventDefault();
    if (!topic.trim() || types.length === 0) return;
    onGenerate({
      topic: topic.trim(),
      difficulty,
      question_types: types,
      num_questions: Number(num),
    });
  }

  return (
    <form className="card form" onSubmit={submit}>
      <label className="field">
        <span>Topic / Study material</span>
        <textarea
          rows={5}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Paste study material or type a topic, e.g. 'Python Functions'"
        />
      </label>

      <div className="row">
        <label className="field">
          <span>Difficulty</span>
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>
                {d[0].toUpperCase() + d.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Number of questions</span>
          <input
            type="number"
            min={1}
            max={20}
            value={num}
            onChange={(e) => setNum(e.target.value)}
          />
        </label>
      </div>

      <fieldset className="field">
        <span>Question types</span>
        <div className="chips">
          {QUESTION_TYPES.map((t) => (
            <button
              type="button"
              key={t.value}
              className={`chip ${types.includes(t.value) ? "chip--on" : ""}`}
              onClick={() => toggleType(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </fieldset>

      <button className="btn btn--primary" type="submit" disabled={loading}>
        {loading ? "Generating…" : "Generate Questions"}
      </button>
    </form>
  );
}
