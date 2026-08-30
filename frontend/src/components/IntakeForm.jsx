import React, { useState } from "react";

const DEFAULTS = {
  age: 30,
  sex: "male",
  height_cm: 175,
  weight_kg: 75,
  activity_level: "moderate",
  goal: "maintain",
  diet_type: "balanced",
  meals_per_day: 3,
  allergies: "",
  dislikes: "",
  notes: "",
};

const ACTIVITY = ["sedentary", "light", "moderate", "active", "very_active"];
const GOALS = ["lose_weight", "maintain", "gain_muscle"];
const DIETS = [
  "balanced",
  "vegetarian",
  "vegan",
  "keto",
  "mediterranean",
  "high_protein",
];

function toCsvList(value) {
  return value
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

export default function IntakeForm({ onSubmit, loading }) {
  const [form, setForm] = useState(DEFAULTS);

  const update = (key) => (e) => {
    const value =
      e.target.type === "number" ? Number(e.target.value) : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };

  const submit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      allergies: toCsvList(form.allergies),
      dislikes: toCsvList(form.dislikes),
    });
  };

  return (
    <form className="card form" onSubmit={submit}>
      <h2>Your details</h2>
      <div className="grid">
        <label>
          Age
          <input type="number" min="13" max="100" value={form.age} onChange={update("age")} required />
        </label>
        <label>
          Sex
          <select value={form.sex} onChange={update("sex")}>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </label>
        <label>
          Height (cm)
          <input type="number" min="120" max="250" value={form.height_cm} onChange={update("height_cm")} required />
        </label>
        <label>
          Weight (kg)
          <input type="number" min="30" max="400" value={form.weight_kg} onChange={update("weight_kg")} required />
        </label>
        <label>
          Activity
          <select value={form.activity_level} onChange={update("activity_level")}>
            {ACTIVITY.map((a) => (
              <option key={a} value={a}>{a.replace("_", " ")}</option>
            ))}
          </select>
        </label>
        <label>
          Goal
          <select value={form.goal} onChange={update("goal")}>
            {GOALS.map((g) => (
              <option key={g} value={g}>{g.replace("_", " ")}</option>
            ))}
          </select>
        </label>
        <label>
          Diet type
          <select value={form.diet_type} onChange={update("diet_type")}>
            {DIETS.map((d) => (
              <option key={d} value={d}>{d.replace("_", " ")}</option>
            ))}
          </select>
        </label>
        <label>
          Meals / day
          <input type="number" min="2" max="6" value={form.meals_per_day} onChange={update("meals_per_day")} />
        </label>
      </div>

      <label>
        Allergies (comma-separated)
        <input type="text" placeholder="e.g. peanut, shellfish" value={form.allergies} onChange={update("allergies")} />
      </label>
      <label>
        Dislikes (comma-separated)
        <input type="text" placeholder="e.g. mushroom, olives" value={form.dislikes} onChange={update("dislikes")} />
      </label>
      <label>
        Notes
        <textarea rows="2" maxLength="500" placeholder="Preferences, schedule, cuisines…" value={form.notes} onChange={update("notes")} />
      </label>

      <button type="submit" disabled={loading}>
        {loading ? "Generating…" : "Generate diet plan"}
      </button>
    </form>
  );
}
