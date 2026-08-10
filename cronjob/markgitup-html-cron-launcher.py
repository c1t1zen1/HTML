#!/usr/bin/env python3
"""Cron-safe launcher for the repository-canonical Markgitup publisher."""

from pathlib import Path
import runpy

CANONICAL = Path("/home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py")
runpy.run_path(str(CANONICAL), run_name="__main__")
