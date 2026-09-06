import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Button, Card, Input } from "../../components/ui";
import { api } from "../../lib/api-client";
import type { Citation } from "../../lib/types";

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export function ChatPage() {
  const queryClient = useQueryClient();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: api.listConversations,
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns]);

  async function openConversation(id: string) {
    setConversationId(id);
    const messages = await api.conversationMessages(id);
    setTurns(
      messages.map((m) => ({
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
        citations: m.citations,
      })),
    );
  }

  function newConversation() {
    setConversationId(null);
    setTurns([]);
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || streaming) return;
    setQuestion("");
    setTurns((t) => [...t, { role: "user", content: q }, { role: "assistant", content: "" }]);
    setStreaming(true);
    let citations: Citation[] = [];
    try {
      await api.streamChat(q, conversationId, {
        onMeta: (meta) => {
          setConversationId(meta.conversation_id);
          citations = meta.citations as Citation[];
        },
        onToken: (token) => {
          setTurns((t) => {
            const next = [...t];
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: next[next.length - 1].content + token,
            };
            return next;
          });
        },
        onDone: () => {
          setTurns((t) => {
            const next = [...t];
            next[next.length - 1] = { ...next[next.length - 1], citations };
            return next;
          });
        },
      });
    } finally {
      setStreaming(false);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    }
  }

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white p-3 md:flex">
        <Button className="mb-3 w-full" onClick={newConversation}>
          + New chat
        </Button>
        <p className="mb-1 px-1 text-xs font-medium uppercase text-slate-400">History</p>
        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => openConversation(c.id)}
              className={`w-full truncate rounded-md px-2 py-1.5 text-left text-sm ${
                c.id === conversationId
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {c.title}
            </button>
          ))}
        </div>
      </aside>

      <section className="flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-2xl space-y-4">
            {turns.length === 0 && (
              <p className="mt-10 text-center text-sm text-slate-400">
                Ask a question about your documents.
              </p>
            )}
            {turns.map((turn, i) => (
              <div key={i} className={turn.role === "user" ? "text-right" : ""}>
                <Card
                  className={`inline-block max-w-[85%] p-3 text-left text-sm ${
                    turn.role === "user" ? "bg-brand-600 text-white" : ""
                  }`}
                >
                  <div className="whitespace-pre-wrap">{turn.content || "…"}</div>
                  {turn.citations && turn.citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1 border-t border-slate-200 pt-2">
                      {turn.citations.map((c, idx) => (
                        <span
                          key={c.chunk_id}
                          className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600"
                          title={c.heading_path ?? undefined}
                        >
                          [{idx + 1}] {c.document_id.slice(0, 8)}
                          {c.page != null ? ` p.${c.page}` : ""}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            ))}
          </div>
        </div>
        <form onSubmit={send} className="border-t border-slate-200 bg-white p-3">
          <div className="mx-auto flex max-w-2xl gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question…"
              disabled={streaming}
            />
            <Button type="submit" disabled={streaming || !question.trim()}>
              Send
            </Button>
          </div>
        </form>
      </section>
    </div>
  );
}
