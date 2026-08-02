import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, ToolActivity } from "../lib/types";

const TOOL_LABELS: Record<string, string> = {
  search_movies: "Searching movies",
  get_movie_details: "Fetching movie details",
  get_trending: "Getting trending titles",
  discover_movies: "Discovering movies",
  search_person: "Searching people",
  list_movie_genres: "Loading genres",
  translate: "Translating",
  list_supported_languages: "Listing languages",
  get_current_time: "Checking the time",
  compare_timezones: "Comparing timezones",
  convert_time: "Converting time",
};

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const showTyping = message.streaming && !message.content && (message.tools?.length ?? 0) === 0;

  return (
    <div className={`bubble-row ${isUser ? "bubble-row--user" : "bubble-row--assistant"}`}>
      <div className="avatar">{isUser ? "🧑" : "🎬"}</div>
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--assistant"}`}>
        {message.tools && message.tools.length > 0 && (
          <div className="tools">
            {message.tools.map((tool, i) => (
              <ToolChip key={`${tool.name}-${i}`} tool={tool} />
            ))}
          </div>
        )}

        {showTyping ? (
          <TypingDots />
        ) : (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            {message.streaming && <span className="cursor" />}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolChip({ tool }: { tool: ToolActivity }) {
  const label = TOOL_LABELS[tool.name] ?? tool.name;
  const icon = tool.status === "success" ? "✓" : tool.status === "error" ? "✕" : "";
  return (
    <span className={`tool-chip tool-chip--${tool.status ?? "running"}`}>
      {tool.status === "running" && <span className="spinner" />}
      {icon && <span className="tool-icon">{icon}</span>}
      {label}
    </span>
  );
}

function TypingDots() {
  return (
    <div className="typing">
      <span />
      <span />
      <span />
    </div>
  );
}
