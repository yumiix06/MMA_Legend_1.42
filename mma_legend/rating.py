"""Hidden power rating used only for matchmaking."""
from __future__ import annotations


def power(fighter) -> float:
    from . import constants as C
    skills = list(getattr(C, "SKILLS", []) or [])
    if not skills:
        skills = ["striking", "grappling", "cardio", "fight_iq"]
    avg = sum(float(getattr(fighter, s, 40) or 40) for s in skills) / max(1, len(skills))
    rec = fighter.pro_record if getattr(fighter, "pro_debut", False) else fighter.amateur_record
    rec = rec or [0, 0, 0]
    form = 0.0
    for x in list(getattr(fighter, "recent_results", None) or [])[-5:]:
        form += 2.0 if str(x).upper().startswith("W") else -1.5
    age = int(getattr(fighter, "age", 22) or 22)
    age_mod = 2.0 if 22 <= age <= 29 else (0 if age < 22 else -1.2 * max(0, age - 30))
    inj = getattr(fighter, "injury", None) or {}
    inj_mod = -4.0 if int(inj.get("weeks", 0) or 0) > 0 else 0.0
    camp = 1.5 if getattr(fighter, "camp_active", False) else 0.0
    conf = (int(getattr(fighter, "confidence", 50) or 50) - 50) * 0.04
    cut = -2.0 if getattr(fighter, "_chose_cut", False) else 0.0
    exp = (int(rec[0]) + int(rec[1])) * 0.35
    return avg + rec[0] * 1.1 - rec[1] * 0.9 + form + age_mod + inj_mod + camp + conf + cut + exp


def window(fighter) -> float:
    if not getattr(fighter, "pro_debut", False):
        return 8.0
    room = str(getattr(fighter, "room", "") or "")
    if room in ("ufc", "mid", "dwcs"):
        return 4.0
    if room in ("national",):
        return 5.0
    return 6.0


def close_enough(a, b) -> bool:
    return abs(power(a) - power(b)) <= window(a) + 3.0
