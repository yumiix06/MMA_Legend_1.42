"""Career systems: category, contracts, school, auditor and recency."""
from __future__ import annotations

import random

CATEGORIES = ("MMA", "BJJ / No-Gi", "Boxing", "Kickboxing", "Wrestling", "Judo", "Combat Sambo", "Taekwondo")

_ALIASES = {
    "sambo": "Combat Sambo", "combat sambo": "Combat Sambo",
    "grappling": "BJJ / No-Gi", "bjj": "BJJ / No-Gi", "no-gi": "BJJ / No-Gi",
    "tkd": "Taekwondo", "tae kwon do": "Taekwondo",
}


def normalize_category(name: str) -> str:
    raw = str(name or "MMA").strip()
    return _ALIASES.get(raw.lower(), next((x for x in CATEGORIES if x.lower() == raw.lower()), "MMA"))

TACTICAL_SKILLS = ("distance_management", "striking_def", "submission_def", "fight_iq")

ORG_LADDER = [
    "Local Fight Nights", "LFA", "Cage Warriors", "KSW", "PFL", "Bellator", "DWCS", "UFC",
]


def ensure(fighter) -> None:
    flags = getattr(fighter, "story_flags", None)
    if flags is None:
        fighter.story_flags = {}
        flags = fighter.story_flags
    flags["compete_in"] = normalize_category(flags.get("compete_in", getattr(fighter, "active_amateur_sport", "MMA")))
    fighter.active_amateur_sport = flags["compete_in"]
    flags.setdefault("recent_opp_fids", [])
    flags.setdefault("session_log", [])
    flags.setdefault("audit", [])
    # Old passives were counters with no combat consumer. Real tactical
    # development now lives in the visible skill model.
    flags.pop("passives", None)
    flags.setdefault("org_rank", 99)
    if not getattr(fighter, "sport_records", None):
        fighter.sport_records = {"mma": [0, 0, 0]}


def compete_in(fighter) -> str:
    ensure(fighter)
    return normalize_category(fighter.story_flags.get("compete_in"))


def set_category(fighter, name: str) -> str:
    ensure(fighter)
    n = normalize_category(name)
    fighter.story_flags["compete_in"] = n
    fighter.active_amateur_sport = n
    return "Competing in %s." % n


def note_opponent(fighter, opp) -> None:
    ensure(fighter)
    fid = getattr(opp, "fid", None) or getattr(opp, "name", "")
    rec = list(fighter.story_flags.get("recent_opp_fids") or [])
    rec.append(str(fid))
    fighter.story_flags["recent_opp_fids"] = rec[-24:]


def seen_recently(fighter, opp) -> bool:
    ensure(fighter)
    fid = str(getattr(opp, "fid", None) or getattr(opp, "name", ""))
    rec = list(fighter.story_flags.get("recent_opp_fids") or [])
    return rec.count(fid) >= 1 and fid in rec[-8:]


def log_session(fighter, kind: str, detail: str = "") -> None:
    ensure(fighter)
    log = list(fighter.story_flags.get("session_log") or [])
    log.append({"week": int(getattr(fighter, "week", 0) or 0), "kind": kind, "detail": detail})
    fighter.story_flags["session_log"] = log[-80:]
    # A small cross-training chance rewards consistent sessions without
    # recreating the old invisible 1-10 passive progression.
    if kind in ("train", "spar", "camp") and random.random() < 0.12:
        pick = random.choice(TACTICAL_SKILLS)
        try:
            from .physiology import gain_stat
            gain_stat(fighter, pick, 1)
        except (ImportError, AttributeError, TypeError, ValueError):
            setattr(fighter, pick, min(100, int(getattr(fighter, pick, 20) or 20) + 1))


def graduate(fighter, console=None) -> str:
    """Compatibility entry point for the v1.40 education system."""
    try:
        from .education import ensure, _graduate_secondary
        ensure(fighter)
        if fighter.education_stage != "secondary":
            return ""
        return "graduated" if _graduate_secondary(fighter, console) else ""
    except Exception:
        return ""

def contract_locked(fighter, org: str) -> bool:
    """True if taking a date from `org` would breach an exclusive deal.

    Delegates to contracts.can_accept() so exclusivity is enforced in exactly
    one place. Kept as a thin wrapper because several 1.7-era call sites and
    tests use this name.
    """
    try:
        from . import contracts
        allowed, _why = contracts.can_accept(fighter, org)
        return not allowed
    except Exception:
        pass
    c = getattr(fighter, "org_contract", None) or {}
    if not c:
        return False
    home = str(c.get("org") or getattr(fighter, "organization", "") or "")
    if not home or org == home:
        return False
    if org in ("DWCS", "Dana White Contender Series") and home not in ("UFC",):
        return False
    return True


def manager_on_offer(fighter, offer: dict) -> str:
    org = str(offer.get("org") or "")
    purse = int(offer.get("purse_win") or 0)
    locked = contract_locked(fighter, org)
    if locked:
        return "Manager: you are signed to %s. This card is a breach." % (
            (getattr(fighter, "org_contract") or {}).get("org")
        )
    if org == "UFC" and int(getattr(fighter, "fame", 0) or 0) < 18:
        return "Manager: UFC is a reach. Push DWCS first."
    if org == "DWCS":
        return "Manager: Contender Series is the clean door. Take it if the weight is right."
    if purse < 200:
        return "Manager: purse is light. I would ask for show money."
    return "Manager: %s is a fair step. Sign it if the camp is ready." % org


def dwcs_ready(fighter) -> bool:
    """Invitation bar. Not a 3-0 regional kid."""
    try:
        from . import dwcs
        ok, _why = dwcs.eligible(fighter)
        return ok
    except Exception:
        pass
    if not getattr(fighter, "pro_debut", False):
        return False
    rec = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    return rec[0] >= 6 and int(getattr(fighter, "fame", 0) or 0) >= 15


def ufc_ready(fighter) -> bool:
    rec = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    ufc_bouts = sum(
        1 for h in (getattr(fighter, "fight_history", None) or [])
        if str(h.get("event") or "").upper() in ("UFC", "DWCS")
    )
    return rec[0] >= 8 and int(getattr(fighter, "fame", 0) or 0) >= 22 and ufc_bouts >= 1


def audit_fighter(fighter) -> list:
    """Logic checker written into the save."""
    notes = []
    if int(getattr(fighter, "suspension_weeks", 0) or 0) > 0 and getattr(fighter, "booked_fight", None):
        notes.append("booked while suspended")
    if getattr(fighter, "pro_debut", False) and getattr(fighter, "competition_signup", None):
        notes.append("pro still signed to amateur comp")
    rec = list(getattr(fighter, "amateur_record", [0, 0, 0]) or [])
    if rec and rec[0] + rec[1] + rec[2] != len([
        h for h in (getattr(fighter, "fight_history", None) or [])
        if h.get("sport", "mma") == "mma" and not getattr(fighter, "pro_debut", False)
    ]) and False:
        notes.append("record vs history mismatch (soft)")
    if int(getattr(fighter, "age", 0) or 0) >= 18 and getattr(fighter, "school_status", "") == "school":
        notes.append("still in school after 18 — should graduate")
    money = int(getattr(fighter, "money", 0) or 0)
    if money == 0 and int(getattr(fighter, "debt", 0) or 0) > 800:
        notes.append("cash floor 0 with high debt")
    fighter.story_flags = fighter.story_flags or {}
    fighter.story_flags["audit"] = notes[-12:]
    fighter.story_flags["audit_week"] = int(getattr(fighter, "week", 0) or 0)
    return notes
