import React, { useState } from "react";

const GRADES = [5, 6, 7, 8, 9, 10, 11, 12];
const LEVELS = ["beginner", "intermediate", "advanced"];

const SUBJECT_SUGGESTIONS = [
  "Mathematics",
  "Physics",
  "Chemistry",
  "Biology",
  "Science",
  "Environmental Science",
  "English",
  "Hindi",
  "Sanskrit",
  "French",
  "Spanish",
  "History",
  "Geography",
  "Civics",
  "Political Science",
  "Economics",
  "Social Studies",
  "Computer Science",
  "Information Technology",
  "Accountancy",
  "Business Studies",
  "Statistics",
  "Psychology",
  "Sociology",
  "Philosophy",
  "Physical Education",
  "Art & Craft",
  "Music",
  "General Knowledge",
];

const DEFAULTS = {
  grade: 8,
  subject: "Mathematics",
  topic: "",
  duration_weeks: 4,
  hours_per_week: 5,
  goal: "build a strong conceptual understanding",
  level: "intermediate",
  notes: "",
};

export default function StudyPlanForm({ onSubmit, loading }) {
  const [form, setForm] = useState(DEFAULTS);

  const update = (key) => (e) => {
    const value = e.target.value;
    setForm((f) => ({
      ...f,
      [key]:
        key === "grade" || key === "duration_weeks" || key === "hours_per_week"
          ? Number(value)
          : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.topic.trim()) return;
    const payload = { ...form };
    if (!payload.notes.trim()) delete payload.notes;
    onSubmit(payload);
  };

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="form-head">
        <h2>Design your study plan</h2>
        <p>Tell us about the student — the agents do the rest.</p>
      </div>

      <div className="grid grid-2">
        <label>
          <span>Class / Grade</span>
          <select value={form.grade} onChange={update("grade")}>
            {GRADES.map((g) => (
              <option key={g} value={g}>
                Class {g}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Current level</span>
          <select value={form.level} onChange={update("level")}>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l[0].toUpperCase() + l.slice(1)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        <span>Subject</span>
        <input
          list="subject-list"
          value={form.subject}
          onChange={update("subject")}
          placeholder="e.g. Mathematics"
          required
        />
        <datalist id="subject-list">
          {SUBJECT_SUGGESTIONS.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </label>

      <label>
        <span>Topic</span>
        <input
          value={form.topic}
          onChange={update("topic")}
          placeholder="e.g. Quadratic Equations, Photosynthesis, World War II"
          required
        />
      </label>

      <div className="grid grid-2">
        <label>
          <span>Duration: {form.duration_weeks} week(s)</span>
          <input
            type="range"
            min="1"
            max="16"
            value={form.duration_weeks}
            onChange={update("duration_weeks")}
          />
        </label>

        <label>
          <span>Time: {form.hours_per_week} hrs/week</span>
          <input
            type="range"
            min="1"
            max="20"
            value={form.hours_per_week}
            onChange={update("hours_per_week")}
          />
        </label>
      </div>

      <label>
        <span>Goal</span>
        <input
          value={form.goal}
          onChange={update("goal")}
          placeholder="What do you want to achieve?"
        />
      </label>

      <label>
        <span>Extra notes (optional)</span>
        <textarea
          rows="2"
          value={form.notes}
          onChange={update("notes")}
          placeholder="Exam date, weak areas, preferred learning style…"
        />
      </label>

      <button className="btn btn-primary" type="submit" disabled={loading}>
        {loading ? "Agents are working…" : "✨ Generate Study Plan"}
      </button>
    </form>
  );
}
