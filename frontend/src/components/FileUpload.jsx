import { useRef, useState } from "react";

export default function FileUpload({ onFile, loading, hasResult }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function pick(files) {
    if (files && files[0]) onFile(files[0]);
  }

  return (
    <div
      className={`dropzone ${dragging ? "dragging" : ""} ${
        hasResult ? "compact" : ""
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        pick(e.dataTransfer.files);
      }}
      onClick={() => !loading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.tsv,.txt"
        hidden
        onChange={(e) => pick(e.target.files)}
      />
      <div className="drop-icon">⬆</div>
      <p className="drop-title">
        {hasResult ? "Analyze another CSV" : "Drop a CSV here or click to browse"}
      </p>
      <p className="drop-sub">
        The agent profiles every column — numbers, text, booleans, dates — and
        explains what it finds.
      </p>
    </div>
  );
}
