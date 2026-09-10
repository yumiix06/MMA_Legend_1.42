"""Fight-week atmosphere, post-event storytelling and rivalry intelligence.

v1.30 Phase 3 keeps presentation driven by real career state.  It does not add
fake scenes to low-level bouts; title/UFC/major rivalry fights get the richer
sequence, and post-event news is built from the actual result/rank/belt ledger.
"""
from __future__ import annotations


def _org(fighter, booked=None) -> str:
    booked = booked or {}
    return str(booked.get("org") or getattr(fighter, "_bout_org", "") or getattr(fighter, "organization", "") or "")


def importance(fighter, opponent=None, booked=None, is_title: bool = False) -> str:
    booked = booked or getattr(fighter, "booked_fight", None) or {}
    org = _org(fighter, booked)
    if is_title or booked.get("title"):
        return "championship"
    if org == "UFC" and (booked.get("slot") in ("main", "co-main") or int(getattr(fighter, "fame", 0) or 0) >= 35):
        return "major"
    try:
        from . import story
        if opponent is not None and getattr(fighter, "rival", None) == getattr(opponent, "name", None) and story.rival_heat(fighter) >= 35:
            return "major"
    except Exception:
        pass
    if org in ("UFC", "PFL", "Bellator", "KSW", "Cage Warriors") or int(getattr(fighter, "fame", 0) or 0) >= 20:
        return "featured"
    return "routine"


def rank_snapshot(fighter, pool, org: str | None = None, wc: str | None = None) -> int | None:
    if pool is None:
        return None
    org = org or _org(fighter)
    wc = wc or getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", None)
    try:
        board = list(pool.get_org_top(org, wc, 20) or [])
    except Exception:
        return None
    fid = getattr(fighter, "fid", None)
    for i, f in enumerate(board, 1):
        if f is fighter or (fid and getattr(f, "fid", None) == fid):
            return i
    return None


def fight_week_open(console, fighter, opponent, booked=None, is_title: bool = False) -> bool:
    booked = booked or getattr(fighter, "booked_fight", None) or {}
    level = importance(fighter, opponent, booked, is_title)
    if level not in ("championship", "major"):
        return False
    org = _org(fighter, booked) or "Fight Night"
    wc = str(booked.get("weight_class") or getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", ""))
    location = str(booked.get("location") or "")
    console.header("FIGHT WEEK", "%s%s" % (org, (" · " + location) if location else ""))
    if level == "championship":
        console.gold("Championship week · %s" % wc)
    else:
        console.print("Featured fight · %s" % wc)
    console.section("Tale of the Tape")
    for who, tag in ((fighter, "YOU"), (opponent, "OPP")):
        rec = list(getattr(who, "pro_record", None) or [0, 0, 0])
        console.print("  %s %s · %s-%s-%s" % (tag, getattr(who, "name", ""), rec[0], rec[1], rec[2]))
        console.print("    %scm · reach %scm · %s" % (
            int(getattr(who, "height", 0) or 0), int(getattr(who, "reach", 0) or 0),
            getattr(who, "stance", "Orthodox") or "Orthodox"))
    getattr(console, "continue_prompt", lambda *_a, **_k: console.read_pause("fight week", extra=0.1))("Press Enter to continue")
    return True


def staredown(console, fighter, opponent, booked=None, is_title: bool = False) -> bool:
    booked = booked or getattr(fighter, "booked_fight", None) or {}
    if importance(fighter, opponent, booked, is_title) not in ("championship", "major"):
        return False
    console.header("WEIGH-IN STAREDOWN", "Final face-off")
    console.print("%s and %s meet at center stage." % (fighter.name, opponent.name))
    console.print("  A) Calm — no reaction")
    console.print("  B) Intense — hold the stare")
    console.print("  C) Talk — make it personal")
    ans = (console.ask("Staredown > ") or "A").strip().upper()
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}; flags = fighter.story_flags
    if ans == "B":
        fighter.confidence = min(100, int(getattr(fighter, "confidence", 50) or 50) + 1)
        fighter.press_hype = min(100, int(getattr(fighter, "press_hype", 0) or 0) + 2)
        console.info("No shove, no cheap shot. The tension sells itself.")
    elif ans == "C":
        fighter.press_hype = min(100, int(getattr(fighter, "press_hype", 0) or 0) + 5)
        flags["last_trash_talk_opponent"] = getattr(opponent, "fid", None) or opponent.name
        flags["last_trash_talk_week"] = int(getattr(fighter, "week", 0) or 0)
        try:
            from . import story
            story.register_rival(fighter, opponent.name, heat=8, rival_id=getattr(opponent, "fid", None))
        except Exception:
            pass
        console.warn("You trade words. The matchup now has a personal edge.")
    else:
        fighter.discipline = min(100, int(getattr(fighter, "discipline", 50) or 50) + 1)
        console.print("You keep it professional.")
    getattr(console, "continue_prompt", lambda *_a, **_k: console.read_pause("staredown", extra=0.1))("Press Enter to continue")
    return True


def _rivalry_reasons(fighter, opponent, result: str, method: str) -> tuple[int, list[str]]:
    heat = 0; reasons = []
    low = str(method or "").lower()
    if "split" in low or "majority decision" in low or str(result).lower() == "draw":
        heat += 22; reasons.append("close decision")
    prior = [h for h in list(getattr(fighter, "fight_history", None) or [])
             if str(h.get("opponent") or "") == str(getattr(opponent, "name", ""))]
    # Called after the current fight was committed, so two ledger rows means a rematch.
    if len(prior) >= 2:
        heat += min(24, 8 + (len(prior) - 2) * 6); reasons.append("rematch history")
    if getattr(fighter, "team", None) and getattr(fighter, "team", None) == getattr(opponent, "team", None):
        heat += 14; reasons.append("gym history")
    flags = getattr(fighter, "story_flags", None) or {}
    marker = flags.get("last_trash_talk_opponent")
    if marker in (getattr(opponent, "fid", None), getattr(opponent, "name", None)):
        if int(getattr(fighter, "week", 0) or 0) - int(flags.get("last_trash_talk_week", 0) or 0) <= 6:
            heat += 18; reasons.append("trash talk")
    return heat, reasons


def rivalry_after_bout(fighter, opponent, result: str, method: str) -> list[str]:
    heat, reasons = _rivalry_reasons(fighter, opponent, result, method)
    if heat <= 0:
        return []
    try:
        from . import story
        story.register_rival(fighter, opponent.name, heat=heat, rival_id=getattr(opponent, "fid", None))
        for row in getattr(fighter, "rivalries", None) or []:
            if row.get("name") == opponent.name:
                origins = list(row.get("origins") or [])
                for reason in reasons:
                    if reason not in origins: origins.append(reason)
                row["origins"] = origins[-6:]
                row["last_week"] = int(getattr(fighter, "week", 0) or 0)
                break
    except Exception:
        return []
    return reasons


def _bonus_amount(org: str, kind: str) -> int:
    if org == "UFC":
        return 50000
    if org in ("PFL", "Bellator"):
        return 12000
    if org in ("KSW", "Cage Warriors", "BRAVE CF", "ACA"):
        return 5000
    return 1500 if kind == "performance" else 1000


def _event_row(pool, event_id: str | None) -> dict | None:
    if not pool or not event_id:
        return None
    for row in reversed(list(getattr(pool, "event_history", None) or [])):
        if row.get("id") == event_id:
            return row
    for row in list(getattr(pool, "events", None) or []):
        if row.get("id") == event_id:
            return row
    return None


def post_event(console, fighter, opponent, result: str, method: str, pool, booked=None,
               old_rank: int | None = None) -> dict:
    """Resolve bonuses, ranking movement, rivalry and persistent event notes."""
    booked = booked or getattr(fighter, "booked_fight", None) or {}
    org = _org(fighter, booked)
    wc = str(booked.get("weight_class") or getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", ""))
    new_rank = rank_snapshot(fighter, pool, org, wc)
    rating = float(getattr(fighter, "performance_rating", 0.0) or 0.0)
    win = str(result).lower().startswith("w")
    level = importance(fighter, opponent, booked, bool(booked.get("title")))
    notes = []
    bonus_kind = None; bonus = 0
    if win and level in ("featured", "major", "championship") and rating >= 8.8:
        bonus_kind = "performance"; bonus = _bonus_amount(org, bonus_kind)
    elif level in ("major", "championship") and "decision" in str(method).lower() and rating >= 8.4:
        bonus_kind = "fight_of_night"; bonus = _bonus_amount(org, bonus_kind)
    if bonus:
        fighter.money += bonus
        flags = getattr(fighter, "story_flags", None)
        if not isinstance(flags, dict): fighter.story_flags = {}; flags = fighter.story_flags
        flags["performance_bonuses"] = int(flags.get("performance_bonuses", 0) or 0) + 1
        flags["bonus_money"] = int(flags.get("bonus_money", 0) or 0) + bonus
        label = "Performance bonus" if bonus_kind == "performance" else "Fight of the Night bonus"
        notes.append("%s +$%s" % (label, format(bonus, ",")))
        if pool is not None:
            pool.news.append("%s earns a %s after %s." % (fighter.name, label.lower(), org or "fight night"))
    if isinstance(old_rank, int) and isinstance(new_rank, int) and old_rank != new_rank:
        direction = "rises" if new_rank < old_rank else "falls"
        notes.append("Ranking %s #%s → #%s" % (direction, old_rank, new_rank))
        if pool is not None:
            pool.news.append("%s %s from #%s to #%s in %s %s." % (fighter.name, direction, old_rank, new_rank, org, wc))
    reasons = rivalry_after_bout(fighter, opponent, result, method)
    if reasons:
        notes.append("Rivalry: " + ", ".join(reasons))
    if booked.get("title") and pool is not None:
        champ = pool.belt_holder(org, wc) if hasattr(pool, "belt_holder") else None
        if champ is fighter:
            info = (getattr(pool, "belts", None) or {}).get(org + "|" + wc, {})
            notes.append("Champion · %s defense%s" % (int(info.get("defenses", 0) or 0), "" if int(info.get("defenses", 0) or 0) == 1 else "s"))
    row = _event_row(pool, booked.get("event_id"))
    if row is not None:
        if booked.get("title") and pool is not None and win:
            row.setdefault("title_changes", [])
            champ = pool.belt_holder(org, wc) if hasattr(pool, "belt_holder") else None
            if champ is fighter and not any(x.get("winner") == fighter.name and x.get("weight_class") == wc for x in row["title_changes"]):
                row["title_changes"].append({"weight_class": wc, "winner": fighter.name,
                                             "previous": getattr(opponent, "name", None)})
        row.setdefault("post_event", [])
        row["post_event"].append({
            "fighter": fighter.name, "result": result, "method": method,
            "rating": rating, "bonus": bonus, "bonus_kind": bonus_kind,
            "rank_before": old_rank, "rank_after": new_rank,
            "rivalry_reasons": reasons,
        })
        row["post_event"] = row["post_event"][-12:]
    if console and (notes or level in ("major", "championship")):
        console.header("POST-EVENT", org or "Fight night consequences")
        console.print("%s vs %s · %s · rating %.1f/10" % (result, opponent.name, method, rating))
        if notes:
            for note in notes: console.print("  • " + note)
        else:
            console.print("  • No major ranking or bonus consequence.")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.read_pause("post event", extra=0.1))("Press Enter to continue")
    return {"bonus": bonus, "bonus_kind": bonus_kind, "old_rank": old_rank,
            "new_rank": new_rank, "rivalry_reasons": reasons, "notes": notes}
