"""Unit tests for playlist parsing and AES IV handling (no network)."""

import struct

from m3u8_downloader.downloader import (
    _default_iv,
    _parse_attributes,
    is_master_playlist,
    parse_master_playlist,
    parse_media_playlist,
)

MASTER = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS="avc1.4d401e"
360p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2400000,RESOLUTION=1280x720,CODECS="avc1.4d401f"
720p/index.m3u8
"""

MEDIA = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-TARGETDURATION:10
#EXTINF:9.009,
seg0.ts
#EXTINF:9.009,
seg1.ts
#EXT-X-ENDLIST
"""

ENCRYPTED = """#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="key.bin",IV=0x00000000000000000000000000000001
#EXTINF:6.0,
seg0.ts
"""


def test_is_master():
    assert is_master_playlist(MASTER)
    assert not is_master_playlist(MEDIA)


def test_parse_master_sorted_best_first():
    variants = parse_master_playlist(MASTER, "https://host/path/master.m3u8")
    assert len(variants) == 2
    assert variants[0].height == 720
    assert variants[0].url == "https://host/path/720p/index.m3u8"
    assert variants[1].height == 360


def test_parse_media_segments():
    pl = parse_media_playlist(MEDIA, "https://host/path/index.m3u8")
    assert len(pl.segments) == 2
    assert pl.segments[0].url == "https://host/path/seg0.ts"
    assert pl.segments[1].sequence == 1
    assert round(pl.total_duration, 2) == 18.02


def test_parse_encryption_key():
    pl = parse_media_playlist(ENCRYPTED, "https://host/path/index.m3u8")
    seg = pl.segments[0]
    assert seg.key is not None
    assert seg.key.method == "AES-128"
    assert seg.key.uri == "https://host/path/key.bin"
    assert seg.key.iv == bytes.fromhex("00000000000000000000000000000001")


def test_attribute_parsing_with_commas_in_quotes():
    attrs = _parse_attributes('BANDWIDTH=123,CODECS="avc1.4d,mp4a.40",RESOLUTION=1x2')
    assert attrs["BANDWIDTH"] == "123"
    assert attrs["CODECS"] == "avc1.4d,mp4a.40"
    assert attrs["RESOLUTION"] == "1x2"


def test_default_iv():
    assert _default_iv(5) == struct.pack(">QQ", 0, 5)
