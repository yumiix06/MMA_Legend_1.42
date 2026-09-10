#!/usr/bin/env python3
"""Phone-friendly entry point. Tap this file to launch MMA Legend."""
from __future__ import annotations

import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
runpy.run_path(str(HERE / "main.py"), run_name="__main__")
