# cribasagent 🗞️📚

A small, modular, standalone **daily current-affairs agent** built for
**UPSC** (and other general-knowledge exam) aspirants.

Every morning it:

1. **Reads** the last 24 hours of news from major **Indian English-language**
   newspapers and official wires (The Hindu, Indian Express, Times of India,
   Hindustan Times, LiveMint, PIB, Down To Earth) via their RSS feeds.
2. **Filters & summarises** the news with an **OpenAI LLM**, keeping *only*
   what matters for the exam — polity, economy, international relations,
   environment, science & tech, schemes, reports/indices and prelims facts —
   and discarding sports, gossip, crime and noise.
3. **Writes** a clean, dated **Markdown brief** grouped by GS subject.

## How it works

```
RSS feeds ─▶ fetcher ─▶ articles ─▶ summarizer (map-reduce, OpenAI) ─▶ Brief ─▶ writer ─▶ Markdown
```

Each stage lives in its own module so it's easy to extend or test:

| Module | Responsibility |
| --- | --- |
| `sources.py` | The list of RSS feeds (edit to taste). |
| `config.py` | All tunables; overridable via env vars. |
| `models.py` | `Article` / `Brief` data classes. |
| `fetcher.py` | Concurrent RSS fetch + 24h filter + de-dup. |
| `summarizer.py` | OpenAI map-reduce → exam-ready bullets by subject. |
| `writer.py` | Render & save the Markdown document. |
| `agent.py` | Orchestrates the pipeline. |
| `scheduler.py` | Runs it daily at 10:00. |
| `cli.py` | `run` / `schedule` commands. |

## Setup

```bash
cd cribasagent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e .
cp .env.example .env                      # then add your OPENAI_API_KEY
```

## Usage

Run once now (writes today's brief into `output/`):

```bash
python -m cribasagent run
```

Run every day at 10:00 (keeps the process alive):

```bash
python -m cribasagent schedule
```

Handy overrides:

```bash
python -m cribasagent run --model gpt-4o --lookback-hours 36 -v
```

Prefer the OS scheduler? Drop the daemon and add a cron line instead:

```cron
0 10 * * *  cd /path/to/cribasagent && /path/to/.venv/bin/python -m cribasagent run
```

## Configuration

Everything is configurable through environment variables (see `.env.example`):
`OPENAI_API_KEY`, `CRIBAS_MODEL`, `CRIBAS_LOOKBACK_HOURS`, `CRIBAS_MAX_ARTICLES`,
`CRIBAS_BATCH_SIZE`, `CRIBAS_OUTPUT_DIR`, `CRIBAS_RUN_AT`, and more.

## Troubleshooting

**"0 articles in window" / no articles found.** The fetcher now logs the real
HTTP status per feed. If you see `HTTP 403`, the site blocked the request —
cribasagent already sends a browser User-Agent, but some networks/sites are
stricter; try again, switch network, or prune that source in `sources.py`.
Run with `-v` for full detail:

```bash
python -m cribasagent run -v
```

**`SSL: CERTIFICATE_VERIFY_FAILED` / `unable to get local issuer certificate`.**
Your Python has no CA bundle (common on fresh macOS installs). Just install the
dependencies — cribasagent verifies against `certifi`'s bundle:

```bash
pip install -r requirements.txt        # installs certifi
# macOS python.org build: also run Applications/Python 3.x/Install Certificates.command
```

If instead you see `self-signed certificate in certificate chain`, a corporate
proxy/antivirus is intercepting TLS. Either install your organisation's root CA,
or, as a last resort, disable verification (drops authenticity checks):

```bash
CRIBAS_INSECURE_SSL=1 python -m cribasagent run
```

**`python-dotenv could not parse statement starting at line N`.** A line in your
`.env` isn't valid `KEY=value`. Check that line — keys need no spaces around
`=`, and values with `#` or spaces should be quoted. It's only a warning, but
if the bad line *is* your `OPENAI_API_KEY` the run will fail to authenticate.

## Output

A file like `output/upsc-current-affairs-2026-06-16.md`, with sections such as
**Polity & Governance**, **Economy**, **International Relations**,
**Environment & Ecology**, **Science & Technology**, **Government Schemes** and
**Prelims Facts** — each a list of crisp, revisable bullet points.
