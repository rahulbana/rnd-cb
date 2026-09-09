import React, { useRef, useState } from "react";

export default function Composer({ onSend, disabled, onStop, streaming }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleInput(e) {
    setText(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }

  return (
    <div className="composer">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Send a message…  (Enter to send, Shift+Enter for newline)"
        rows={1}
      />
      {streaming ? (
        <button className="stop-btn" onClick={onStop} title="Stop generating">
          Stop
        </button>
      ) : (
        <button
          className="send-btn"
          onClick={submit}
          disabled={disabled || !text.trim()}
        >
          Send
        </button>
      )}
    </div>
  );
}
