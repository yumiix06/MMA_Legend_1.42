"""Bounded playtest telemetry for reproducing what the player actually saw.

This is deliberately observational.  It never changes RNG, balance or game
state.  Two outputs are kept:

* an in-memory tail embedded into every save under top-level ``playtest``;
* ``playtest_trace.jsonl`` beside the game, rotated at a small size so a crash
  can still be diagnosed even when no save completed.

The UI records rendered lines + prompts + answers.  Combat may additionally
record structured action snapshots.  The save bundle therefore tells a future
developer not only *what state survived*, but how the player got there.
"""
from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path
import re
import time

TRACE_PATH = Path.cwd() / "playtest_trace.jsonl"
_MAX_BYTES = 4_000_000
_UI = deque(maxlen=260)
_DECISIONS = deque(maxlen=160)
_COMBAT = deque(maxlen=520)
_SYSTEM = deque(maxlen=120)
_SEQ = 0
_SCREEN = ""
_SUBTITLE = ""
_FIGHT_ID = ""

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text) -> str:
    return _ANSI_RE.sub("", str(text or ""))


def _rotate() -> None:
    try:
        if TRACE_PATH.exists() and TRACE_PATH.stat().st_size > _MAX_BYTES:
            old = TRACE_PATH.with_suffix(".previous.jsonl")
            try:
                if old.exists():
                    old.unlink()
                TRACE_PATH.replace(old)
            except OSError:
                TRACE_PATH.write_text("", encoding="utf-8")
    except OSError:
        pass


def _entry(kind: str, **data) -> dict:
    global _SEQ
    _SEQ += 1
    e = {
        "seq": _SEQ,
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": kind,
    }
    if _SCREEN:
        e["screen"] = _SCREEN
    if _SUBTITLE:
        e["subtitle"] = _SUBTITLE
    if _FIGHT_ID:
        e["fight_id"] = _FIGHT_ID
    for k, v in data.items():
        if v is not None:
            e[k] = v
    return e


def _write(e: dict) -> None:
    try:
        _rotate()
        with TRACE_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
    except (OSError, TypeError, ValueError):
        pass


def set_screen(title: str = "", subtitle: str = "") -> None:
    global _SCREEN, _SUBTITLE
    _SCREEN, _SUBTITLE = _plain(title).strip(), _plain(subtitle).strip()
    e = _entry("screen", title=_SCREEN, subtitle=_SUBTITLE)
    _SYSTEM.append(e); _write(e)


def ui_output(text: str) -> None:
    e = _entry("ui", text=_plain(text))
    _UI.append(e); _write(e)


def prompt(text: str) -> None:
    e = _entry("prompt", text=_plain(text))
    _UI.append(e); _write(e)


def answer(value: str) -> None:
    e = _entry("input", value=str(value))
    _DECISIONS.append(e); _write(e)


def decision(name: str, choice=None, options=None, reason=None, **meta) -> None:
    # Headless balance labs call the combat AI thousands of times.  Those are
    # not human playtests and must not turn a test run into megabytes of disk
    # I/O.  AI fight choices are captured only while begin_fight() has opened
    # a real player-facing fight trace.
    if name == "ai_pick" and not _FIGHT_ID:
        return
    e = _entry("decision", name=name, choice=choice, options=options, reason=reason, **meta)
    _DECISIONS.append(e); _write(e)


def system(name: str, **meta) -> None:
    e = _entry("system", name=name, **meta)
    _SYSTEM.append(e); _write(e)


def begin_fight(fighter, opponent, *, org="", rules="mma", rounds=3, gameplan="") -> str:
    global _FIGHT_ID
    week = int(getattr(fighter, "week", 0) or 0)
    fid = getattr(opponent, "fid", None) or getattr(opponent, "name", "opp")
    _FIGHT_ID = "w%s:%s:%s" % (week, getattr(fighter, "fid", "PLAYER") or "PLAYER", fid)
    system("fight_begin", fighter=getattr(fighter, "name", ""), opponent=getattr(opponent, "name", ""),
           opponent_id=getattr(opponent, "fid", None), org=org, rules=rules, rounds=rounds,
           gameplan=gameplan, player_record=list(getattr(fighter, "pro_record", []) or []),
           opponent_record=list(getattr(opponent, "pro_record", []) or []))
    return _FIGHT_ID


def combat(**meta) -> None:
    if not _FIGHT_ID:
        return
    e = _entry("combat", **meta)
    _COMBAT.append(e); _write(e)


def end_fight(**meta) -> None:
    global _FIGHT_ID
    e = _entry("fight_end", **meta)
    _COMBAT.append(e); _write(e)
    _FIGHT_ID = ""


def save_marker(path, fighter=None, pool=None, phase="") -> None:
    system("save", path=str(path), phase=phase,
           week=int(getattr(fighter, "week", 0) or 0) if fighter is not None else None,
           world_pool=len(getattr(pool, "fighters", []) or []) if pool is not None else None)


def snapshot(fighter=None, pool=None, *, saved_pool_n=None, path="", phase="") -> dict:
    """Small JSON-safe payload embedded in a save.

    The buffers are bounded so this remains useful on phones.  ``ui_tail`` is
    intentionally the *rendered* text, not reconstructed state.
    """
    flags = getattr(fighter, "story_flags", None) or {} if fighter is not None else {}
    return {
        "format": 1,
        "path": str(path or ""),
        "phase": phase,
        "screen": _SCREEN,
        "subtitle": _SUBTITLE,
        "week": int(getattr(fighter, "week", 0) or 0) if fighter is not None else 0,
        "world_pool_n": len(getattr(pool, "fighters", []) or []) if pool is not None else None,
        "saved_pool_n": saved_pool_n,
        "booked_fight": bool(getattr(fighter, "booked_fight", None)) if fighter is not None else False,
        "org_rank": flags.get("org_rank") if isinstance(flags, dict) else None,
        "last_note": getattr(fighter, "last_week_note", "") if fighter is not None else "",
        "ui_tail": list(_UI),
        "decisions": list(_DECISIONS),
        "combat_tail": list(_COMBAT),
        "system_tail": list(_SYSTEM),
    }


def reset_runtime() -> None:
    """Tests/new careers can clear in-memory tails without touching old files."""
    global _SEQ, _SCREEN, _SUBTITLE, _FIGHT_ID
    _UI.clear(); _DECISIONS.clear(); _COMBAT.clear(); _SYSTEM.clear()
    _SEQ = 0; _SCREEN = ""; _SUBTITLE = ""; _FIGHT_ID = ""


def restore(blob: dict | None) -> None:
    """Carry a save's recent trace into the next session after loading."""
    if not isinstance(blob, dict):
        return
    try:
        for e in list(blob.get("ui_tail") or [])[-_UI.maxlen:]:
            if isinstance(e, dict): _UI.append(e)
        for e in list(blob.get("decisions") or [])[-_DECISIONS.maxlen:]:
            if isinstance(e, dict): _DECISIONS.append(e)
        for e in list(blob.get("combat_tail") or [])[-_COMBAT.maxlen:]:
            if isinstance(e, dict): _COMBAT.append(e)
        for e in list(blob.get("system_tail") or [])[-_SYSTEM.maxlen:]:
            if isinstance(e, dict): _SYSTEM.append(e)
    except Exception:
        pass
