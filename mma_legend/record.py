"""One writer for official records.

History is the ledger. Pro W-L and pro_fights_done are derived from MMA
rows that are tagged pro or fought under a named promotion. Grappling
and blank amateur nights do not move the pro record.
"""
from __future__ import annotations

from . import orgs


PRO_EVENTS = set(orgs.ORGS) | {
    "DWCS", "Dana White Contender Series", "Contender Series",
}
MMA_TAGS = {"mma", "mixed martial arts"}
NON_MMA_TAGS = {
    "grappling", "adcc", "no-gi", "nogi", "bjj", "bjj / no-gi",
    "boxing", "kickboxing", "taekwondo", "wrestling", "judo", "sambo",
    "combat sambo",
}


def _tag(value) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def is_mma(row: dict) -> bool:
    """Return whether a history row belongs to MMA.

    New history rows carry an explicit sport/ruleset and that metadata is
    authoritative. Only legacy untagged rows fall back to event-name heuristics.
    The older implementation treated every explicit side sport except BJJ as MMA,
    which polluted amateur-ledger audits and any future consumer of this helper.
    """
    if row.get("sport") not in (None, ""):
        sport = _tag(row.get("sport"))
        return sport in MMA_TAGS

    if row.get("ruleset") not in (None, ""):
        ruleset = _tag(row.get("ruleset"))
        if ruleset in NON_MMA_TAGS:
            return False
        if ruleset in MMA_TAGS:
            return True

    ev = _tag(row.get("event"))
    if any(token in ev for token in (
        "no-gi", "nogi", "adcc", "combat sambo", "boxing", "kickboxing",
        "wrestling", "judo", "taekwondo", "bjj", "grappling",
    )):
        return False
    return True


def is_pro_row(row: dict) -> bool:
    if "pro" in row:
        return bool(row.get("pro"))
    ev = str(row.get("event") or "").strip()
    if ev in PRO_EVENTS:
        return True
    up = ev.upper()
    if "UFC" in up or up == "DWCS":
        return True
    return False


def _wl(rows: list) -> list:
    w = l = d = 0
    for h in rows:
        r = str(h.get("result") or "").title()
        if r.startswith("W"):
            w += 1
        elif r.startswith("L"):
            l += 1
        else:
            d += 1
    return [w, l, d]



def performance_rating(stats: dict | None, opponent_stats: dict | None, result: str, method: str, round_no: int) -> float:
    """Return a defined 1.0-10.0 bout grade from observable fight data.

    It is deliberately a *performance* grade rather than another hidden skill
    rating: result matters, but efficiency, activity, grappling and the opponent's
    production can move a competitive loss above a poor win.
    """
    st = dict(stats or {})
    op = dict(opponent_stats or {})
    landed = int(st.get("strikes_landed", 0) or 0) + int(st.get("ground_strikes_landed", 0) or 0)
    attempts = int(st.get("strikes_attempted", 0) or 0) + int(st.get("ground_strikes_attempted", 0) or 0)
    opp_landed = int(op.get("strikes_landed", 0) or 0) + int(op.get("ground_strikes_landed", 0) or 0)
    td = int(st.get("takedowns_landed", 0) or 0)
    ctrl = int(st.get("control_sec", 0) or 0)
    kd = int(st.get("knockdowns", 0) or 0)
    sub = int(st.get("submission_attempts", 0) or 0)
    pos = int(st.get("passes", 0) or 0) + int(st.get("back_takes", 0) or 0) + int(st.get("mount_ups", 0) or 0)

    r = str(result or "Draw").title()
    score = 5.0 + (1.45 if r == "Win" else -1.15 if r == "Loss" else 0.0)
    if attempts:
        eff = landed / max(1, attempts)
        score += max(-0.45, min(0.65, (eff - 0.48) * 1.6))
    score += min(0.65, landed / 45.0)
    score += min(0.80, td * 0.13 + ctrl / 240.0 + pos * 0.08 + kd * 0.18 + sub * 0.035)
    if op:
        score += max(-0.65, min(0.65, (landed - opp_landed) / 35.0))
    meth = str(method or "Decision").lower()
    if r == "Win" and any(x in meth for x in ("ko", "tko", "submission", "stoppage")):
        score += 0.45 + max(0.0, (3 - max(1, int(round_no or 1))) * 0.12)
    elif r == "Loss" and any(x in meth for x in ("ko", "tko", "submission", "stoppage")):
        score -= 0.20
    return round(max(1.0, min(10.0, score)), 1)

def tag_last(fighter, *, amateur: bool, event: str = "") -> None:
    hist = list(getattr(fighter, "fight_history", None) or [])
    if not hist:
        return
    row = dict(hist[-1])
    if event and not row.get("event"):
        row["event"] = event
    row["pro"] = (not amateur) and is_mma(row)
    hist[-1] = row
    fighter.fight_history = hist


def _ensure_baseline(fighter) -> list:
    """The record a fighter carried BEFORE we started logging their history.

    Every NPC is generated with a synthetic record (say 4-1) and no fight
    history at all. Deriving the official record purely from history therefore
    wiped a background fighter's entire career the first time they fought:
    4-1 became 1-0. The baseline is that pre-history career, snapshotted once
    and then added to whatever the ledger records from here on.
    """
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}
        flags = fighter.story_flags
    base = flags.get("record_baseline")
    if isinstance(base, (list, tuple)) and len(base) == 3:
        return [int(x) for x in base]
    hist = list(getattr(fighter, "fight_history", None) or [])
    pro_rows = [h for h in hist if is_mma(h) and is_pro_row(h)]
    cur = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    if pro_rows:
        # This fighter already has a pro ledger, so the ledger IS the record.
        # A stored number that disagrees with it is corruption to be repaired
        # (the 1.18 case: bogus records attached to fighters who had history).
        base = [0, 0, 0]
    else:
        # No pro history at all, but a record exists: this is a generated NPC
        # carrying a synthetic career. Preserve it, or their first fight wipes
        # it (4-1 became 1-0 before this).
        base = [max(0, int(x)) for x in cur]
    flags["record_baseline"] = base
    return base


def sync(fighter) -> list:
    """Recompute official pro record from history. Returns [W,L,D]."""
    base = _ensure_baseline(fighter)
    hist = list(getattr(fighter, "fight_history", None) or [])
    pro_rows = [h for h in hist if is_mma(h) and is_pro_row(h)]
    derived = _wl(pro_rows)
    fighter.pro_record = [base[i] + derived[i] for i in range(3)]
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}
        flags = fighter.story_flags
    flags["pro_fights_done"] = sum(base) + len(pro_rows)
    flags["history_n"] = len(hist)
    return list(fighter.pro_record or [0, 0, 0])


def commit(fighter, opponent_name: str, result: str, method: str, round_no: int,
           event: str = "", stats=None, opponent_stats=None, sport: str = "mma", amateur: bool = True) -> None:
    # Snapshot the pre-history career BEFORE this bout is appended.
    if (sport or "mma") == "mma" and not amateur:
        _ensure_baseline(fighter)
    rating = performance_rating(stats, opponent_stats, result, method, round_no)
    fighter.record_fight(opponent_name, result, method, round_no, event or "",
                         performance_rating=rating, sport=sport, stats=stats)
    tag_last(fighter, amateur=amateur, event=event or "")
    if (sport or "mma") == "mma" and not amateur:
        sync(fighter)


def repair_dict(d: dict) -> dict:
    hist = list(d.get("fight_history") or [])
    pro_rows = [h for h in hist if is_mma(h) and is_pro_row(h)]
    flags = d.get("story_flags") if isinstance(d.get("story_flags"), dict) else {}
    d["story_flags"] = flags
    derived = _wl(pro_rows)
    base = flags.get("record_baseline")
    if not (isinstance(base, (list, tuple)) and len(base) == 3):
        cur = list(d.get("pro_record") or [0, 0, 0])
        base = [0, 0, 0] if pro_rows else [max(0, int(x)) for x in cur]
        flags["record_baseline"] = base
    base = [int(x) for x in base]
    d["pro_record"] = [base[i] + derived[i] for i in range(3)]
    flags["pro_fights_done"] = sum(base) + len(pro_rows)
    flags["history_n"] = len(hist)
    return d
