"""Career legacy, records, multiple championships and Hall of Fame (v1.30).

The module deliberately derives most history from persistent ledgers instead of
creating another hidden progression score.  `title_history`, live belts and the
fighter's fight history remain the sources of truth.
"""
from __future__ import annotations

from collections import Counter


def _fid(fighter):
    return getattr(fighter, "fid", None)


def current_belts(pool, fighter, org: str | None = None) -> list[dict]:
    fid = _fid(fighter)
    out = []
    for key, info in (getattr(pool, "belts", None) or {}).items():
        if not isinstance(info, dict) or info.get("fid") != fid:
            continue
        if org and str(info.get("org") or "") != str(org):
            continue
        row = dict(info)
        row.setdefault("key", key)
        out.append(row)
    return out


def title_stats(pool, fighter) -> dict:
    fid = _fid(fighter)
    flags = getattr(fighter, "story_flags", None) or {}
    lifetime = flags.get("career_title_stats") if isinstance(flags, dict) else None
    if isinstance(lifetime, dict):
        classes = []
        for token in list(lifetime.get("championships") or []):
            if "|" in str(token):
                org, wc = str(token).split("|", 1)
                classes.append((org, wc))
        return {
            "title_wins": int(lifetime.get("title_wins", 0) or 0),
            "defenses": int(lifetime.get("defenses", 0) or 0),
            "ufc_title_wins": int(lifetime.get("ufc_title_wins", 0) or 0),
            "ufc_defenses": int(lifetime.get("ufc_defenses", 0) or 0),
            "championships": sorted(classes),
            "current_belts": current_belts(pool, fighter),
        }

    # Migration/diagnostic fallback for older saves that pre-date the lifetime
    # counters. New 1.30 careers stop depending on this capped recent ledger.
    hist = [h for h in list(getattr(pool, "title_history", None) or [])
            if h.get("fighter_id") == fid]
    wins = [h for h in hist if h.get("action") in ("won", "inaugural")]
    defenses = [h for h in hist if h.get("action") == "defended"]
    ufc_wins = [h for h in wins if h.get("org") == "UFC"]
    ufc_def = [h for h in defenses if h.get("org") == "UFC"]
    classes = sorted({(h.get("org"), h.get("weight_class")) for h in wins})
    return {
        "title_wins": len(wins), "defenses": len(defenses),
        "ufc_title_wins": len(ufc_wins), "ufc_defenses": len(ufc_def),
        "championships": classes, "current_belts": current_belts(pool, fighter),
    }


def performance_bonus_count(fighter) -> int:
    flags = getattr(fighter, "story_flags", None) or {}
    return int(flags.get("performance_bonuses", 0) or 0)


def hall_score(pool, fighter) -> float:
    """Transparent Hall-of-Fame résumé score; not a combat attribute."""
    rec = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    wins = int(rec[0])
    stats = title_stats(pool, fighter)
    fame = int(getattr(fighter, "fame", 0) or 0)
    legacy = int(getattr(fighter, "legacy_score", 0) or 0)
    bonuses = performance_bonus_count(fighter)
    medals = 0
    for table in (getattr(fighter, "sport_championships", None) or {}).values():
        if not isinstance(table, dict):
            continue
        medals += sum(sum((level or {}).values()) for level in table.values() if isinstance(level, dict))
    return round(
        wins * 1.25
        + stats["title_wins"] * 7.0
        + stats["defenses"] * 4.0
        + stats["ufc_title_wins"] * 12.0
        + stats["ufc_defenses"] * 5.0
        + fame * 0.18
        + legacy * 0.20
        + bonuses * 1.5
        + min(8, medals) * 0.6,
        1,
    )


def hall_tier(score: float) -> str:
    if score >= 90:
        return "first-ballot"
    if score >= 65:
        return "Hall of Fame"
    if score >= 45:
        return "borderline"
    if score >= 28:
        return "notable career"
    return "outside consideration"


def maybe_induct(pool, fighter, reason: str = "retirement") -> dict | None:
    score = hall_score(pool, fighter)
    if score < 65:
        return None
    if not isinstance(getattr(pool, "hall_of_fame", None), list):
        pool.hall_of_fame = []
    fid = _fid(fighter)
    existing = next((x for x in pool.hall_of_fame if x.get("fid") == fid), None)
    if existing:
        return existing
    stats = title_stats(pool, fighter)
    row = {
        "fid": fid, "name": getattr(fighter, "name", ""),
        "country": getattr(fighter, "country", ""),
        "week": int(getattr(pool, "week", 0) or getattr(fighter, "week", 0) or 0),
        "score": score, "tier": hall_tier(score), "reason": reason,
        "record": list(getattr(fighter, "pro_record", None) or [0, 0, 0]),
        "title_wins": stats["title_wins"], "defenses": stats["defenses"],
        "ufc_title_wins": stats["ufc_title_wins"], "ufc_defenses": stats["ufc_defenses"],
    }
    pool.hall_of_fame.append(row)
    pool.hall_of_fame = pool.hall_of_fame[-200:]
    return row


def on_belt_awarded(pool, org: str, wc: str, winner) -> bool:
    """Mark a real simultaneous two-division champion.

    The belt ledger remains authoritative.  The fighter flag only tells belt
    repair that holding another class is intentional rather than stale data.
    """
    belts = current_belts(pool, winner, org=org)
    if len(belts) < 2:
        return False
    classes = sorted({str(b.get("wc") or "") for b in belts if b.get("wc")})
    flags = getattr(winner, "story_flags", None)
    if not isinstance(flags, dict):
        winner.story_flags = {}; flags = winner.story_flags
    was = bool(flags.get("double_champion"))
    flags["double_champion"] = True
    flags["double_champ_classes"] = classes
    for info in belts:
        info["multi_division"] = True
        key = str(info.get("key") or (str(info.get("org")) + "|" + str(info.get("wc"))))
        if key in getattr(pool, "belts", {}):
            pool.belts[key]["multi_division"] = True
    if not was:
        try:
            pool._title_log(org, wc, "double_champion", fighter=winner)
        except Exception:
            pass
        pool.news.append("%s becomes a two-division %s champion." % (winner.name, org))
    return not was


def record_book(pool, player=None, limit: int = 5) -> dict[str, list[tuple]]:
    fighters = list(getattr(pool, "fighters", None) or [])
    if player is not None and player not in fighters:
        fighters.append(player)
    rows = [f for f in fighters if getattr(f, "pro_debut", False)]
    def top(key):
        ranked = sorted(((key(f), f) for f in rows), key=lambda x: x[0], reverse=True)
        return [(value, f) for value, f in ranked[:limit] if value > 0]
    return {
        "pro_wins": top(lambda f: int((getattr(f, "pro_record", [0]) or [0])[0])),
        "title_defenses": top(lambda f: title_stats(pool, f)["defenses"]),
        "ufc_defenses": top(lambda f: title_stats(pool, f)["ufc_defenses"]),
        "championships": top(lambda f: title_stats(pool, f)["title_wins"]),
        "performance_bonuses": top(performance_bonus_count),
        "legacy": top(lambda f: hall_score(pool, f)),
    }


def candidate_rows(pool, player=None, limit: int = 8) -> list[dict]:
    fighters = list(getattr(pool, "fighters", None) or [])
    if player is not None and player not in fighters:
        fighters.append(player)
    out = []
    for f in fighters:
        if not getattr(f, "pro_debut", False):
            continue
        score = hall_score(pool, f)
        if score < 28:
            continue
        out.append({"fighter": f, "score": score, "tier": hall_tier(score)})
    out.sort(key=lambda row: row["score"], reverse=True)
    return out[:limit]
