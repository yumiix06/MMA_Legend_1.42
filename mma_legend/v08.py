"""0.8.0 helpers: records, medals, scout, belts, debut penalty."""
from __future__ import annotations

import random


def am_bouts(fighter) -> int:
    rec = list(getattr(fighter, "amateur_record", [0, 0, 0]) or [0, 0, 0])
    return int(rec[0]) + int(rec[1]) + int(rec[2])


def pro_bouts(fighter) -> int:
    rec = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    return int(rec[0]) + int(rec[1]) + int(rec[2])


def record_line(fighter) -> str:
    pr = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    ar = list(getattr(fighter, "amateur_record", [0, 0, 0]) or [0, 0, 0])
    return "pro %s-%s-%s  ·  am %s-%s-%s" % (pr[0], pr[1], pr[2], ar[0], ar[1], ar[2])


def empty_medals() -> dict:
    z = {"gold": 0, "silver": 0, "bronze": 0}
    return {"national": dict(z), "continental": dict(z), "european": dict(z), "world": dict(z)}


def ensure_medals(fighter) -> dict:
    m = getattr(fighter, "medals", None)
    if not isinstance(m, dict):
        m = empty_medals()
        fighter.medals = m
    for k in ("national", "continental", "european", "world"):
        m.setdefault(k, {"gold": 0, "silver": 0, "bronze": 0})
        for c in ("gold", "silver", "bronze"):
            m[k].setdefault(c, 0)
    # v1.30: European medals were the old generic continental table.
    # Migrate European athletes without deleting the legacy key.
    try:
        from .systems15 import continent
        if continent(getattr(fighter, "country", "")) == "Europe":
            for c in ("gold", "silver", "bronze"):
                if int(m["continental"].get(c, 0) or 0) == 0:
                    m["continental"][c] = int(m["european"].get(c, 0) or 0)
    except Exception:
        pass
    return m


def medal_key(comp_name: str) -> str:
    n = (comp_name or "").lower()
    if "world" in n or "immaf" in n:
        return "world"
    if any(x in n for x in ("europe", "pan-amer", "asian", "african", "oceania", "continental")):
        return "continental"
    return "national"


def award_medal(fighter, comp_name: str, colour: str) -> None:
    m = ensure_medals(fighter)
    key = medal_key(comp_name)
    if colour not in ("gold", "silver", "bronze"):
        return
    m[key][colour] = int(m[key].get(colour, 0)) + 1
    tag = "%s_%s" % (key, colour)
    titles = list(getattr(fighter, "amateur_titles", []) or [])
    if tag not in titles:
        titles.append(tag)
    fighter.amateur_titles = titles


def national_best(fighter) -> str:
    m = ensure_medals(fighter)["national"]
    if m.get("gold"):
        return "gold"
    if m.get("silver"):
        return "silver"
    if m.get("bronze"):
        return "bronze"
    return ""


def continental_eligible(fighter) -> bool:
    if getattr(fighter, "pro_debut", False):
        return False
    if not getattr(fighter, "national_team", False):
        return False
    return national_best(fighter) in ("gold", "silver")


def europe_eligible(fighter) -> bool:
    """Legacy wrapper retained for old tests/saves; Europe uses continental rules."""
    if not continental_eligible(fighter):
        return False
    from .systems15 import continent
    return continent(getattr(fighter, "country", "")) == "Europe"


def worlds_eligible(fighter) -> bool:
    if getattr(fighter, "pro_debut", False) or not getattr(fighter, "national_team", False):
        return False
    m = ensure_medals(fighter)
    cont = m.get("continental", {}) or {}
    if any(int(cont.get(c, 0) or 0) for c in ("gold", "silver", "bronze")):
        return True
    # Keep old European save compatibility until those saves are migrated.
    old = m.get("european", {}) or {}
    if any(int(old.get(c, 0) or 0) for c in ("gold", "silver", "bronze")):
        return True
    return bool(m["national"].get("gold"))

def _recent_tendencies(opponent) -> list[str]:
    rows=list(getattr(opponent,"fight_history",None) or [])[-4:]; agg={"td":0,"sub":0,"head":0,"body":0,"leg":0,"ctrl":0,"wins":0}
    for row in rows:
        st=row.get("stats") if isinstance(row,dict) else {}; st=st if isinstance(st,dict) else {}
        agg["td"]+=int(st.get("takedowns_attempted",0) or 0); agg["sub"]+=int(st.get("submission_attempts",0) or 0)
        agg["head"]+=int(st.get("head_landed",0) or 0); agg["body"]+=int(st.get("body_landed",0) or 0); agg["leg"]+=int(st.get("leg_landed",0) or 0)
        agg["ctrl"]+=int(st.get("control_sec",0) or 0); agg["wins"]+=1 if str(row.get("result","")).lower().startswith("w") else 0
    tags=[]
    if agg["td"]>=8: tags.append("shoots often")
    if agg["sub"]>=6: tags.append("chains submissions")
    target=max(("head","body","leg"),key=lambda k:agg[k]) if rows else "head"
    if rows and agg[target]>=4: tags.append("targets the %s"%target)
    if agg["ctrl"]>=120: tags.append("leans on control")
    if rows and agg["wins"]>=3: tags.append("hot recent run")
    return tags or (["limited recent tape"] if rows else ["no recent tape"] )

def scout_lines(fighter, opponent) -> list:
    """Public scouting API; v1.39 intelligence owns report quality/content."""
    try:
        from . import combat_intelligence as _ci
        return _ci.scout_lines(fighter, opponent)
    except Exception:
        return ["Scout: limited tape."]


def debut_penalty(fighter) -> int:
    if not getattr(fighter, "pro_debut", False):
        return 0
    if am_bouts(fighter) >= 10:
        return 0
    done = int(getattr(fighter, "story_flags", {}).get("pro_fights_done", 0) or 0)
    if done >= 5:
        return 0
    return max(0, 12 - done * 2)


def note_pro_fight(fighter) -> None:
    from . import record as _rec
    _rec.sync(fighter)


def turn_pro_ready(fighter) -> bool:
    if getattr(fighter, "pro_debut", False):
        return False
    return am_bouts(fighter) >= 5


def turn_pro_on_cooldown(fighter) -> bool:
    flags = getattr(fighter, "story_flags", {}) or {}
    last = int(flags.get("cd_turn_pro", -999) or -999)
    if last < 0:
        return False
    return fighter.week - last < 5


def mark_turn_pro_declined(fighter) -> None:
    flags = getattr(fighter, "story_flags", None)
    if flags is None:
        fighter.story_flags = {}
        flags = fighter.story_flags
    flags["cd_turn_pro"] = fighter.week


def cancel_amateur_comps(fighter) -> None:
    fighter.competition_signup = None
    fighter.competition_week = 0
    fighter.competition_prep = False
    fighter.competition_sport = "MMA"
    fighter.competition_level = None
    fighter.competition_due_week = 0


def belt_label(fighter) -> str:
    belt = getattr(fighter, "bjj_belt", None) or ""
    stripes = int(getattr(fighter, "bjj_stripes", 0) or 0)
    if not belt:
        return "none"
    return "%s (%s stripe%s)" % (belt, stripes, "" if stripes == 1 else "s")


def tick_bjj_stripes(fighter, console=None) -> None:
    """Compatibility hook only.

    v1.31 makes amateur_sports the sole owner of BJJ/Judo mat weeks, grading
    points and promotions. The old weekly timer promoted belts simply because
    a calendar week passed and could double-count specialist training.
    """
    return None


def technique_amateur_ok(tech: dict) -> bool:
    if tech.get("amateur_ok") is False or tech.get("pro_only"):
        return False
    return True


def is_illegal_amateur_name(name: str) -> bool:
    n = (name or "").lower()
    banned = ("heel hook", "elbow", "neck crank", "twister", "can opener", "knee to head", "soccer kick")
    return any(b in n for b in banned)
