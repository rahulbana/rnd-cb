# PyPlayer

A VLC-powered desktop media player written in Python. It plays virtually any
audio or video format, network streams, and online videos (YouTube and 1000+
other sites via `yt-dlp`) — with a playlist, subtitle and audio-track
selection, playback-speed control, fullscreen, drag-and-drop, and keyboard
shortcuts.

Built with **PySide6** (Qt) for the interface and **libvlc** (via
`python-vlc`) for playback, so format support matches VLC itself.

## Features

- **Plays everything** — MP4, MKV, AVI, MOV, WebM, MP3, FLAC, WAV, and more,
  courtesy of the VLC engine.
- **Online & streaming** — paste a YouTube URL or a direct HTTP/HLS/RTSP
  stream; YouTube and other site URLs are resolved with `yt-dlp`.
- **Playlist** — add files, whole folders, or URLs; reorder, remove, repeat,
  and shuffle; double-click to play.
- **Transport controls** — play/pause, stop, next/previous, click-to-seek
  slider with elapsed/total time, volume with mute.
- **Tracks & subtitles** — switch audio tracks, pick subtitle tracks, or load
  an external subtitle file.
- **Playback speed** — 0.25x up to 2x.
- **Fullscreen** — double-click the video or press `F`; `Esc` to exit.
- **Drag and drop** files or URLs onto the window.

## Requirements

1. **Python 3.9+**
2. **VLC media player** installed on your system (this provides `libvlc`,
   which `python-vlc` binds to). Download it from
   <https://www.videolan.org/vlc/>.
3. Python packages (see `requirements.txt`):
   - `PySide6`
   - `python-vlc`
   - `yt-dlp`

> On 64-bit Windows, install the **64-bit** VLC so it matches 64-bit Python.

## Installation

```bash
# 1. Install VLC itself first (see link above).

# 2. Install the Python dependencies.
pip install -r requirements.txt
```

Or install the package (adds a `pyplayer` command):

```bash
pip install .
```

## Usage

```bash
# Run without installing:
python run.py

# Or as a module:
python -m video_player

# Open a file or URL directly:
python run.py /path/to/movie.mkv
python run.py "https://www.youtube.com/watch?v=..."

# If installed:
pyplayer
```

Then use **Media → Open File(s)… / Open Folder… / Open URL…** to load media,
or just drag files and links onto the window.

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `Space` | Play / Pause |
| `S` | Stop |
| `N` / `P` | Next / Previous track |
| `→` / `←` | Seek +5s / −5s |
| `↑` / `↓` | Volume up / down |
| `M` | Mute |
| `F` | Toggle fullscreen |
| `Esc` | Exit fullscreen |
| `Ctrl+O` | Open file(s) |
| `Ctrl+F` | Open folder |
| `Ctrl+U` | Open URL |
| `Ctrl+L` | Toggle playlist |
| `Ctrl+Q` | Quit |

## Project layout

```
video_player/
├── app.py          # entry point; creates the Qt app, checks for libvlc
├── main_window.py  # main window: menus, shortcuts, wiring
├── player.py       # libvlc wrapper (PlayerEngine) with Qt signals
├── controls.py     # transport control bar (seek/volume/speed)
├── playlist.py     # playlist model + list widget
├── video_frame.py  # black video output surface
├── resolver.py     # yt-dlp URL resolution on a worker thread
└── utils.py        # time formatting, URL/media helpers
```

## How online video works

Direct media links (`.mp4`, `.m3u8`, RTSP, …) are handed straight to libvlc.
Other site URLs (YouTube, Vimeo, etc.) are passed to `yt-dlp`, which runs on a
background thread and returns a playable stream URL that libvlc then plays.

## Troubleshooting

- **"Could not load VLC"** — install the VLC application, and make sure its
  architecture (32/64-bit) matches your Python. Then `pip install python-vlc`.
- **No video, audio only** — some codecs/containers need the full VLC install;
  reinstall the latest VLC.
- **YouTube fails to resolve** — update yt-dlp: `pip install -U yt-dlp`.

## License

MIT
