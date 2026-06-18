"""Command-line interface for the m3u8 downloader agent."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import Optional

from .downloader import (
    DEFAULT_HEADERS,
    M3U8Downloader,
    http_get_text,
    is_master_playlist,
    make_ssl_context,
    parse_master_playlist,
)


def _print_progress(done: int, total: int) -> None:
    width = 30
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "-" * (width - filled)
    pct = (done / total * 100) if total else 100.0
    sys.stderr.write(f"\r[{bar}] {done}/{total} ({pct:5.1f}%)")
    sys.stderr.flush()
    if done >= total:
        sys.stderr.write("\n")


def _parse_headers(items: Optional[list]) -> dict:
    headers: dict = {}
    for item in items or []:
        if ":" not in item:
            raise SystemExit(f"Invalid --header (expected 'Name: value'): {item!r}")
        name, _, value = item.partition(":")
        headers[name.strip()] = value.strip()
    return headers


def _remux_to_mp4(ts_path: str, mp4_path: str) -> bool:
    """Losslessly remux a .ts file to .mp4 using ffmpeg (no re-encode)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", ts_path,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        mp4_path,
    ]
    return subprocess.run(cmd).returncode == 0


def cmd_list(args: argparse.Namespace) -> int:
    ctx = make_ssl_context(verify=not args.insecure)
    text = http_get_text(args.url, _parse_headers(args.header), ssl_context=ctx)
    if not is_master_playlist(text):
        print("This URL is a media playlist (single quality), not a master playlist.")
        return 0
    variants = parse_master_playlist(text, args.url)
    print(f"Found {len(variants)} variant(s):\n")
    for i, v in enumerate(variants):
        print(f"  [{i}] {v}  codecs={v.codecs or '?'}")
        print(f"      {v.url}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    headers = _parse_headers(args.header)
    if args.referer:
        headers.setdefault("Referer", args.referer)

    downloader = M3U8Downloader(
        headers=headers,
        concurrency=args.concurrency,
        max_retries=args.retries,
        timeout=args.timeout,
        progress=None if args.quiet else _print_progress,
        verify_ssl=not args.insecure,
        inherit_query=not args.no_inherit_query,
    )

    output = args.output
    want_mp4 = output.lower().endswith(".mp4")
    ts_target = output[:-4] + ".ts" if want_mp4 else output

    start = time.time()
    if not args.quiet:
        print(f"Resolving playlist: {args.url}", file=sys.stderr)
    result = downloader.download(args.url, ts_target, prefer_height=args.height)
    elapsed = time.time() - start

    if not args.quiet:
        print(
            f"Downloaded {result.segments} segments "
            f"(~{result.duration:.0f}s of video) in {elapsed:.1f}s",
            file=sys.stderr,
        )

    if want_mp4:
        if _remux_to_mp4(ts_target, output):
            os.remove(ts_target)
            if not args.quiet:
                print(f"Remuxed to {output}", file=sys.stderr)
        else:
            print(
                f"ffmpeg not found or remux failed; kept raw stream at {ts_target}\n"
                "Install ffmpeg to get a clean .mp4, or play the .ts directly.",
                file=sys.stderr,
            )
            print(ts_target)
            return 0

    print(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m3u8-dl",
        description="Download HLS (.m3u8) videos from a URL.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-H", "--header", action="append",
        help="Extra HTTP header 'Name: value' (repeatable).",
    )
    common.add_argument(
        "-k", "--insecure", action="store_true",
        help="Skip TLS certificate verification (use only for hosts you trust).",
    )

    p_dl = sub.add_parser("download", parents=[common], help="Download a stream.")
    p_dl.add_argument("url", help="The .m3u8 URL (master or media playlist).")
    p_dl.add_argument(
        "-o", "--output", default="video.mp4",
        help="Output file. Use a .mp4 extension to remux via ffmpeg "
             "(default: video.mp4).",
    )
    p_dl.add_argument(
        "--height", type=int, default=None,
        help="Preferred max vertical resolution, e.g. 720. Default: best.",
    )
    p_dl.add_argument("-c", "--concurrency", type=int, default=8,
                      help="Parallel segment downloads (default: 8).")
    p_dl.add_argument("--retries", type=int, default=3,
                      help="Retries per segment (default: 3).")
    p_dl.add_argument("--timeout", type=int, default=30,
                      help="Per-request timeout in seconds (default: 30).")
    p_dl.add_argument("--referer", default=None, help="Shortcut for a Referer header.")
    p_dl.add_argument(
        "--no-inherit-query", action="store_true",
        help="Do not copy the playlist's query string (signed token) onto "
             "segment/key URLs that lack one. On by default.",
    )
    p_dl.add_argument("-q", "--quiet", action="store_true", help="Suppress progress.")
    p_dl.set_defaults(func=cmd_download)

    p_ls = sub.add_parser("list", parents=[common],
                          help="List quality variants in a master playlist.")
    p_ls.add_argument("url", help="The master .m3u8 URL.")
    p_ls.set_defaults(func=cmd_list)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - top-level friendly error
        print(f"Error: {exc}", file=sys.stderr)
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            print(
                "\nTLS certificate verification failed. Try one of:\n"
                "  * pip install certifi   (adds an up-to-date CA bundle)\n"
                "  * re-run with -k/--insecure to skip verification "
                "(only for hosts you trust)",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
