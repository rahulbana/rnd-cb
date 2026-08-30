import React from "react";

function Macro({ label, value, unit }) {
  return (
    <div className="macro">
      <span className="macro-value">{Math.round(value)}{unit}</span>
      <span className="macro-label">{label}</span>
    </div>
  );
}

function SafetyBanner({ safety }) {
  const cls = safety.approved ? "banner ok" : "banner blocked";
  return (
    <div className={cls}>
      <strong>{safety.approved ? "✓ Reviewed & approved" : "⚠ Needs attention"}</strong>
      <p>{safety.summary}</p>
      {safety.issues.length > 0 && (
        <ul>
          {safety.issues.map((i, idx) => (
            <li key={idx} className={`issue ${i.severity}`}>
              <b>{i.severity}:</b> {i.message}
            </li>
          ))}
        </ul>
      )}
      <p className="disclaimer">{safety.disclaimer}</p>
    </div>
  );
}

export default function PlanView({ plan }) {
  if (!plan) return null;
  const { nutrition, meal_plan, safety } = plan;

  return (
    <div className="plan">
      <SafetyBanner safety={safety} />

      <div className="card">
        <h2>Nutrition targets</h2>
        <div className="targets">
          <Macro label="Daily calories" value={nutrition.target_kcal} unit=" kcal" />
          <Macro label="Protein" value={nutrition.macros.protein_g} unit=" g" />
          <Macro label="Carbs" value={nutrition.macros.carbs_g} unit=" g" />
          <Macro label="Fat" value={nutrition.macros.fat_g} unit=" g" />
          <Macro label="BMI" value={nutrition.bmi} unit="" />
        </div>
        <p className="muted">
          {nutrition.bmi_category} · {nutrition.rationale}
        </p>
      </div>

      {meal_plan.source === "fallback" && (
        <div className="banner warn">
          Generated with the deterministic template planner (no OpenAI key set).
          Set <code>OPENAI_API_KEY</code> on the backend for LLM-generated plans.
        </div>
      )}

      {meal_plan.days.map((day) => (
        <div className="card" key={day.day}>
          <div className="day-header">
            <h3>{day.day}</h3>
            <span className="muted">
              {Math.round(day.total_calories)} kcal · P{Math.round(day.total_protein_g)}
              /C{Math.round(day.total_carbs_g)}/F{Math.round(day.total_fat_g)} g
            </span>
          </div>
          {day.meals.map((meal) => (
            <div className="meal" key={meal.name}>
              <div className="meal-title">
                <b>{meal.name}</b>
                <span className="muted">{Math.round(meal.calories)} kcal</span>
              </div>
              <ul>
                {meal.items.map((item, i) => (
                  <li key={i}>
                    {item.name} — {item.quantity}{" "}
                    <span className="muted">
                      ({Math.round(item.calories)} kcal)
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ))}

      {meal_plan.general_tips?.length > 0 && (
        <div className="card">
          <h3>Tips</h3>
          <ul>
            {meal_plan.general_tips.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
          <p className="muted">Hydration target: {meal_plan.hydration_liters} L/day</p>
        </div>
      )}
    </div>
  );
}
