import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";

interface ComposerProps {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

const SUGGESTIONS = [
  "What's trending this week?",
  "Best sci-fi movies from 2019",
  "Translate 'good evening' to Japanese",
  "What time is it in Tokyo vs New York?",
];

export function Composer({ onSend, onStop, isStreaming }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const autoGrow = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  };

  return (
    <div className="composer">
      {value.length === 0 && !isStreaming && (
        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="suggestion" onClick={() => onSend(s)} type="button">
              {s}
            </button>
          ))}
        </div>
      )}

      <form className="composer-form" onSubmit={submit}>
        <textarea
          ref={textareaRef}
          value={value}
          rows={1}
          placeholder="Ask about movies, translations, or world time…"
          onChange={(e) => {
            setValue(e.target.value);
            autoGrow(e.target);
          }}
          onKeyDown={handleKeyDown}
        />
        {isStreaming ? (
          <button type="button" className="btn btn--stop" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button type="submit" className="btn btn--send" disabled={!value.trim()}>
            Send
          </button>
        )}
      </form>
    </div>
  );
}
