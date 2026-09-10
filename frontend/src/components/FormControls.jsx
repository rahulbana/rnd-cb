// Small, reusable form primitives used across the resume form.

export function Field({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input
        type={type}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

export function TextArea({ label, value, onChange, placeholder, rows = 3 }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <textarea
        rows={rows}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

// Edits an array of strings, one per line, exposed as a textarea. Empty lines
// are preserved while typing; the parent filters blanks before submitting.
export function LinesField({ label, value, onChange, placeholder }) {
  return (
    <TextArea
      label={label}
      value={(value || []).join("\n")}
      placeholder={placeholder}
      rows={4}
      onChange={(text) => onChange(text.split("\n"))}
    />
  );
}

// Comma-separated tags -> array of strings.
export function TagsField({ label, value, onChange, placeholder }) {
  return (
    <Field
      label={label}
      value={(value || []).join(", ")}
      placeholder={placeholder}
      onChange={(text) =>
        onChange(
          text
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        )
      }
    />
  );
}

export function RepeatableSection({ title, items, onAdd, onRemove, renderItem, addLabel }) {
  return (
    <div className="repeatable">
      {items.map((item, idx) => (
        <div className="repeatable-item" key={idx}>
          <div className="repeatable-head">
            <span>
              {title} {idx + 1}
            </span>
            <button type="button" className="btn-remove" onClick={() => onRemove(idx)}>
              Remove
            </button>
          </div>
          {renderItem(item, idx)}
        </div>
      ))}
      <button type="button" className="btn-add" onClick={onAdd}>
        + {addLabel || `Add ${title}`}
      </button>
    </div>
  );
}
