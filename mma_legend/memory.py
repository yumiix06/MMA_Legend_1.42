"""Persistent promoter/matchmaker memory for career intelligence (v1.30).

Memories live inside ``fighter.story_flags`` so old saves upgrade without a
new Fighter field.  The module is intentionally tiny: systems record concrete
career interactions here, then promoters/managers can use the resulting trust
score rather than relying on one flat rapport number.
"""
from __future__ import annotations

from typing import Any

WEIGHTS = {
    "accepted_offer": 2,
    "declined_offer": -3,
    "late_decline": -6,
    "cancelled_bout": -7,
    "made_weight": 1,
    "missed_weight": -6,
    "professional_negotiation": 0,
    "hard_negotiation": -2,
    "reliable_short_notice": 5,
    "exciting_performance": 4,
    "boring_performance": -1,
    "title_win": 6,
}
MAX_PER_PERSON = 24


def _store(fighter) -> dict:
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}
        flags = fighter.story_flags
    mem = flags.get("people_memory")
    if not isinstance(mem, dict):
        mem = {}
        flags["people_memory"] = mem
    return mem


def remember(fighter, person_id: str, kind: str, detail: Any = "", week: int | None = None) -> dict:
    pid = str(person_id or "unknown")
    row = {
        "week": int(week if week is not None else (getattr(fighter, "week", 0) or 0)),
        "kind": str(kind or "note"),
        "detail": str(detail or "")[:120],
    }
    mem = _store(fighter)
    rows = list(mem.get(pid) or [])
    rows.append(row)
    mem[pid] = rows[-MAX_PER_PERSON:]
    return row


def entries(fighter, person_id: str, kind: str | None = None) -> list[dict]:
    rows = list(_store(fighter).get(str(person_id or "unknown")) or [])
    if kind is not None:
        rows = [r for r in rows if r.get("kind") == kind]
    return rows


def count(fighter, person_id: str, kind: str | None = None) -> int:
    return len(entries(fighter, person_id, kind))


def latest(fighter, person_id: str, kind: str | None = None) -> dict | None:
    rows = entries(fighter, person_id, kind)
    return rows[-1] if rows else None


def score(fighter, person_id: str, recent_weeks: int = 156) -> int:
    """Career-behaviour score, gently recency weighted and capped."""
    now = int(getattr(fighter, "week", 0) or 0)
    total = 0.0
    for row in entries(fighter, person_id):
        age = max(0, now - int(row.get("week", 0) or 0))
        if recent_weeks and age > recent_weeks:
            continue
        weight = float(WEIGHTS.get(str(row.get("kind") or ""), 0))
        decay = max(0.30, 1.0 - age / float(max(1, recent_weeks))) if recent_weeks else 1.0
        total += weight * decay
    return max(-20, min(20, int(round(total))))


def summary(fighter, person_id: str) -> str:
    row = latest(fighter, person_id)
    if not row:
        return "No meaningful history yet."
    kind = str(row.get("kind") or "note").replace("_", " ")
    detail = str(row.get("detail") or "").strip()
    return "%s%s" % (kind, (" · " + detail) if detail else "")
