import { useRef } from "react";
import { FORMAT_LABELS, LENGTH_LABELS, STYLE_LABELS } from "../labels";
import type {
  AppConfig,
  SummaryFormat,
  SummaryLength,
  SummaryStyle,
} from "../types";

interface Props {
  config: AppConfig | null;
  text: string;
  length: SummaryLength;
  style: SummaryStyle;
  format: SummaryFormat;
  focus: string;
  tokenInfo: string;
  busy: boolean;
  onText: (v: string) => void;
  onLength: (v: SummaryLength) => void;
  onStyle: (v: SummaryStyle) => void;
  onFormat: (v: SummaryFormat) => void;
  onFocus: (v: string) => void;
  onSummarize: () => void;
  onExtract: () => void;
  onCount: () => void;
  onStop: () => void;
  onClear: () => void;
  onSample: () => void;
}

export function InputPanel(props: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    props.onText(await file.text());
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Input</h2>
        <div className="input-actions">
          <label className="file-btn">
            Upload .txt / .md
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.markdown,.text,text/plain"
              hidden
              onChange={onFile}
            />
          </label>
          <button className="ghost" type="button" onClick={props.onSample}>
            Load sample
          </button>
          <button className="ghost" type="button" onClick={props.onClear}>
            Clear
          </button>
        </div>
      </div>

      <textarea
        value={props.text}
        onChange={(e) => props.onText(e.target.value)}
        placeholder="Paste long text here, or upload a .txt / .md file…"
      />

      <div className="stats">
        <span>{props.text.length.toLocaleString()} characters</span>
        <span>{props.tokenInfo}</span>
      </div>

      <div className="controls">
        <label>
          Length
          <select
            value={props.length}
            onChange={(e) => props.onLength(e.target.value as SummaryLength)}
          >
            {(props.config?.lengths ?? []).map((v) => (
              <option key={v} value={v}>
                {LENGTH_LABELS[v] ?? v}
              </option>
            ))}
          </select>
        </label>
        <label>
          Style
          <select
            value={props.style}
            onChange={(e) => props.onStyle(e.target.value as SummaryStyle)}
          >
            {(props.config?.styles ?? []).map((v) => (
              <option key={v} value={v}>
                {STYLE_LABELS[v] ?? v}
              </option>
            ))}
          </select>
        </label>
        <label>
          Format
          <select
            value={props.format}
            onChange={(e) => props.onFormat(e.target.value as SummaryFormat)}
          >
            {(props.config?.formats ?? []).map((v) => (
              <option key={v} value={v}>
                {FORMAT_LABELS[v] ?? v}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="focus-field">
        Focus (optional)
        <input
          type="text"
          value={props.focus}
          onChange={(e) => props.onFocus(e.target.value)}
          placeholder="e.g. emphasize risks and costs"
        />
      </label>

      <div className="run-actions">
        <button
          className="primary"
          type="button"
          disabled={props.busy}
          onClick={props.onSummarize}
        >
          Summarize
        </button>
        <button
          className="secondary"
          type="button"
          disabled={props.busy}
          onClick={props.onExtract}
        >
          Extract structured (JSON)
        </button>
        <button
          className="ghost"
          type="button"
          disabled={props.busy}
          onClick={props.onCount}
        >
          Count tokens
        </button>
        {props.busy && (
          <button className="ghost" type="button" onClick={props.onStop}>
            Stop
          </button>
        )}
      </div>
    </section>
  );
}
