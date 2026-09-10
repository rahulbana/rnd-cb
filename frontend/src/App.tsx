import { useEffect, useRef, useState } from "react";
import {
  countTokens,
  extractStructured,
  fetchConfig,
  summarizeStream,
} from "./api";
import { InputPanel } from "./components/InputPanel";
import { OutputPanel } from "./components/OutputPanel";
import { SAMPLE_TEXT } from "./sample";
import type {
  AppConfig,
  StructuredSummary,
  SummaryFormat,
  SummaryLength,
  SummaryStyle,
} from "./types";

export function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [model, setModel] = useState("…");

  const [text, setText] = useState("");
  const [length, setLength] = useState<SummaryLength>("medium");
  const [style, setStyle] = useState<SummaryStyle>("neutral");
  const [format, setFormat] = useState<SummaryFormat>("structured");
  const [focus, setFocus] = useState("");
  const [tokenInfo, setTokenInfo] = useState("");

  const [markdown, setMarkdown] = useState("");
  const [structured, setStructured] = useState<StructuredSummary | null>(null);
  const [status, setStatus] = useState("");
  const [meta, setMeta] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchConfig()
      .then((cfg) => {
        setConfig(cfg);
        setModel(cfg.model);
      })
      .catch(() => setModel("offline"));
  }, []);

  const options = () => ({
    text,
    length,
    style,
    format,
    focus: focus.trim() || undefined,
  });

  const resetOutput = () => {
    setMarkdown("");
    setStructured(null);
    setError(null);
    setMeta("");
  };

  const onCount = async () => {
    if (!text.trim()) return;
    setTokenInfo("counting…");
    try {
      const { inputTokens } = await countTokens(options());
      setTokenInfo(`~${inputTokens.toLocaleString()} input tokens`);
    } catch (e) {
      setTokenInfo(`token count failed: ${(e as Error).message}`);
    }
  };

  const onSummarize = async () => {
    if (!text.trim()) {
      resetOutput();
      setError("Please enter or upload some text first.");
      return;
    }
    setBusy(true);
    resetOutput();
    setStatus("Starting…");

    let acc = "";
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await summarizeStream(
        options(),
        (event) => {
          switch (event.type) {
            case "status":
              setStatus(event.message);
              break;
            case "meta":
              setMeta(
                event.strategy === "map-reduce"
                  ? `map-reduce · ${event.chunks} sections · ~${event.inputTokens.toLocaleString()} input tokens`
                  : `single pass · ~${event.inputTokens.toLocaleString()} input tokens`,
              );
              break;
            case "delta":
              acc += event.text;
              setMarkdown(acc);
              break;
            case "done":
              setStatus("Done.");
              setMeta(
                (m) => `${m} · ${event.outputTokens.toLocaleString()} output tokens`,
              );
              break;
            case "error":
              throw new Error(event.message);
          }
        },
        controller.signal,
      );
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        setStatus("Stopped.");
      } else {
        setError((e as Error).message);
        setStatus("");
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const onExtract = async () => {
    if (!text.trim()) {
      resetOutput();
      setError("Please enter or upload some text first.");
      return;
    }
    setBusy(true);
    resetOutput();
    setStatus("Extracting structured data…");
    try {
      setStructured(await extractStructured(text));
      setStatus("Done.");
    } catch (e) {
      setError((e as Error).message);
      setStatus("");
    } finally {
      setBusy(false);
    }
  };

  const onClear = () => {
    setText("");
    setFocus("");
    setTokenInfo("");
    resetOutput();
    setStatus("");
  };

  return (
    <>
      <header className="topbar">
        <h1>AI Text Summarizer</h1>
        <span className="model-badge">{model}</span>
      </header>

      <main className="layout">
        <InputPanel
          config={config}
          text={text}
          length={length}
          style={style}
          format={format}
          focus={focus}
          tokenInfo={tokenInfo}
          busy={busy}
          onText={(v) => {
            setText(v);
            setTokenInfo("");
          }}
          onLength={setLength}
          onStyle={setStyle}
          onFormat={setFormat}
          onFocus={setFocus}
          onSummarize={onSummarize}
          onExtract={onExtract}
          onCount={onCount}
          onStop={() => abortRef.current?.abort()}
          onClear={onClear}
          onSample={() => setText(SAMPLE_TEXT)}
        />
        <OutputPanel
          status={status}
          meta={meta}
          markdown={markdown}
          structured={structured}
          error={error}
          streaming={busy && !structured}
        />
      </main>
    </>
  );
}
