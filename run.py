#!/usr/bin/env python3
"""Convenience launcher so you can run the player without installing it.

    python run.py                     # open the player
    python run.py video.mp4           # open and play a file
    python run.py "https://youtu.be/..."  # open and play a URL
"""

from video_player.app import main

if __name__ == "__main__":
    raise SystemExit(main())
