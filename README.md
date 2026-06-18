# rnd-cb

RND CB

## m3u8 video downloader

A small, dependency-light "agent" that downloads HLS (`.m3u8`) videos from a
URL. It handles master playlists (picks the best quality, or one you choose),
parallel segment downloads with retries, AES-128 encrypted streams, and
optional remuxing to `.mp4` via `ffmpeg`.

Plain (unencrypted) streams use only the Python standard library. Encrypted
streams additionally need a crypto backend (`cryptography` or `pycryptodome`).

### Install

```bash
pip install -e .
# optional, only needed for AES-128 encrypted streams:
pip install -e ".[crypto]"   # or: pip install pycryptodome
```

This exposes a `m3u8-dl` command. You can also run it without installing:

```bash
python -m m3u8_downloader ...
```

### Usage

Download the best quality to `video.mp4` (remuxes with ffmpeg if available):

```bash
m3u8-dl download "https://example.com/stream/master.m3u8" -o video.mp4
```

List the quality variants in a master playlist:

```bash
m3u8-dl list "https://example.com/stream/master.m3u8"
```

Pick a specific resolution, raw `.ts` output, more parallelism, and custom
headers (useful when a site requires a `Referer` or `Cookie`):

```bash
m3u8-dl download "https://example.com/master.m3u8" \
    -o clip.ts \
    --height 720 \
    --concurrency 16 \
    --referer "https://example.com/" \
    -H "Cookie: session=abc123"
```

### Options (`download`)

| Option | Description |
| --- | --- |
| `-o, --output` | Output file. A `.mp4` extension triggers an ffmpeg remux; otherwise a raw `.ts` is written. Default: `video.mp4`. |
| `--height N` | Preferred max vertical resolution (e.g. `720`). Default: best available. |
| `-c, --concurrency N` | Parallel segment downloads. Default: 8. |
| `--retries N` | Retries per segment. Default: 3. |
| `--timeout N` | Per-request timeout (seconds). Default: 30. |
| `--referer URL` | Convenience shortcut for a `Referer` header. |
| `-H, --header "Name: value"` | Extra HTTP header (repeatable). |
| `-k, --insecure` | Skip TLS certificate verification (only for hosts you trust). |
| `-q, --quiet` | Suppress the progress bar. |

### Troubleshooting

**`SSL: CERTIFICATE_VERIFY_FAILED ... unable to get local issuer certificate`**

Your Python can't find a CA bundle to validate the server's certificate. Options:

- `pip install certifi` — the downloader picks this up automatically.
- Re-run with `-k/--insecure` to skip verification (only for hosts you trust):

  ```bash
  m3u8-dl download "https://example.com/master.m3u8" -o video.mp4 --insecure
  ```

### Use as a library

```python
from m3u8_downloader.downloader import M3U8Downloader

dl = M3U8Downloader(concurrency=16)
result = dl.download("https://example.com/master.m3u8", "out.ts", prefer_height=720)
print(result.segments, "segments,", round(result.duration), "seconds")
```

### Notes

- `.mp4` output requires [`ffmpeg`](https://ffmpeg.org/) on your `PATH`. Without
  it, the raw `.ts` is kept (it's still directly playable in most players).
- Only download streams you have the rights to. This tool is for personal,
  authorized use.

### Tests

```bash
python -m pytest tests/
```
