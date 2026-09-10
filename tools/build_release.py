#!/usr/bin/env python3
"""Build a clean MMA Legend release ZIP from the repository root."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKIP_NAMES = {
    "save.json", "save_a.json", "save_b.json", "save_auto.json",
    "playtest_snapshot.json", "playtest_summary.json", "playtest_trace.jsonl",
    "playtest_trace_prev.jsonl", "MMA_Legend_playtest_bundle.zip",
}
SKIP_PREFIX = ("debug_log",)
SKIP_DIR = {"__pycache__", ".git", ".pytest_cache", "imagine_images"}
SKIP_SUFFIX = {".pyc", ".pyo"}


def keep(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if set(rel.parts) & SKIP_DIR:
        return False
    if path.name in SKIP_NAMES or path.name.startswith("playtest_"):
        return False
    if path.name.startswith(SKIP_PREFIX) or path.suffix in SKIP_SUFFIX:
        return False
    return True


def main() -> Path:
    from mma_legend import constants as C

    out = ROOT.parent / f"MMA_Legend_{C.GAME_VERSION}.zip"
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and keep(p))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"wrote {out} ({len(files)} files)")
    return out


if __name__ == "__main__":
    main()
