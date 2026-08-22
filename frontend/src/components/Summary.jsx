import ReactMarkdown from "react-markdown";

export default function Summary({ text }) {
  return (
    <div className="markdown">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}
