import React from "react";

export default function MessageBubble({ role, content, streaming }) {
  const isUser = role === "user";
  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className="message-avatar">{isUser ? "You" : "AI"}</div>
      <div className="message-bubble">
        {content ? (
          <span className="message-content">{content}</span>
        ) : streaming ? (
          <span className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </span>
        ) : null}
        {streaming && content && <span className="cursor">▍</span>}
      </div>
    </div>
  );
}
