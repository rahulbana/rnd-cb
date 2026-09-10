import React, { useState } from "react";

function QuestionInput({ question, index, value, onChange, disabled, result }) {
  const feedbackClass = result
    ? result.correct
      ? "q--correct"
      : "q--wrong"
    : "";

  return (
    <div className={`card question ${feedbackClass}`}>
      <div className="question__head">
        <span className="badge">{question.type.replace("_", " ")}</span>
        <span className="badge badge--muted">{question.difficulty}</span>
      </div>
      <h3 className="question__text">
        Q{index + 1}. {question.question}
      </h3>

      {question.type === "mcq" && (
        <div className="options">
          {question.options.map((o) => (
            <label key={o.label} className="option">
              <input
                type="radio"
                name={`q${index}`}
                value={o.label}
                checked={value === o.label}
                disabled={disabled}
                onChange={() => onChange(o.label)}
              />
              <span>
                <strong>{o.label}.</strong> {o.text}
              </span>
            </label>
          ))}
        </div>
      )}

      {question.type === "true_false" && (
        <div className="options options--row">
          {["true", "false"].map((v) => (
            <label key={v} className="option">
              <input
                type="radio"
                name={`q${index}`}
                value={v}
                checked={value === v}
                disabled={disabled}
                onChange={() => onChange(v)}
              />
              <span>{v[0].toUpperCase() + v.slice(1)}</span>
            </label>
          ))}
        </div>
      )}

      {question.type === "short_answer" && (
        <textarea
          rows={3}
          className="short-answer"
          value={value || ""}
          disabled={disabled}
          placeholder="Type your answer…"
          onChange={(e) => onChange(e.target.value)}
        />
      )}

      {result && (
        <div className="feedback">
          <p>
            <strong>{result.correct ? "✓ Correct" : "✗ Incorrect"}</strong>
            {" — Answer: "}
            <code>{result.expected}</code>
          </p>
          <p className="explanation">{result.explanation}</p>
        </div>
      )}
    </div>
  );
}

export default function Quiz({ data, onGrade, graded, onReset }) {
  const { questions } = data;
  const [answers, setAnswers] = useState({});

  function setAnswer(index, value) {
    setAnswers((prev) => ({ ...prev, [index]: value }));
  }

  function submit() {
    const payload = {
      questions,
      answers: questions.map((_, index) => ({
        index,
        response: String(answers[index] ?? ""),
      })),
    };
    onGrade(payload);
  }

  const resultsByIndex = {};
  if (graded) graded.results.forEach((r) => (resultsByIndex[r.index] = r));

  return (
    <div className="quiz">
      <div className="quiz__bar">
        <div>
          <strong>{data.topic}</strong>
          <span className="badge badge--muted">{data.difficulty}</span>
        </div>
        <button className="btn" onClick={onReset}>
          New set
        </button>
      </div>

      {graded && (
        <div className="card scorecard">
          <div className="scorecard__num">{graded.score_percent}%</div>
          <div>
            You scored <strong>{graded.correct}</strong> / {graded.total}
          </div>
        </div>
      )}

      {questions.map((q, i) => (
        <QuestionInput
          key={i}
          index={i}
          question={q}
          value={answers[i]}
          disabled={!!graded}
          result={resultsByIndex[i]}
          onChange={(v) => setAnswer(i, v)}
        />
      ))}

      {!graded ? (
        <button className="btn btn--primary btn--wide" onClick={submit}>
          Submit Answers
        </button>
      ) : (
        <button className="btn btn--wide" onClick={onReset}>
          Generate a new quiz
        </button>
      )}
    </div>
  );
}
