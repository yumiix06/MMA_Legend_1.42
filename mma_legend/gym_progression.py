"""Persistent specialist-gym development (v1.41).

A specialist membership is a relationship with a room, not a button that only
matters on the week the player opens its menu.  While the fighter is home and
healthy enough to train, the membership now provides steady mat time,
technique exposure and belt progress.  A deliberate specialist session still
accelerates that development, but is no longer the only way it can happen.
"""
from __future__ import annotations

import random
from typing import Iterable

from . import data

GYM_LABELS = {"bjj": "BJJ", "judo": "Judo", "kb": "Kickboxing", "tkd": "Taekwondo"}
GYM_DISCIPLINES = {
    "bjj": ("BJJ",),
    "judo": ("Judo",),
    # Kickboxing rooms in the data include Dutch/kickboxing and Muay Thai work.
    "kb": ("Kickboxing", "Muay Thai"),
    "tkd": ("Taekwondo",),
}
GYM_SKILLS = {
    "bjj": ("submissions", "ground_control", "grappling"),
    "judo": ("grappling", "ground_control", "takedown_def"),
    "kb": ("kicks", "striking", "distance_management"),
    "tkd": ("kicks", "speed", "distance_management"),
}


def ensure(fighter) -> None:
    fighter.specialty_gym_dues = max(0, int(getattr(fighter, "specialty_gym_dues", 0) or 0))
    fighter.specialty_gym_weeks = max(0, int(getattr(fighter, "specialty_gym_weeks", 0) or 0))
    fighter.specialty_gym_tech_xp = max(0, int(getattr(fighter, "specialty_gym_tech_xp", 0) or 0))
    fighter.specialty_gym_last_learn_week = max(0, int(getattr(fighter, "specialty_gym_last_learn_week", 0) or 0))
    fighter.specialty_gym_auto = bool(getattr(fighter, "specialty_gym_auto", True))
    if not isinstance(getattr(fighter, "specialty_gym_event_history", None), list):
        fighter.specialty_gym_event_history = []


def gym_type(fighter) -> str:
    return str(getattr(fighter, "specialty_gym_type", "") or "").lower()


def _eligible_technique_rows(fighter, kind: str) -> list[dict]:
    disciplines = set(GYM_DISCIPLINES.get(kind, ()))
    if not disciplines:
        return []
    rows = [row for row in data.TECHNIQUES_DB if row.get("discipline") in disciplines]
    if not getattr(fighter, "pro_debut", False):
        try:
            from .v08 import technique_amateur_ok, is_illegal_amateur_name
            rows = [r for r in rows if technique_amateur_ok(r) and not is_illegal_amateur_name(r.get("name", ""))]
        except Exception:
            pass
    return rows


def _syllabus(fighter, kind: str) -> list[str]:
    """Signature gym moves first, then the wider discipline syllabus.

    Prerequisites are respected when choosing a new move, so membership does
    not teleport a novice straight into an advanced branch.
    """
    wider = [str(r.get("name")) for r in _eligible_technique_rows(fighter, kind) if r.get("name")]
    valid = set(wider)
    signature = [str(x) for x in (getattr(fighter, "specialty_pool", None) or []) if x and str(x) in valid]
    out = []
    for name in signature + wider:
        if name not in out:
            out.append(name)
    return out


def _learnable(fighter, kind: str) -> list[str]:
    known = set(getattr(fighter, "techniques", None) or [])
    rows = {str(r.get("name")): r for r in _eligible_technique_rows(fighter, kind) if r.get("name")}
    signature = [str(x) for x in (getattr(fighter, "specialty_pool", None) or []) if str(x) in rows]
    order = []
    for name in signature + list(rows):
        if name and name not in order:
            order.append(name)
    out = []
    for name in order:
        if name in known:
            continue
        row = rows.get(name, {})
        prereq = row.get("prerequisite")
        if prereq and prereq not in known:
            continue
        out.append(name)
    return out


def _known_syllabus(fighter, kind: str) -> list[str]:
    syllabus = set(_syllabus(fighter, kind))
    return [name for name in (getattr(fighter, "techniques", None) or []) if name in syllabus]


def _develop_technique(fighter, kind: str, console=None, force: bool = False) -> str | None:
    """Spend accumulated gym XP on a new move or mastery level."""
    ensure(fighter)
    threshold = 3
    if not force and fighter.specialty_gym_tech_xp < threshold:
        return None
    if not force:
        fighter.specialty_gym_tech_xp -= threshold
    else:
        fighter.specialty_gym_tech_xp = max(0, fighter.specialty_gym_tech_xp - 1)

    unknown = _learnable(fighter, kind)
    if unknown:
        # Signature techniques remain more likely while they are still unknown.
        signature = [x for x in (getattr(fighter, "specialty_pool", None) or []) if x in unknown]
        pool = signature * 3 + unknown
        name = random.choice(pool)
        if fighter.learn_technique(name):
            fighter.specialty_gym_last_learn_week = int(getattr(fighter, "week", 0) or 0)
            if console:
                console.good("%s taught you %s." % (getattr(fighter, "specialty_coach", None) or "Your coach", name))
            return "learned:%s" % name

    known = [n for n in _known_syllabus(fighter, kind)
             if int((getattr(fighter, "technique_levels", None) or {}).get(n, 1) or 1) < 5]
    if known:
        # Prefer the least-mastered material rather than repeatedly maxing one move.
        levels = getattr(fighter, "technique_levels", None) or {}
        low = min(int(levels.get(n, 1) or 1) for n in known)
        pool = [n for n in known if int(levels.get(n, 1) or 1) == low]
        name = random.choice(pool)
        if fighter.level_up_technique(name):
            if console:
                console.info("Gym reps improved %s to Lv%s." % (name, fighter.technique_levels.get(name)))
            return "leveled:%s" % name
    return None


def _belt_week(fighter, kind: str, amount: int, console=None) -> str | None:
    if kind not in ("bjj", "judo", "tkd"):
        return None
    from . import amateur_sports
    amateur_sports.train_belt(fighter, "taekwondo" if kind == "tkd" else kind, amount)
    return amateur_sports.auto_promote_belt(fighter, "taekwondo" if kind == "tkd" else kind, console=console)


def tick(fighter, console=None) -> None:
    """Automatic development from one calendar week of active membership."""
    ensure(fighter)
    if not getattr(fighter, "specialty_gym", None) or not fighter.specialty_gym_auto:
        return
    kind = gym_type(fighter)
    if kind not in GYM_LABELS:
        return
    # Home membership remains on the books while abroad, but it cannot teach
    # you from another continent.  This also prevents double development with
    # international-camp technique rewards.
    if getattr(fighter, "intl_camp", None):
        return
    if int(getattr(fighter, "health", 100) or 100) < 25:
        return

    fighter.specialty_gym_weeks += 1
    fighter.specialty_gym_tech_xp += 1
    _belt_week(fighter, kind, 3, console=console)
    # XP guarantees a new/leveled technique about every three home weeks.
    _develop_technique(fighter, kind, console=console)

    # Long-term room familiarity gives very slow, capped skill polish.  It is
    # deliberately much smaller than choosing Train as the week's action.
    if fighter.specialty_gym_weeks % 8 == 0:
        skills = GYM_SKILLS.get(kind, ())
        if skills:
            skill = random.choice(skills)
            try:
                from .physiology import gain_stat
                gain_stat(fighter, skill, 1)
            except Exception:
                setattr(fighter, skill, min(99, int(getattr(fighter, skill, 40) or 40) + 1))
            if console:
                console.info("%s membership: %s sharpened." % (GYM_LABELS[kind], skill.replace("_", " ").title()))


def manual_session(fighter, console=None) -> bool:
    """Extra specialist session selected from Team & Gym."""
    ensure(fighter)
    kind = gym_type(fighter)
    if kind not in GYM_LABELS or not getattr(fighter, "specialty_gym", None):
        return False
    if getattr(fighter, "intl_camp", None):
        return False
    if int(getattr(fighter, "energy", 0) or 0) < 8:
        if console:
            console.warn("Not enough energy for specialist rounds.")
        return False
    fighter.energy = max(0, int(fighter.energy) - 8)
    fighter.specialty_gym_tech_xp += 2
    _belt_week(fighter, kind, 5, console=console)
    result = _develop_technique(fighter, kind, console=console)
    if console and not result:
        console.print("Hard specialist rounds. The work went into your next breakthrough.")
    return True


def status_lines(fighter) -> list[str]:
    ensure(fighter)
    if not getattr(fighter, "specialty_gym", None):
        return ["No specialist membership."]
    kind = gym_type(fighter)
    label = GYM_LABELS.get(kind, kind.upper() or "Specialist")
    rows = [
        "%s · %s" % (getattr(fighter, "specialty_gym", "Gym"), label),
        "Coach %s · %s membership weeks" % (getattr(fighter, "specialty_coach", None) or "—", fighter.specialty_gym_weeks),
        "Technique progress %s/3" % min(3, fighter.specialty_gym_tech_xp),
    ]
    if kind in ("bjj", "judo", "tkd"):
        try:
            from .amateur_sports import belt_progress_line
            belt = (getattr(fighter, "bjj_belt", None) if kind == "bjj" else
                    getattr(fighter, "judo_belt", None) if kind == "judo" else getattr(fighter, "tkd_belt", None))
            rows.append("%s %s belt · %s" % (label, str(belt or "white").title(), belt_progress_line(fighter, "taekwondo" if kind == "tkd" else kind)))
        except Exception:
            pass
    else:
        known = len(_known_syllabus(fighter, kind))
        total = len(_syllabus(fighter, kind))
        rows.append("Syllabus %s/%s techniques known" % (known, total))
    return rows


def syllabus_lines(fighter, limit: int = 18) -> list[str]:
    ensure(fighter)
    kind = gym_type(fighter)
    levels = getattr(fighter, "technique_levels", None) or {}
    rows = []
    for name in _syllabus(fighter, kind)[:limit]:
        if name in levels:
            rows.append("%s · Lv%s" % (name, levels.get(name, 1)))
        else:
            rows.append("%s · not learned" % name)
    return rows
