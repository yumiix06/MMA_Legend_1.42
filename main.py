#!/usr/bin/env python3
"""MMA Legend launcher.

Keep startup deliberately local: launch the package that lives beside this file.
Older launchers searched sibling MMA_Legend folders, which could silently start the
wrong installed version when several builds existed on the same device.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / "mma_legend"


def _clear_stale_package() -> None:
    """Drop a cached mma_legend package only when it came from another folder."""
    loaded = sys.modules.get("mma_legend")
    origin = getattr(loaded, "__file__", None) if loaded is not None else None
    if not origin:
        return
    try:
        local = Path(origin).resolve().is_relative_to(PACKAGE.resolve())
    except (OSError, ValueError, AttributeError):
        local = False
    if local:
        return
    for key in list(sys.modules):
        if key == "mma_legend" or key.startswith("mma_legend."):
            del sys.modules[key]


def _boot() -> None:
    if not (PACKAGE / "app.py").is_file():
        print("mma_legend/app.py was not found next to main.py")
        print("Keep main.py, START.py and the mma_legend folder together.")
        raise SystemExit(1)
    _clear_stale_package()
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from mma_legend.app import main as game_main
    game_main()


if __name__ == "__main__":
    try:
        _boot()
    except KeyboardInterrupt:
        print("\nGoodbye!")
