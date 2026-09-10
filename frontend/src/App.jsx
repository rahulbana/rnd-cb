import React, { useEffect, useState } from "react";
import GeneratorForm from "./components/GeneratorForm.jsx";
import Quiz from "./components/Quiz.jsx";
import { checkHealth, generateQuestions, gradeQuiz } from "./api.js";

export default function App() {
  const [quizData, setQuizData] = useState(null);
  const [graded, setGraded] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth({ openai_configured: false }));
  }, []);

  async function handleGenerate(payload) {
    setError("");
    setGraded(null);
    setLoading(true);
    try {
      const data = await generateQuestions(payload);
      setQuizData(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGrade(payload) {
    setError("");
    try {
      const result = await gradeQuiz(payload);
      setGraded(result);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(e.message);
    }
  }

  function reset() {
    setQuizData(null);
    setGraded(null);
    setError("");
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🎓 AI Question Generator</h1>
        <p>Turn any topic or study material into a graded quiz.</p>
      </header>

      {health && !health.openai_configured && (
        <div className="card banner banner--warn">
          ⚠️ The backend has no <code>OPENAI_API_KEY</code> configured. Add it to{" "}
          <code>backend/.env</code> and restart to generate questions.
        </div>
      )}

      {error && <div className="card banner banner--error">{error}</div>}

      {!quizData ? (
        <GeneratorForm onGenerate={handleGenerate} loading={loading} />
      ) : (
        <Quiz
          data={quizData}
          graded={graded}
          onGrade={handleGrade}
          onReset={reset}
        />
      )}

      <footer className="footer">
        Structured generation · JSON schemas · evaluation · educational AI
      </footer>
    </div>
  );
}
