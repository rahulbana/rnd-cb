import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";
import Composer from "./Composer.jsx";

export default function ChatWindow({
  conversation,
  messages,
  streamingText,
  isStreaming,
  error,
  onSend,
  onStop,
  onOpenSettings,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streamingText]);

  if (!conversation) {
    return (
      <main className="chat-window empty">
        <div className="welcome">
          <h1>💬 AI Chatbot</h1>
          <p>Select a conversation or start a new one to begin.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="chat-window">
      <header className="chat-header">
        <h2 className="chat-title" title={conversation.title}>
          {conversation.title || "New conversation"}
        </h2>
        <button className="settings-btn" onClick={onOpenSettings} title="Settings">
          ⚙ Settings
        </button>
      </header>

      <div className="messages" ref={scrollRef}>
        {messages.length === 0 && !isStreaming && (
          <div className="empty-conversation">
            <p>Send a message to start the conversation.</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
        {isStreaming && (
          <MessageBubble role="assistant" content={streamingText} streaming />
        )}
        {error && <div className="error-banner in-chat">{error}</div>}
      </div>

      <Composer
        onSend={onSend}
        onStop={onStop}
        disabled={isStreaming}
        streaming={isStreaming}
      />
    </main>
  );
}
