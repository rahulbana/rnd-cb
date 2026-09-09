import React, { useCallback, useEffect, useRef, useState } from "react";
import Login from "./components/Login.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import * as api from "./api.js";

export default function App() {
  const [user, setUser] = useState(null); // { username, model, temperature_supported }
  const [booting, setBooting] = useState(true);

  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);

  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState("");
  const [showSettings, setShowSettings] = useState(false);

  const abortRef = useRef(null);

  // --- Session bootstrap ----------------------------------------------------
  useEffect(() => {
    (async () => {
      if (api.getStoredAuth()) {
        try {
          const info = await api.fetchMe();
          setUser(info);
        } catch {
          api.clearAuth();
        }
      }
      setBooting(false);
    })();
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      return list;
    } catch (err) {
      if (err.status === 401) handleLogout();
      return [];
    }
  }, []);

  useEffect(() => {
    if (user) refreshConversations();
  }, [user, refreshConversations]);

  // --- Auth -----------------------------------------------------------------
  function handleLoggedIn(info) {
    setUser(info);
  }

  function handleLogout() {
    api.clearAuth();
    setUser(null);
    setConversations([]);
    setActiveId(null);
    setActiveConversation(null);
    setMessages([]);
  }

  // --- Conversation selection ----------------------------------------------
  const selectConversation = useCallback(async (id) => {
    setActiveId(id);
    setError("");
    try {
      const conv = await api.getConversation(id);
      setActiveConversation(conv);
      setMessages(conv.messages || []);
    } catch (err) {
      setError(err.message || "Failed to load conversation.");
    }
  }, []);

  async function handleNew() {
    try {
      const conv = await api.createConversation({});
      setConversations((prev) => [conv, ...prev]);
      setActiveId(conv.id);
      setActiveConversation(conv);
      setMessages([]);
      setError("");
    } catch (err) {
      setError(err.message || "Failed to create conversation.");
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this conversation? This cannot be undone."))
      return;
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeId) {
        setActiveId(null);
        setActiveConversation(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message || "Failed to delete conversation.");
    }
  }

  // --- Sending & streaming --------------------------------------------------
  async function handleSend(content) {
    let conversationId = activeId;
    // Auto-create a conversation if none is active.
    if (!conversationId) {
      try {
        const conv = await api.createConversation({});
        setConversations((prev) => [conv, ...prev]);
        setActiveId(conv.id);
        setActiveConversation(conv);
        conversationId = conv.id;
      } catch (err) {
        setError(err.message || "Failed to create conversation.");
        return;
      }
    }

    setError("");
    const userMsg = {
      id: `local-${Date.now()}`,
      role: "user",
      content,
    };
    setMessages((prev) => [...prev, userMsg]);
    setStreamingText("");
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    let accumulated = "";
    await api.sendMessageStream(conversationId, content, {
      signal: controller.signal,
      onDelta: (text) => {
        accumulated += text;
        setStreamingText(accumulated);
      },
      onDone: () => {
        finalizeAssistant(accumulated);
      },
      onError: (detail) => {
        setError(detail || "Something went wrong.");
        finalizeAssistant(accumulated); // keep any partial text
      },
    });
    abortRef.current = null;
  }

  function finalizeAssistant(text) {
    setIsStreaming(false);
    setStreamingText("");
    if (text) {
      setMessages((prev) => [
        ...prev,
        { id: `asst-${Date.now()}`, role: "assistant", content: text },
      ]);
    }
    // Refresh sidebar (title may have been auto-derived) and reconcile ids.
    refreshConversations();
  }

  function handleStop() {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    finalizeAssistant(streamingText);
  }

  // --- Settings -------------------------------------------------------------
  async function handleSaveSettings(payload) {
    if (!activeId) return;
    try {
      const updated = await api.updateConversation(activeId, payload);
      setActiveConversation(updated);
      setConversations((prev) =>
        prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c))
      );
    } catch (err) {
      setError(err.message || "Failed to save settings.");
    }
  }

  // --- Render ---------------------------------------------------------------
  if (booting) {
    return <div className="boot-screen">Loading…</div>;
  }

  if (!user) {
    return <Login onLoggedIn={handleLoggedIn} />;
  }

  return (
    <div className="app-shell">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={handleNew}
        onDelete={handleDelete}
        username={user.username}
        onLogout={handleLogout}
      />
      <ChatWindow
        conversation={activeConversation}
        messages={messages}
        streamingText={streamingText}
        isStreaming={isStreaming}
        error={error}
        onSend={handleSend}
        onStop={handleStop}
        onOpenSettings={() => setShowSettings(true)}
      />
      {showSettings && activeConversation && (
        <SettingsPanel
          conversation={activeConversation}
          temperatureSupported={user.temperature_supported}
          model={user.model}
          onSave={handleSaveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}
