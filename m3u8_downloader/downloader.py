"""Core HLS (.m3u8) download logic.

The downloader understands the subset of the HLS spec that matters for
grabbing a VOD stream:

* master playlists  -> pick a variant (best quality by default)
* media playlists   -> list of segments + optional AES-128 encryption
* AES-128 segments  -> decrypted on the fly before being written

Everything here uses only the standard library, except for AES decryption
which falls back across ``cryptography`` / ``pycryptodome`` if a stream is
encrypted. Plain (unencrypted) streams need no third-party packages.
"""

from __future__ import annotations

import os
import ssl
import struct
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def make_ssl_context(verify: bool = True) -> ssl.SSLContext:
    """Build an SSL context.

    When ``verify`` is True we try to load certificates from ``certifi`` (if
    installed) before falling back to the system trust store — this fixes the
    common "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate"
    error on machines with an incomplete cert store. When ``verify`` is False
    certificate checks are disabled entirely (use only for hosts you trust).
    """
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 - certifi optional; fall back to system store
        return ssl.create_default_context()


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def http_get(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 30,
    ssl_context: Optional[ssl.SSLContext] = None,
) -> bytes:
    """Fetch a URL and return the raw body bytes."""
    req = urllib.request.Request(url, headers={**DEFAULT_HEADERS, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
        return resp.read()


def http_get_text(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 30,
    ssl_context: Optional[ssl.SSLContext] = None,
) -> str:
    return http_get(url, headers, timeout, ssl_context).decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# Playlist model + parsing
# --------------------------------------------------------------------------- #
@dataclass
class Variant:
    """A single quality entry from a master playlist."""

    url: str
    bandwidth: int = 0
    resolution: Optional[str] = None
    codecs: Optional[str] = None

    @property
    def height(self) -> int:
        if self.resolution and "x" in self.resolution:
            try:
                return int(self.resolution.split("x")[1])
            except ValueError:
                return 0
        return 0

    def __str__(self) -> str:
        res = self.resolution or "?"
        return f"{res} @ {self.bandwidth // 1000} kbps"


@dataclass
class EncryptionKey:
    method: str
    uri: Optional[str] = None
    iv: Optional[bytes] = None


@dataclass
class Segment:
    url: str
    duration: float = 0.0
    key: Optional[EncryptionKey] = None
    sequence: int = 0


@dataclass
class MediaPlaylist:
    segments: list = field(default_factory=list)
    total_duration: float = 0.0


def _absolute(base_url: str, ref: str) -> str:
    return urllib.parse.urljoin(base_url, ref.strip())


def _parse_attributes(line: str) -> dict:
    """Parse a comma-separated ``KEY=VALUE`` attribute list (HLS style)."""
    attrs: dict = {}
    field_chars: list = []
    in_quotes = False
    parts: list = []
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            field_chars.append(ch)
        elif ch == "," and not in_quotes:
            parts.append("".join(field_chars))
            field_chars = []
        else:
            field_chars.append(ch)
    if field_chars:
        parts.append("".join(field_chars))

    for part in parts:
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        attrs[key.strip().upper()] = value.strip().strip('"')
    return attrs


def is_master_playlist(text: str) -> bool:
    return "#EXT-X-STREAM-INF" in text


def parse_master_playlist(text: str, base_url: str) -> list:
    """Return the list of :class:`Variant` entries in a master playlist."""
    variants: list = []
    pending: Optional[dict] = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-STREAM-INF:"):
            pending = _parse_attributes(line.split(":", 1)[1])
        elif not line.startswith("#") and pending is not None:
            variants.append(
                Variant(
                    url=_absolute(base_url, line),
                    bandwidth=int(pending.get("BANDWIDTH", 0) or 0),
                    resolution=pending.get("RESOLUTION"),
                    codecs=pending.get("CODECS"),
                )
            )
            pending = None
    variants.sort(key=lambda v: (v.height, v.bandwidth), reverse=True)
    return variants


def parse_media_playlist(text: str, base_url: str) -> MediaPlaylist:
    """Parse a media playlist into an ordered list of segments."""
    playlist = MediaPlaylist()
    current_key: Optional[EncryptionKey] = None
    next_duration = 0.0
    sequence = 0

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            sequence = int(line.split(":", 1)[1].strip() or 0)
        elif line.startswith("#EXT-X-KEY:"):
            attrs = _parse_attributes(line.split(":", 1)[1])
            method = attrs.get("METHOD", "NONE")
            if method == "NONE":
                current_key = None
            else:
                iv_hex = attrs.get("IV")
                iv = None
                if iv_hex:
                    iv_hex = iv_hex.lower().removeprefix("0x")
                    iv = bytes.fromhex(iv_hex.rjust(32, "0"))
                uri = attrs.get("URI")
                current_key = EncryptionKey(
                    method=method,
                    uri=_absolute(base_url, uri) if uri else None,
                    iv=iv,
                )
        elif line.startswith("#EXTINF:"):
            value = line.split(":", 1)[1].split(",", 1)[0]
            try:
                next_duration = float(value)
            except ValueError:
                next_duration = 0.0
        elif not line.startswith("#"):
            playlist.segments.append(
                Segment(
                    url=_absolute(base_url, line),
                    duration=next_duration,
                    key=current_key,
                    sequence=sequence,
                )
            )
            playlist.total_duration += next_duration
            next_duration = 0.0
            sequence += 1

    return playlist


# --------------------------------------------------------------------------- #
# AES-128 decryption
# --------------------------------------------------------------------------- #
def _aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt AES-128-CBC using whichever crypto backend is installed.

    Backends are tried in order. A broken install (e.g. ``cryptography``
    missing its native ``_cffi_backend``) can raise things other than
    ``ImportError`` at import time, so each attempt is guarded broadly and
    we simply move on to the next backend.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import (
            Cipher,
            algorithms,
            modes,
        )

        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        return decryptor.update(data) + decryptor.finalize()
    except BaseException:  # noqa: BLE001 - incl. pyo3 PanicException on broken installs
        pass

    try:
        from Crypto.Cipher import AES  # pycryptodome

        return AES.new(key, AES.MODE_CBC, iv).decrypt(data)
    except Exception as exc:  # noqa: BLE001 - depends on environment
        raise RuntimeError(
            "This stream is AES-128 encrypted but no working crypto backend "
            "was found. Install one of:\n"
            "    pip install cryptography\n"
            "  (or)\n"
            "    pip install pycryptodome"
        ) from exc


def _default_iv(sequence: int) -> bytes:
    """HLS default IV = the segment media sequence as a 128-bit big-endian int."""
    return struct.pack(">QQ", 0, sequence)


# --------------------------------------------------------------------------- #
# Downloader
# --------------------------------------------------------------------------- #
@dataclass
class DownloadResult:
    output_path: str
    segments: int
    duration: float


class M3U8Downloader:
    def __init__(
        self,
        headers: Optional[dict] = None,
        concurrency: int = 8,
        max_retries: int = 3,
        timeout: int = 30,
        progress: Optional[Callable[[int, int], None]] = None,
        verify_ssl: bool = True,
    ) -> None:
        self.headers = headers or {}
        self.concurrency = max(1, concurrency)
        self.max_retries = max(1, max_retries)
        self.timeout = timeout
        self.progress = progress
        self.ssl_context = make_ssl_context(verify_ssl)
        self._key_cache: dict = {}

    # -- public API ------------------------------------------------------- #
    def resolve_media_playlist(
        self, url: str, prefer_height: Optional[int] = None
    ) -> tuple:
        """Follow a master playlist (if any) and return (media_playlist, url)."""
        text = http_get_text(url, self.headers, self.timeout, self.ssl_context)
        if is_master_playlist(text):
            variants = parse_master_playlist(text, url)
            if not variants:
                raise RuntimeError("Master playlist contained no variants.")
            variant = self._pick_variant(variants, prefer_height)
            url = variant.url
            text = http_get_text(url, self.headers, self.timeout, self.ssl_context)
        return parse_media_playlist(text, url), url

    def download(
        self,
        url: str,
        output_path: str,
        prefer_height: Optional[int] = None,
    ) -> DownloadResult:
        playlist, _ = self.resolve_media_playlist(url, prefer_height)
        if not playlist.segments:
            raise RuntimeError("No media segments found in playlist.")

        total = len(playlist.segments)
        tmp_dir = tempfile.mkdtemp(prefix="m3u8_")
        parts: dict = {}
        completed = 0

        try:
            with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
                futures = {
                    pool.submit(self._fetch_segment, seg, idx, tmp_dir): idx
                    for idx, seg in enumerate(playlist.segments)
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    parts[idx] = future.result()
                    completed += 1
                    if self.progress:
                        self.progress(completed, total)

            os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
            with open(output_path, "wb") as out:
                for idx in range(total):
                    with open(parts[idx], "rb") as part:
                        out.write(part.read())
        finally:
            for path in parts.values():
                try:
                    os.remove(path)
                except OSError:
                    pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

        return DownloadResult(
            output_path=output_path,
            segments=total,
            duration=playlist.total_duration,
        )

    # -- internals -------------------------------------------------------- #
    def _pick_variant(self, variants: list, prefer_height: Optional[int]):
        if prefer_height is None:
            return variants[0]  # already sorted best-first
        # closest variant whose height is <= requested, else the smallest
        eligible = [v for v in variants if v.height and v.height <= prefer_height]
        if eligible:
            return max(eligible, key=lambda v: (v.height, v.bandwidth))
        return min(variants, key=lambda v: (v.height or 1 << 30, v.bandwidth))

    def _get_key(self, uri: str) -> bytes:
        if uri not in self._key_cache:
            self._key_cache[uri] = http_get(
                uri, self.headers, self.timeout, self.ssl_context
            )
        return self._key_cache[uri]

    def _fetch_segment(self, segment: Segment, idx: int, tmp_dir: str) -> str:
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                data = http_get(
                    segment.url, self.headers, self.timeout, self.ssl_context
                )
                if segment.key and segment.key.method == "AES-128" and segment.key.uri:
                    key = self._get_key(segment.key.uri)
                    iv = segment.key.iv or _default_iv(segment.sequence)
                    data = _aes_cbc_decrypt(data, key, iv)
                path = os.path.join(tmp_dir, f"seg_{idx:06d}.ts")
                with open(path, "wb") as fh:
                    fh.write(data)
                return path
            except Exception as exc:  # noqa: BLE001 - retried below
                last_err = exc
        raise RuntimeError(
            f"Failed to download segment {idx} ({segment.url}): {last_err}"
        )
