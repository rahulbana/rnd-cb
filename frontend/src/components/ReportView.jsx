import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ReportView({ markdown }) {
  return (
    <div className="report">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
        }}
      >
        {markdown}
      </Markdown>
    </div>
  );
}
