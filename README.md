# Podcastify — Article/Blog → 2-Person Audio Podcast

A small **multi-agent** pipeline that turns any article or blog post into a
natural, two-person audio podcast.

- **LLM "thinking" agents** sit behind a swappable `LLMProvider` interface;
  **OpenAI** is the default implementation.
- **Text-to-speech** uses a **free, open-source** model — **Kokoro** by default
  (Apache-2.0, runs locally), with **Piper** (MIT, fully offline) as an option.

```
 URL / text ─▶ Extractor ─▶ Script Writer ─▶ Editor ─▶ Voice/Audio ─▶ podcast.wav
                (OpenAI)       (OpenAI)       (OpenAI)   (Kokoro/Piper)
```

## The agents

| Agent | Powered by | Job |
|-------|-----------|-----|
| **ExtractorAgent**   | trafilatura + OpenAI | Download a URL (or take raw text), strip boilerplate, produce a clean titled `Article`. |
| **ScriptWriterAgent**| OpenAI | Turn the article into a lively **host + co-host** dialogue covering all key points. |
| **EditorAgent**      | OpenAI | Polish flow, fix hand-offs, expand symbols/abbreviations so TTS reads them correctly. |
| **VoiceAgent**       | Kokoro / Piper (open source) | Give each of the 2 speakers a distinct voice and stitch the lines into one audio file. |

A `PodcastPipeline` orchestrator wires them together; data passes between
agents as typed Pydantic models (`Article` → `PodcastScript` → audio).

## Install

```bash
pip install -r requirements.txt
# ffmpeg is needed only for .mp3 output (apt install ffmpeg / brew install ffmpeg)
```

Set your OpenAI key:

```bash
cp .env.example .env      # then edit it, or just:
export OPENAI_API_KEY=sk-...
```

## Usage

```bash
# From a URL (~6 min episode), default Kokoro voices
python main.py --url https://example.com/some-blog-post --minutes 6

# From a local article file, custom host names + output
python main.py --file examples/sample_article.txt \
    --host Maya --cohost Leo --out output/episode.wav

# Script + transcript only (no TTS dependencies required)
python main.py --file examples/sample_article.txt --no-audio -v
```

Outputs:
- `output/podcast.wav` — the audio podcast (use `.mp3` for compressed output).
- `output/podcast.transcript.md` — the readable transcript.

### Use it as a library

```python
from podcastify import PodcastPipeline, PipelineConfig, Speaker

config = PipelineConfig(
    llm_provider="openai",                # swappable; see below
    llm_model="gpt-4o",
    target_minutes=6,
    tts_backend="kokoro",                 # or "piper"
    speakers=[
        Speaker(name="Maya", role="host",   voice="af_heart"),
        Speaker(name="Leo",  role="cohost", voice="am_michael"),
    ],
)
result = PodcastPipeline(config).run(
    url="https://example.com/post",
    out_path="output/episode.wav",
)
print(result.audio_path, result.transcript_path)
```

## Swapping the LLM provider

The agents depend only on the `LLMProvider` interface
(`podcastify/llm/base.py`), so any vendor can be plugged in without touching
agent code. Implement two methods and register it:

```python
from podcastify import LLMProvider, register_provider, PodcastPipeline, PipelineConfig

class MyProvider(LLMProvider):
    name = "myllm"
    def __init__(self, model=None, api_key=None, **kw):
        self.model = model or "my-model"
        # ... init your SDK client ...
    def complete(self, messages, temperature=0.7) -> str:
        ...
    def complete_structured(self, messages, schema, temperature=0.7):
        ...  # return an instance of `schema` (a Pydantic model)

register_provider("myllm", lambda model=None, api_key=None, **kw: MyProvider(model, api_key, **kw))

PodcastPipeline(PipelineConfig(llm_provider="myllm", llm_model="my-model")).run(...)
```

You can also inject a provider instance directly (handy for tests):
`PodcastPipeline(config, provider=MyProvider())`. From the CLI, choose the
built-in vendor with `--provider` / `--model`.

## TTS backends (free / open source)

### Kokoro (default)
- Apache-2.0, open weights, natural multi-voice English. `pip install kokoro soundfile`
- Voice ids: `af_heart`, `af_bella`, `am_michael`, `am_adam`, `bf_emma`,
  `bm_george`. Set per speaker via `Speaker.voice` or `--host-voice/--cohost-voice`.

### Piper (offline option)
- MIT, fully local. `pip install piper-tts`
- Download `.onnx` voices from
  [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) and set
  each `Speaker.voice` to a model path. Run with `--tts piper`.

## How distinct voices are assigned

Each of the two `Speaker`s gets its own backend voice. If you don't specify
one, the host and co-host fall back to the backend's two default voices
(female/male for Kokoro), so the two people always sound different.

## Project layout

```
main.py                     CLI entrypoint
podcastify/
  models.py                 Article, PodcastScript, Speaker, DialogueLine
  pipeline.py               PodcastPipeline orchestrator + PipelineConfig
  llm/
    base.py                 LLMProvider interface (vendor-neutral)
    openai_provider.py      OpenAI implementation (default)
    factory.py              get_llm_provider() + register_provider()
  agents/
    base.py                 LLMAgent (uses an LLMProvider, structured outputs)
    extractor.py            ExtractorAgent
    scriptwriter.py         ScriptWriterAgent
    editor.py               EditorAgent
    voice.py                VoiceAgent (renders script -> audio)
  tts/
    base.py                 TTSBackend interface
    kokoro_backend.py       Kokoro (default)
    piper_backend.py        Piper (offline)
    factory.py              get_tts_backend()
examples/sample_article.txt Sample input
```

## Notes
- OpenAI is the default LLM provider; swap the vendor with `--provider` (after
  registering it) or the model with `--model`.
- `--no-audio` lets you generate and review the script without installing any
  TTS dependencies.
