"""v1.38 living-career intelligence.

This module adds persistent career motives to NPCs and makes promotion identity
matter to matchmaking and player opportunities. It deliberately does not own
bookings, rankings or contracts; those remain with promotion_events/world,
booking and contracts respectively.
"""
from __future__ import annotations

import hashlib
import random


PROMOTION_PROFILES = {
    "UFC": {"label":"merit + star power", "merit":1.00, "stars":0.85, "protect":0.20, "activity":0.65, "tough":0.90, "regional":0.05},
    "PFL": {"label":"activity + record", "merit":0.85, "stars":0.35, "protect":0.30, "activity":1.00, "tough":0.70, "regional":0.10},
    "Bellator": {"label":"names + competitive fights", "merit":0.65, "stars":0.90, "protect":0.35, "activity":0.60, "tough":0.70, "regional":0.10},
    "BRAVE CF": {"label":"international prospects", "merit":0.75, "stars":0.40, "protect":0.55, "activity":0.70, "tough":0.55, "regional":0.45},
    "KSW": {"label":"stars + finishes", "merit":0.70, "stars":0.85, "protect":0.45, "activity":0.60, "tough":0.60, "regional":0.70},
    "Cage Warriors": {"label":"prospect builder", "merit":0.80, "stars":0.25, "protect":0.85, "activity":0.75, "tough":0.50, "regional":0.75},
    "Balkan Combat": {"label":"homegrown regional ladder", "merit":0.70, "stars":0.30, "protect":0.70, "activity":0.75, "tough":0.50, "regional":1.00},
    "LFA": {"label":"feeder + prospect tests", "merit":0.90, "stars":0.15, "protect":0.80, "activity":0.90, "tough":0.60, "regional":0.65},
    "Road FC": {"label":"action + regional names", "merit":0.65, "stars":0.55, "protect":0.45, "activity":0.85, "tough":0.70, "regional":0.85},
    "ARES FC": {"label":"European prospect builder", "merit":0.80, "stars":0.30, "protect":0.80, "activity":0.75, "tough":0.50, "regional":0.90},
    "ACA": {"label":"merit + hard matchmaking", "merit":0.95, "stars":0.20, "protect":0.20, "activity":0.75, "tough":1.00, "regional":0.85},
    "EFC": {"label":"regional development", "merit":0.70, "stars":0.30, "protect":0.70, "activity":0.80, "tough":0.50, "regional":1.00},
}

PERSONALITIES = ("ambitious", "loyal", "mercenary", "cautious", "action", "professional")


def profile(org: str) -> dict:
    return dict(PROMOTION_PROFILES.get(str(org or ""), {"label":"balanced", "merit":0.65, "stars":0.35, "protect":0.50, "activity":0.65, "tough":0.60, "regional":0.40}))


def _stable_index(f, n: int) -> int:
    raw = "%s|%s|%s" % (getattr(f, "fid", ""), getattr(f, "name", ""), getattr(f, "country", ""))
    digest = hashlib.md5(raw.encode("utf-8", "ignore")).hexdigest()
    return int(digest[:8], 16) % max(1, n)


def ensure(f) -> None:
    if not getattr(f, "career_personality", ""):
        f.career_personality = PERSONALITIES[_stable_index(f, len(PERSONALITIES))]
    if not isinstance(getattr(f, "career_log", None), list):
        f.career_log = []
    if not getattr(f, "career_goal", ""):
        f.career_goal = "develop" if not getattr(f, "pro_debut", False) else "activity"
    if not isinstance(getattr(f, "career_goal_week", None), int):
        f.career_goal_week = int(getattr(f, "week", 1) or 1)


def _rank(f) -> int:
    flags = getattr(f, "story_flags", None) or {}
    org = str(getattr(f, "organization", "") or "")
    n = flags.get("ufc_rank") if org == "UFC" else flags.get("org_rank")
    return int(n) if isinstance(n, int) and n > 0 else 99


def choose_goal(f, pool=None) -> str:
    ensure(f)
    if not getattr(f, "active", True):
        return "retired"
    age = int(getattr(f, "age", 25) or 25)
    idle = int(getattr(f, "idle_weeks", 0) or 0)
    streak = int(getattr(f, "current_streak", 0) or 0)
    rec = list(getattr(f, "pro_record", [0,0,0]) or [0,0,0])
    wins, losses = int(rec[0]), int(rec[1])
    if not getattr(f, "pro_debut", False):
        return "turn_pro" if wins >= 6 and age >= 19 else "develop"
    org = str(getattr(f, "organization", "") or "")
    champ = False
    if pool is not None and org and hasattr(pool, "belt_holder"):
        try: champ = pool.belt_holder(org, getattr(f, "weight_class", "")) is f
        except Exception: champ = False
    if champ:
        return "defend_belt"
    if age >= 36 and (streak <= -2 or losses >= wins):
        return "final_run"
    if streak <= -2:
        return "rebuild"
    if idle >= 12:
        return "activity"
    rank = _rank(f)
    # Regional standouts should not all become permanent local contenders.
    # A genuinely dominant non-champion can decide the next promotion matters
    # more than waiting forever for another local booking.  Less-proven top-five
    # names still chase the belt where they are.
    if wins >= 10 and streak >= 4 and org not in ("UFC", "PFL", "Bellator"):
        return "move_up"
    if wins >= 8 and streak >= 3 and org not in ("UFC", "PFL", "Bellator") and rank > 3:
        return "move_up"
    if rank <= 5 and streak >= 1:
        return "title_chase"
    if wins >= 7 and streak >= 2 and org not in ("UFC", "PFL", "Bellator"):
        return "move_up"
    if wins + losses <= 8 and age <= 29:
        return "develop"
    return "rank_climb"


def update_goal(f, pool=None, week: int | None = None) -> bool:
    ensure(f)
    new = choose_goal(f, pool)
    old = getattr(f, "career_goal", "")
    if new == old:
        return False
    f.career_goal = new
    f.career_goal_week = int(week if week is not None else getattr(pool, "week", getattr(f, "week", 1)) or 1)
    row = {"week": f.career_goal_week, "from": old, "to": new}
    f.career_log = (list(getattr(f, "career_log", None) or []) + [row])[-12:]
    return True


def tick_world(pool) -> list[str]:
    """Refresh motives. Behaviour remains owned by the normal world systems."""
    week = int(getattr(pool, "week", 0) or 0)
    lines = []
    changed = 0
    for f in list(getattr(pool, "fighters", []) or []):
        if not getattr(f, "active", True) or getattr(f, "is_player", False):
            continue
        ensure(f)
        # Reassess on a rolling cadence, plus immediately after strong form swings.
        due = week - int(getattr(f, "career_goal_week", 0) or 0) >= 8
        streak = abs(int(getattr(f, "current_streak", 0) or 0))
        if due or streak >= 3:
            if update_goal(f, pool, week):
                changed += 1
        goal = getattr(f, "career_goal", "")
        if goal in ("activity", "title_chase", "move_up", "final_run"):
            f.npc_wants_fight = True
        elif goal == "rebuild" and int(getattr(f, "idle_weeks", 0) or 0) >= 6:
            f.npc_wants_fight = True
    if changed and week % 8 == 0:
        lines.append("Career desks shift: %s fighters change priorities this month." % changed)
    return lines


def transfer_priority(f, target: str, current: str, pool=None) -> float:
    """Positive score = this move fits the fighter's career/personality."""
    ensure(f)
    from . import orgs
    cur_tier = int((orgs.ORGS.get(current) or {}).get("tier", 4))
    new_tier = int((orgs.ORGS.get(target) or {}).get("tier", 4))
    goal = getattr(f, "career_goal", "")
    p = getattr(f, "career_personality", "professional")
    out = 0.0
    if goal == "move_up": out += (new_tier-cur_tier) * 8.0
    if goal == "title_chase" and new_tier >= cur_tier: out += 7.0
    if goal == "rebuild" and new_tier <= cur_tier: out += 5.0
    if p == "ambitious": out += (new_tier-cur_tier) * 5.0
    elif p == "loyal" and current: out -= 8.0 if target != current else 0.0
    elif p == "mercenary":
        purse = (orgs.ORGS.get(target) or {}).get("purse", (0,0)); out += sum(purse)/3500.0
    elif p == "action": out += profile(target).get("activity", .5) * 5.0
    return out


def matchup_adjustment(pool, org: str, wc: str, a, b, intent: str) -> float:
    """Cost adjustment used by the existing card builder (lower is preferred)."""
    pr = profile(org)
    ensure(a); ensure(b)
    ga, gb = getattr(a, "career_goal", ""), getattr(b, "career_goal", "")
    adj = 0.0
    roles = set()
    try:
        from .promotion_events import _career_role
        roles = {_career_role(pool, org, wc, a), _career_role(pool, org, wc, b)}
    except Exception:
        pass
    if "prospect" in roles and "contender" in roles:
        adj += 35.0 * pr.get("protect", .5)
    if roles == {"prospect", "gatekeeper"}:
        adj -= 16.0 * pr.get("protect", .5)
    if roles == {"contender"} or ("contender" in roles and intent == "title_eliminator"):
        adj -= 15.0 * pr.get("merit", .5)
    if ga == "rebuild" or gb == "rebuild":
        if intent == "rebuild": adj -= 18.0
        elif "contender" in roles: adj += 25.0
    if ga == "activity" or gb == "activity":
        adj -= min(10.0, pr.get("activity", .5) * 8.0)
    fame = int(getattr(a, "fame", 0) or 0) + int(getattr(b, "fame", 0) or 0)
    adj -= min(10.0, fame * .03 * pr.get("stars", .3))
    # Hard-matchmaking promotions are less frightened by score gaps.
    try:
        gap = abs(float(pool._rank_score(a)) - float(pool._rank_score(b)))
        adj -= min(12.0, gap * .04 * pr.get("tough", .6))
    except Exception:
        pass
    return adj


def opponent_score(fighter, cand, org: str, base_gap: float) -> float:
    """Player-offer candidate score. Lower wins."""
    pr = profile(org); ensure(fighter); ensure(cand)
    my = list(getattr(fighter, "pro_record", [0,0,0]) or [0,0,0]); his = list(getattr(cand, "pro_record", [0,0,0]) or [0,0,0])
    bouts = sum(my[:3]); hbouts = sum(his[:3])
    score = float(base_gap)
    # Prospect builders prefer sensible experience tests; ACA/UFC tolerate tougher jumps.
    if bouts <= 8:
        score += max(0, hbouts-bouts-2) * (2.4 * pr.get("protect", .5))
    if pr.get("merit", .5) > .75:
        score += abs(int(his[0])-int(my[0])) * .30
    if pr.get("stars", .3) > .6:
        score -= min(5.0, int(getattr(cand, "fame", 0) or 0) * .04)
    if getattr(fighter, "career_goal", "") == "rebuild":
        score += max(0, int(his[0])-int(my[0])) * 1.4
    return score



def offer_interest_score(fighter, org: str) -> float:
    """How strongly a promotion wants to be in the player's inbox.

    Eligibility still belongs to orgs.eligible_orgs()/contracts.  This merely
    ranks already-legal destinations, combining sporting merit, star power,
    activity, regional fit and the relationships the existing People system
    has accumulated.  Higher is more interested.
    """
    ensure(fighter)
    pr = profile(org)
    rec = list(getattr(fighter, "pro_record", [0,0,0]) or [0,0,0])
    wins, losses = int(rec[0]), int(rec[1])
    bouts = max(1, wins + losses + int(rec[2] if len(rec) > 2 else 0))
    win_rate = wins / float(bouts)
    streak = int(getattr(fighter, "current_streak", 0) or 0)
    fame = int(getattr(fighter, "fame", 0) or 0)
    idle = int(getattr(fighter, "idle_weeks", 0) or 0)
    score = 0.0

    # Sporting case versus marketability.  Profiles decide how much each org
    # values the same fighter rather than giving every organization one ladder.
    score += (wins * 1.15 + max(0, streak) * 2.0 + win_rate * 7.0) * float(pr.get("merit", .5))
    score += fame * .16 * float(pr.get("stars", .3))
    score += min(20, idle) * .18 * float(pr.get("activity", .5))

    # Prospect builders prefer young/low-mileage winners; hard-matchmaking
    # promotions are less concerned with protecting an undefeated record.
    age = int(getattr(fighter, "age", 25) or 25)
    if bouts <= 9 and age <= 29:
        score += 5.0 * float(pr.get("protect", .5))
    if losses == 0 and bouts >= 4:
        score += 2.0 * float(pr.get("protect", .5))
    score += max(0, losses - 1) * .8 * float(pr.get("tough", .5))

    try:
        from . import orgs as _orgs
        if _orgs.home_org(getattr(fighter, "country", "") or "") == org:
            score += 7.0 * float(pr.get("regional", .5))
    except Exception:
        pass

    # Existing promoter/matchmaker rapport now affects access as well as purse
    # and trap fights.  It is intentionally bounded so relationships matter
    # without overriding the sporting gates.
    try:
        from . import people
        prom = people.promoter_for(org)
        mm = people.matchmaker_for(org)
        if prom:
            score += (people.rapport(fighter, prom.id) - 50) * .10
        if mm:
            score += (people.rapport(fighter, mm.id) - 50) * .08
    except Exception:
        pass
    return round(score, 4)


def rank_offer_orgs(fighter, org_names: list[str]) -> list[str]:
    """Rank eligible organizations while retaining enough week-to-week variety."""
    scored = []
    for org in org_names or []:
        # Small random desk noise prevents the inbox becoming a deterministic
        # menu while keeping the political/sporting signal dominant.
        scored.append((offer_interest_score(fighter, org) + random.uniform(-2.5, 2.5), org))
    scored.sort(reverse=True)
    return [org for _score, org in scored]

def _opportunity(fighter, offer: dict, pool=None) -> dict:
    org = str(offer.get("org") or "")
    opp = offer.get("opponent")
    rec = list(getattr(fighter, "pro_record", [0,0,0]) or [0,0,0])
    my_wins = int(rec[0]); streak = int(getattr(fighter, "current_streak", 0) or 0)
    rank = _rank(fighter)
    role = str(offer.get("matchup_role") or "")
    label, risk, upside = "Activity fight", "normal", 1
    if offer.get("title"):
        label, risk, upside = "Championship opportunity", "elite", 5
    elif offer.get("short_notice") or str(offer.get("tag") or "").lower().startswith("short"):
        label, risk, upside = "Short-notice jump", "high", 4
    elif rank <= 6 and streak >= 1:
        label, risk, upside = "Contender test", "high", 4
        offer["matchup_role"] = role or "contender_test"
    elif streak <= -2:
        label, risk, upside = "Rebuild fight", "managed", 2
        offer["matchup_role"] = role or "rebuild"
    elif my_wins <= 5:
        label, risk, upside = "Prospect showcase", "managed", 2
        offer["matchup_role"] = role or "prospect_showcase"
    elif opp is not None and int((getattr(opp, "pro_record", [0]) or [0])[0]) >= my_wins + 2:
        label, risk, upside = "Step-up fight", "high", 4
        offer["matchup_role"] = role or "step_up"
    if getattr(fighter, "country", "") == getattr(opp, "country", "") and label == "Activity fight":
        label, upside = "Home-market feature", 2
    pr = profile(org)
    offer["career_opportunity"] = label
    offer["career_risk"] = risk
    offer["career_upside"] = upside
    offer["promotion_identity"] = pr.get("label", "balanced")
    why = offer.get("why")
    if isinstance(why, str): why = [why]
    why = list(why or [])
    why.append("%s books around %s" % (org, pr.get("label", "balanced")))
    offer["why"] = why[:5]
    return offer


def decorate_player_offers(fighter, offers: list, pool=None) -> list:
    ensure(fighter)
    out = [_opportunity(fighter, dict(o), pool) for o in (offers or [])]
    # Avoid an inbox full of identical generic activity fights when possible.
    seen = set()
    for off in out:
        label = off.get("career_opportunity")
        if label in seen and label == "Activity fight":
            off["career_opportunity"] = "Promotion opportunity"
        seen.add(off.get("career_opportunity"))
    return out


def resolve_player_opportunity(fighter, meta: dict, outcome: str, finish: str = "") -> str:
    label = str((meta or {}).get("career_opportunity") or "")
    if not label:
        return ""
    won = str(outcome).startswith("win")
    if not won:
        if label in ("Step-up fight", "Contender test", "Short-notice jump"):
            return "%s: the risk did not pay off, but the loss is understood in context." % label
        return ""
    fame = rep = legacy = 0
    if label == "Championship opportunity": legacy = 4
    elif label == "Short-notice jump": fame, rep, legacy = 3, 4, 2
    elif label == "Contender test": fame, rep, legacy = 2, 5, 2
    elif label == "Step-up fight": fame, rep, legacy = 2, 4, 1
    elif label == "Prospect showcase": fame, rep = (2 if finish else 1), 2
    elif label == "Home-market feature": fame, rep = 2, 1
    elif label == "Rebuild fight": rep = 2
    else: rep = 1
    fighter.fame = min(100, int(getattr(fighter, "fame", 0) or 0) + fame)
    fighter.reputation = int(getattr(fighter, "reputation", 0) or 0) + rep
    fighter.legacy_score = int(getattr(fighter, "legacy_score", 0) or 0) + legacy
    flags = getattr(fighter, "story_flags", None)
    if isinstance(flags, dict):
        flags["last_career_opportunity"] = {"week": int(getattr(fighter, "week", 0) or 0), "label": label, "won": True}
        if label == "Contender test": flags["earned_contender_test_week"] = int(getattr(fighter, "week", 0) or 0)
    gains = []
    if fame: gains.append("fame +%s" % fame)
    if rep: gains.append("reputation +%s" % rep)
    if legacy: gains.append("legacy +%s" % legacy)
    return "%s paid off%s." % (label, " — " + ", ".join(gains) if gains else "")
