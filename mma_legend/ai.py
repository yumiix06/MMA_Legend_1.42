"""Weekly brains for events, NPCs, promotions, and managers.

None of this talks to an external model. It is scored intent:
what a gym, a matchmaker, or an agent would actually push this week.
"""
from __future__ import annotations

import random
from typing import Optional


# ------------------------------------------------------------------
# Event AI
# ------------------------------------------------------------------

_LIFE = ("party", "club", "nightlife", "hangover", "date", "family")
_GYM = ("coach", "gym", "spar", "training", "camp", "technique")
_MONEY = ("sponsor", "job", "rent", "broke", "bill", "endorsement")
_MEDIA = ("press", "podcast", "interview", "media", "camera")
_INJ = ("injur", "physio", "doctor", "hospital", "scan")


def _blob(event: dict) -> str:
    return ((event.get("title") or "") + " " + (event.get("category") or "") + " "
            + (event.get("description") or "")).lower()


def event_score(fighter, event: dict, ctx: dict) -> float:
    """Higher = more likely this week. Context beats raw chance."""
    from . import events as ev
    base = ev._weight(event, ctx)
    text = _blob(event)
    energy = int(ctx.get("energy") or 50)
    health = int(ctx.get("health") or 80)
    money = int(ctx.get("money") or 0)
    fame = int(ctx.get("fame") or 0)
    last = str(ctx.get("last") or "")
    camp = bool(ctx.get("camp"))
    pro = bool(ctx.get("pro"))

    if any(w in text for w in _LIFE):
        if camp or energy < 35 or health < 40:
            base *= 0.15
        elif energy > 70 and not camp:
            base *= 1.25
    if any(w in text for w in _GYM):
        if last.upper().startswith("L") or energy < 45:
            base *= 1.6
        if camp:
            base *= 1.3
    if any(w in text for w in _MONEY):
        if money < 0:
            base *= 3.0
        elif money < 80:
            base *= 2.2
        elif money > 800:
            base *= 0.4
    booked = bool(getattr(fighter, "booked_fight", None) or ctx.get("camp"))
    if booked and any(w in text for w in _GYM):
        base *= 1.5
    if booked and any(w in text for w in _LIFE):
        base *= 0.2
    if any(w in text for w in _MEDIA):
        if not pro and fame < 8:
            base *= 0.05
        elif fame >= 12:
            base *= 1.4
    if any(w in text for w in _INJ):
        if health < 55:
            base *= 2.0
        else:
            base *= 0.35
    if camp and "party" in text:
        base *= 0.05
    flags = getattr(fighter, "story_flags", None) or {}
    cat = str(event.get("category") or "life").lower()
    if str(flags.get("last_event_category") or "").lower() == cat:
        streak = max(1, int(flags.get("event_category_streak", 1) or 1))
        base *= max(0.22, 0.55 ** min(3, streak))
    return max(0.001, base)


def pick_event(fighter) -> Optional[dict]:
    from . import events as ev
    from . import data
    ctx = ev.context_pack(fighter)
    packs = data.all_events(newest_first=True)
    pool = [e for e in packs if ev.eligible(fighter, e, ctx)]
    if not pool:
        return None
    # Quiet weeks are still a thing. Hurt / broke / post-loss weeks fire more.
    hunger = 0.18
    if int(ctx.get("health") or 80) < 50:
        hunger += 0.12
    if int(ctx.get("money") or 0) < 40:
        hunger += 0.10
    if str(ctx.get("last") or "").upper().startswith("L"):
        hunger += 0.08
    trigger_roll = random.random()
    if trigger_roll > hunger:
        try:
            from . import telemetry
            telemetry.decision("event_ai", choice=None, reason="quiet_week", hunger=round(hunger, 3),
                               trigger_roll=round(trigger_roll, 4), eligible=len(pool))
        except Exception:
            pass
        return None
    weights = [event_score(fighter, e, ctx) for e in pool]
    pick = random.choices(pool, weights=weights, k=1)[0]
    fighter.story_flags["last_event_ai"] = pick.get("id") or pick.get("title")
    try:
        from . import telemetry
        ranked = sorted(zip(pool, weights), key=lambda ew: ew[1], reverse=True)[:6]
        telemetry.decision(
            "event_ai", choice=pick.get("id") or pick.get("title"), reason="weighted_context",
            hunger=round(hunger, 3), trigger_roll=round(trigger_roll, 4), eligible=len(pool),
            top=[{"id": e.get("id"), "title": e.get("title"), "score": round(float(w), 4)} for e, w in ranked])
    except Exception:
        pass
    return pick


# ------------------------------------------------------------------
# NPC AI
# ------------------------------------------------------------------

def npc_intent(f) -> str:
    try:
        from . import living_careers
        living_careers.ensure(f)
        goal = str(getattr(f, "career_goal", "") or "")
    except Exception:
        goal = ""
    age = int(getattr(f, "age", 24) or 24)
    health = int(getattr(f, "health", 80) or 80)
    energy = int(getattr(f, "energy", 70) or 70)
    idle = int(getattr(f, "idle_weeks", 0) or 0)
    rec = f.pro_record if getattr(f, "pro_debut", False) else f.amateur_record
    wins, losses = int(rec[0]), int(rec[1])
    traits = " ".join(str(x) for x in (getattr(f, "traits", None) or []))
    if age >= 38 and losses > wins:
        return "retire"
    if health < 35 or ("clinical" in traits and health < 50):
        return "rehab"
    if energy < 30:
        return "rest"
    if goal in ("title_chase", "final_run") and idle >= 4:
        return "push_fight"
    if goal == "activity" and idle >= 3:
        return "take_fight"
    if goal == "rebuild" and idle < 6:
        return "train"
    if goal in ("develop", "move_up") and energy >= 55 and random.random() < 0.45:
        return "train_hard"
    if "hot-headed" in traits and idle >= 4:
        return "take_fight"
    if idle >= 10 and getattr(f, "pro_debut", False):
        return "push_fight"
    if idle >= 6:
        return "take_fight"
    if wins >= losses + 3 and random.random() < 0.25:
        return "train_hard"
    return "train"


def apply_npc_intent(f, intent: str) -> None:
    from . import constants as C
    f.npc_intent = intent
    if intent == "retire":
        # World sim owns the actual retirement so we do not double-kill the pool.
        f.npc_intent = "retire"
        return
    if intent in ("take_fight", "push_fight"):
        f.npc_wants_fight = True
        return
    if intent == "rehab":
        f.health = min(100, int(f.health) + 8)
        f.energy = min(100, int(f.energy) + 6)
        return
    if intent == "rest":
        f.energy = min(100, int(f.energy) + 10)
        return
    if intent == "train_hard":
        s = random.choice(C.SKILLS)
        setattr(f, s, min(95, getattr(f, s) + 1))
        f.energy = max(20, int(f.energy) - 4)
        return
    if intent == "train":
        if random.random() < 0.35:
            s = random.choice(C.SKILLS)
            setattr(f, s, min(92, getattr(f, s) + 1))
        f.energy = max(25, min(100, int(f.energy) - 1 + random.randint(0, 3)))


def tick_npcs(pool, limit: int = 80) -> list:
    """Advance a slice of the roster. Returns short news lines."""
    news = []
    roster = [f for f in getattr(pool, "fighters", []) or [] if getattr(f, "active", True)]
    random.shuffle(roster)
    retired = 0
    fights_wanted = 0
    for f in roster[:limit]:
        intent = npc_intent(f)
        apply_npc_intent(f, intent)
        if intent == "retire":
            retired += 1
            if retired <= 2:
                news.append("%s walks away." % f.name)
        elif intent in ("take_fight", "push_fight"):
            fights_wanted += 1
    if fights_wanted:
        news.append("%s fighters around the world are asking for dates." % fights_wanted)
    return news


# ------------------------------------------------------------------
# Promotion AI
# ------------------------------------------------------------------

def promo_intent(org: str, roster: list, wc: str, champ=None) -> str:
    try:
        from . import living_careers
        prof = living_careers.profile(org)
    except Exception:
        prof = {"merit": .5, "protect": .5, "activity": .5}
    same = [f for f in roster if getattr(f, "weight_class", None) == wc]
    idle = [f for f in same if int(getattr(f, "idle_weeks", 0) or 0) >= 8]
    hot = [f for f in same if int(getattr(f, "current_streak", 0) or 0) >= 3]
    if champ is not None and champ in same and int(getattr(champ, "idle_weeks", 0) or 0) >= 12:
        return "title_defense"
    if hot and idle and float(prof.get("protect", .5)) >= .55:
        return "protect_streak"
    if hot and (org in ("UFC", "PFL", "Bellator", "KSW") or float(prof.get("merit", .5)) >= .80):
        return "title_eliminator"
    if same and float(prof.get("protect", .5)) >= .70:
        return "prospect_showcase"
    if random.random() < 0.2:
        return "rematch"
    return "short_notice"


def tick_promos(pool) -> list:
    """Org desks move. Some unsigned amateurs get a look."""
    from . import orgs
    news = []
    by_org = {}
    for f in getattr(pool, "fighters", []) or []:
        if not getattr(f, "active", True):
            continue
        org = getattr(f, "organization", None) or ""
        if org:
            by_org.setdefault(org, []).append(f)
    # Sign a couple of local amateurs onto regional books
    unsigned = [f for f in pool.fighters
                if f.active and not f.pro_debut and not getattr(f, "organization", None)]
    random.shuffle(unsigned)
    signed = 0
    for f in unsigned[:40]:
        if signed >= 2:
            break
        if int((f.amateur_record or [0, 0, 0])[0]) < 4:
            continue
        if random.random() > 0.12:
            continue
        home = orgs.home_org(getattr(f, "country", "") or "")
        f.organization = home
        signed += 1
        news.append("%s offers %s a developmental deal." % (home, f.name))
    # Idle signed fighters get a public nudge
    nudged = 0
    for org, roster in by_org.items():
        for f in roster:
            if int(getattr(f, "idle_weeks", 0) or 0) >= 14 and random.random() < 0.2:
                news.append("%s wants %s back on a card." % (org, f.name))
                nudged += 1
                if nudged >= 2:
                    break
        if nudged >= 2:
            break
    return news


def decorate_offer(fighter, offer: dict) -> dict:
    """Promoter + manager flavor on a live offer."""
    from . import people
    org = offer.get("org") or ""
    promo = people.promoter_for(org)
    mm = people.matchmaker_for(org)
    why_raw = offer.get("why")
    why = [why_raw] if isinstance(why_raw, str) and why_raw else list(why_raw or [])
    if promo and promo.quirk == "rewards_finishes" and "W" in "".join(getattr(fighter, "recent_results", []) or [])[-3:]:
        offer["purse_win"] = int(offer.get("purse_win") or 100) + 40
        why.append("%s likes the finishes" % promo.name)
    if mm and mm.quirk == "style_avoid":
        why.append("%s is matching styles carefully" % mm.name)
    if promo and promo.quirk == "rewards_activity" and int(getattr(fighter, "idle_weeks", 0) or 0) >= 8:
        if not offer.get("title"):
            offer["tag"] = "short notice"
            offer["date_week"] = int(getattr(fighter, "week", 1)) + 2
            why.append("%s wants you active" % promo.name)
    offer["why"] = why[:4]
    return offer


# ------------------------------------------------------------------
# Manager AI
# ------------------------------------------------------------------

def manager_advice(fighter) -> str:
    mgr = None
    try:
        from . import people
        mgr = people.current_manager(fighter)
    except Exception:
        pass
    if mgr is None:
        if getattr(fighter, "pro_debut", False):
            return "No manager. Regional dates will stay small."
        wins = int((fighter.amateur_record or [0, 0, 0])[0])
        if wins >= 6 or "national_bronze" in (fighter.amateur_titles or []):
            return "Amateur desks know the name. A manager still waits on a pro debut."
        return "Amateur. A manager is not sniffing yet."
    energy = int(getattr(fighter, "energy", 70) or 70)
    health = int(getattr(fighter, "health", 80) or 80)
    booked = getattr(fighter, "booked_fight", None)
    rec = fighter.pro_record if fighter.pro_debut else fighter.amateur_record
    name = mgr.name
    if health < 40:
        return "%s: sit this month. You are hurt." % name
    if energy < 28:
        return "%s: rest week. Gas is gone." % name
    if booked:
        from .systems15 import opp_label
        return "%s: camp for %s. Do not take extras." % (name, opp_label(booked))
    if int(rec[1]) >= int(rec[0]) + 2:
        return "%s: reset fight. Similar experience, low upset risk — no trap fights." % name
    if mgr.quirk in ("aggressive", "brand") and int(getattr(fighter, "fame", 0) or 0) < 12:
        return "%s: seek a higher-visibility fight, but stay inside your experience band." % name
    if mgr.quirk in ("analytical", "loyal"):
        return "%s: prioritize résumé fit and recovery over headline value." % name
    return "%s: you are free. I am calling matchmakers." % name


def filter_offers(fighter, offers: list) -> list:
    """Manager kills obviously stupid paper."""
    try:
        from . import people
        mgr = people.current_manager(fighter)
    except Exception:
        mgr = None
    if not offers:
        return offers
    kept = []
    for off in offers:
        opp = off.get("opponent")
        rec = getattr(opp, "pro_record", [0, 0, 0]) if opp is not None else [0, 0, 0]
        my = fighter.pro_record if fighter.pro_debut else fighter.amateur_record
        if off.get("title"):
            kept.append(off)
            continue
        too_heavy = fighter.pro_debut and int(rec[0]) > int(my[0]) + 6
        if too_heavy and mgr and mgr.quirk in ("analytical", "loyal", "protects_prospects"):
            continue
        if mgr and mgr.quirk == "style_avoid" and opp is not None:
            if str(getattr(opp, "style", "") or "") == str(getattr(fighter, "style", "") or ""):
                continue
        if mgr and mgr.quirk == "wrestle_bias" and opp is not None:
            st = str(getattr(opp, "style", "") or "").lower()
            if not any(w in st for w in ("wrest", "sambo", "judo")) and len(offers) > 1:
                continue
        kept.append(off)
    return kept or offers[:1]


def tick_manager(fighter) -> str:
    note = manager_advice(fighter)
    fighter.story_flags["manager_note"] = note
    return note
