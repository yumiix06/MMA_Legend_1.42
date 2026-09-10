"""Ten promotions. Rosters live on Fighter.organization. Offers go through the manager."""
from __future__ import annotations

import random

from . import people

ORGS = {
    "UFC": {"tier": 10, "region": "World", "purse": (9000, 16000), "weeks": (8, 10)},
    "PFL": {"tier": 8, "region": "North America", "purse": (3500, 7000), "weeks": (7, 9)},
    "Bellator": {"tier": 8, "region": "North America", "purse": (3200, 6500), "weeks": (7, 9)},
    "BRAVE CF": {"tier": 7, "region": "Middle East", "purse": (1800, 3500), "weeks": (6, 8)},
    "KSW": {"tier": 6, "region": "Europe", "purse": (1600, 3000), "weeks": (6, 8)},
    "Cage Warriors": {"tier": 5, "region": "Europe", "purse": (800, 1600), "weeks": (5, 7)},
    "Balkan Combat": {"tier": 5, "region": "Balkans", "purse": (600, 1200), "weeks": (5, 7)},
    "LFA": {"tier": 4, "region": "North America", "purse": (400, 900), "weeks": (5, 7)},
    "Road FC": {"tier": 5, "region": "Asia", "purse": (700, 1400), "weeks": (5, 7)},
    "ARES FC": {"tier": 5, "region": "Europe", "purse": (700, 1300), "weeks": (5, 7)},
    "ACA": {"tier": 6, "region": "Russia", "purse": (1400, 2800), "weeks": (6, 8)},
    "EFC": {"tier": 5, "region": "Africa", "purse": (600, 1400), "weeks": (5, 7)},
}

MAJORS = ("UFC", "PFL", "Bellator")
REGIONAL_HOME = {
    "Bulgaria": "Balkan Combat", "Serbia": "Balkan Combat", "Croatia": "Balkan Combat",
    "Greece": "Balkan Combat", "Romania": "Balkan Combat", "North Macedonia": "Balkan Combat",
    "USA": "LFA", "Canada": "LFA", "Mexico": "LFA",
    "UK": "Cage Warriors", "Ireland": "Cage Warriors", "England": "Cage Warriors",
    "Poland": "KSW", "France": "ARES FC", "Germany": "ARES FC",
    "South Korea": "Road FC", "Japan": "Road FC", "China": "Road FC",
    "Thailand": "Road FC", "Philippines": "Road FC", "Indonesia": "Road FC",
    "Mongolia": "Road FC",
    "Bahrain": "BRAVE CF", "UAE": "BRAVE CF",
    "Turkey": "BRAVE CF", "India": "BRAVE CF",
    "Russia": "ACA", "Belarus": "ACA", "Kazakhstan": "ACA", "Uzbekistan": "ACA",
    "Ukraine": "ACA", "Georgia": "ACA", "Armenia": "ACA", "Iran": "ACA",
    "South Africa": "EFC", "Nigeria": "EFC", "Ghana": "EFC", "Cameroon": "EFC",
    "Egypt": "EFC", "Morocco": "EFC", "Senegal": "EFC",
    "Netherlands": "Cage Warriors", "Sweden": "Cage Warriors", "Norway": "Cage Warriors",
    "Denmark": "Cage Warriors", "Iceland": "Cage Warriors", "Finland": "Cage Warriors",
    "Italy": "ARES FC", "Spain": "ARES FC", "Portugal": "ARES FC",
    "Austria": "ARES FC", "Czech Republic": "KSW", "Hungary": "KSW",
    "Brazil": "LFA", "Argentina": "LFA", "Colombia": "LFA", "Chile": "LFA",
    "Peru": "LFA", "Venezuela": "LFA", "Cuba": "LFA",
    "Australia": "LFA", "New Zealand": "LFA",
}


def home_org(country: str) -> str:
    return REGIONAL_HOME.get(country or "", "LFA")


def dominance(fighter) -> float:
    rec = fighter.pro_record or [0, 0, 0]
    w, l = int(rec[0]), int(rec[1])
    recent = list(getattr(fighter, "recent_results", None) or [])
    streak = 0
    for x in reversed(recent):
        if str(x).upper().startswith("W"):
            streak += 1
        else:
            break
    ratio = w / max(1, w + l)
    return w * 1.2 + streak * 2.5 + ratio * 8 + int(getattr(fighter, "fame", 0) or 0) * 0.15


def direct_ufc_chance(fighter) -> float:
    """A cold call straight from the regional scene into the UFC.

    This should feel rare, because it is rare. It needs a real record, a real
    win rate, genuine fame, and it is still a long shot. The ordinary route is
    Contender Series.
    """
    fame = int(getattr(fighter, "fame", 0) or 0)
    dom = dominance(fighter)
    rec = fighter.pro_record or [0, 0, 0]
    w, l = int(rec[0]), int(rec[1])
    # Hard gates first.
    if w < 9 or l > 2:
        return 0.0
    if fame < 30:
        return 0.0
    if int(getattr(fighter, "promotion_tier", 0) or 0) < 6:
        return 0.0
    # Must be on a real run, not just an accumulated record.
    streak = 0
    for x in reversed(list(getattr(fighter, "recent_results", None) or [])):
        if str(x).upper().startswith("W"):
            streak += 1
        else:
            break
    if streak < 4:
        return 0.0
    base = ((fame - 30) / 100.0) ** 1.5 * 0.22
    base += min(0.05, max(0.0, dom - 22) * 0.004)
    if getattr(fighter, "manager_id", None) or getattr(fighter, "manager", None):
        base += 0.02
    return max(0.0, min(0.12, base))


def eligible_orgs(fighter) -> list:
    if not getattr(fighter, "pro_debut", False):
        return []
    from . import booking
    w = int((fighter.pro_record or [0])[0])
    fame = int(getattr(fighter, "fame", 0) or 0)
    dom = dominance(fighter)
    cur = getattr(fighter, "organization", "") or ""
    room = booking.current_room(fighter)
    out = []
    home = home_org(getattr(fighter, "country", "") or "")
    # 0-0 kids do not walk into an exclusive regional deal.
    if w < 2:
        return []
    # Debut is hometown regional only. Majors need a real pro record.
    out.append(home)
    if home != "LFA":
        out.append("LFA")
    if room in ("regional", "national", "mid", "dwcs", "ufc") and w >= 3:
        out += ["Cage Warriors", "ARES FC", "Road FC", "Balkan Combat"]
    if room in ("national", "mid", "dwcs", "ufc") and w >= 8 and fame >= 12:
        out += ["KSW", "BRAVE CF", "ACA", "EFC"]
    if room in ("mid", "dwcs", "ufc") and w >= 12 and fame >= 18:
        out += ["PFL", "Bellator"]
    # UFC is never a walk-up from local/regional. DWCS door or already signed.
    if room in ("dwcs", "ufc"):
        out.append("UFC")
    seen = []
    for o in out:
        if o in ORGS and o not in seen:
            seen.append(o)
    return seen


def make_offer(fighter, org_id: str, pool=None) -> dict:
    from . import booking
    offer = booking.build_offer(fighter, pool=pool, org_id=org_id)
    offer["org"] = org_id
    spec = ORGS.get(org_id) or {}
    if spec.get("purse"):
        lo, hi = spec["purse"]
        win = random.randint(lo, hi)
        win = int(win * people.manager_purse_multiplier(fighter))
        win = int(win * people.promoter_purse_multiplier(fighter, org_id))
        if dominance(fighter) >= 18:
            win = int(win * 1.15)
        offer["purse_win"] = max(40, win)
        offer["purse_show"] = max(40, int(win * 0.20))
        delay = random.randint(*spec.get("weeks", (5, 7)))
        if offer.get("tag") != "short notice":
            offer["date_week"] = fighter.week + delay
    if pool is not None:
        try:
            from . import promotion_events
            offer = promotion_events.offer_slot(pool, fighter, offer)
        except Exception:
            pass
    return offer


def stamp_title(fighter, offer: dict, pool=None) -> dict:
    """If this date is a title shot, lock opponent + purse + flag."""
    from . import identity
    shot = identity.title_shot(fighter, pool)
    if not shot:
        return offer
    if str(offer.get("org") or "") != shot["org"]:
        return offer
    opp = shot.get("opponent")
    if opp is None:
        return offer
    offer["opponent"] = opp
    offer["opponent_id"] = getattr(opp, "fid", None)
    offer["weight_class"] = shot.get("wc") or getattr(fighter, "fight_weight_class", None) or fighter.weight_class
    offer["title"] = True
    offer["tag"] = "title"
    if shot["role"] == "defense":
        offer["why"] = "title defense"
    elif shot["role"] == "double_champ":
        offer["why"] = "two-division championship superfight"
        offer["double_champ"] = True
        offer["superfight"] = True
    else:
        offer["why"] = "title fight"
    offer["title_role"] = shot["role"]
    win = int(offer.get("purse_win") or 400)
    offer["purse_win"] = int(win * 1.35)
    offer["purse_show"] = max(40, int(offer["purse_win"] * 0.22))
    flags = getattr(fighter, "story_flags", None)
    if isinstance(flags, dict):
        flags["title_offer_week"] = int(getattr(fighter, "week", 1) or 1)
    return offer


def inbox(fighter, n: int = 3, pool=None) -> list:
    orgs = eligible_orgs(fighter)
    if not orgs:
        return []
    # Promotions do not all value the same fighter equally.  Sporting merit,
    # star power, regional fit and existing promoter/matchmaker rapport rank
    # the eligible desks; a little noise inside rank_offer_orgs keeps weekly
    # inboxes from becoming deterministic.
    try:
        from . import living_careers
        orgs = living_careers.rank_offer_orgs(fighter, orgs)
    except Exception:
        random.shuffle(orgs)
    extra = 1 if (getattr(fighter, "manager_id", None) or getattr(fighter, "manager", None)) else 0
    picks = orgs[: min(n + extra, len(orgs))]
    # Home org first when a title date is live
    from . import identity
    shot = identity.title_shot(fighter, pool)
    if shot and shot["org"] in picks:
        picks = [shot["org"]] + [o for o in picks if o != shot["org"]]
    elif shot and shot["org"] not in picks:
        picks = [shot["org"]] + picks
    offers = [make_offer(fighter, o, pool=pool) for o in picks]
    offers = [stamp_title(fighter, o, pool=pool) for o in offers]
    # Contract clauses are part of the offer economics, so apply them after
    # title stamping (which can increase purse) and before manager filtering.
    try:
        from . import contracts
        offers = [contracts.apply_offer_clauses(fighter, o) for o in offers]
    except Exception:
        pass
    try:
        from . import ai
        offers = [ai.decorate_offer(fighter, o) for o in offers]
        offers = ai.filter_offers(fighter, offers)
    except Exception:
        pass
    try:
        from . import living_careers
        offers = living_careers.decorate_player_offers(fighter, offers, pool=pool)
    except Exception:
        pass
    from . import booking
    if (getattr(fighter, "manager_id", None) and dominance(fighter) >= 20
            and "UFC" not in [x["org"] for x in offers]
            and booking.current_room(fighter) != "local"):
        if booking.try_direct_ufc(fighter):
            u = make_offer(fighter, "UFC", pool=pool)
            u["superfight"] = True
            offers.insert(0, u)
    return offers


def sign_org(fighter, org_id: str, fights: int = None, weeks: int = None,
             purse_win: int = 0, purse_show: int = 0) -> None:
    org_id = str(org_id or "").strip()
    if org_id not in ORGS:
        raise ValueError("unknown organization: %r" % org_id)
    spec = ORGS.get(org_id) or ORGS["LFA"]
    old_org = getattr(fighter, "organization", None)
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}; flags = fighter.story_flags
    old_belt = flags.get("org_belt")
    if old_belt and old_belt != org_id:
        former = list(flags.get("former_belts") or [])
        if old_belt not in former:
            former.append(old_belt)
        flags["former_belts"] = former[-8:]
        flags["org_belt"] = None
    if old_org != org_id:
        flags["org_rank"] = None
        if org_id == "UFC":
            flags["ufc_rank"] = None
        flags["title_offer_week"] = 0
    fighter.organization = org_id
    fighter.promotion_tier = spec["tier"]
    people.promoter_first_meeting_bonus(fighter, org_id)
    from . import identity
    fighter.room = identity.band_for(org_id, fighter.room or "local")
    # The 1.23 direct-sign paths created real exclusive contracts with $0/$0
    # terms because only offer objects carried purse data.  A contract must
    # always describe its baseline economics, even though individual bout
    # offers may later negotiate above them.
    if int(purse_win or 0) <= 0 or int(purse_show or 0) <= 0:
        try:
            from . import booking
            default_win, default_show = booking.purse_for(fighter, fighter.room, org_id)
            purse_win = int(purse_win or default_win)
            purse_show = int(purse_show or default_show)
        except Exception:
            lo, hi = spec.get("purse", (400, 900))
            purse_win = int(purse_win or max(40, (int(lo) + int(hi)) // 2))
            purse_show = int(purse_show or max(40, int(purse_win * 0.20)))
    from . import contracts
    try:
        contracts.sign(fighter, org_id, fights=fights, weeks=weeks,
                       purse_win=purse_win, purse_show=purse_show,
                       room=fighter.room)
    except Exception:
        # Never leave a visually signed fighter with a blank/nonexistent deal.
        fighter.org_contract = {
            "org": org_id, "fights_left": int(fights or contracts.DEFAULT_TERMS.get(fighter.room, (4,78))[0]),
            "fights_total": int(fights or contracts.DEFAULT_TERMS.get(fighter.room, (4,78))[0]),
            "weeks_left": int(weeks or contracts.DEFAULT_TERMS.get(fighter.room, (4,78))[1]),
            "signed_week": int(getattr(fighter, "week", 1) or 1),
            "purse_win": int(purse_win or 0), "purse_show": int(purse_show or 0),
            "exclusive": True, "room": fighter.room,
        }
    identity.sync(fighter)


def roster(pool, org_id: str) -> list:
    return [f for f in getattr(pool, "fighters", []) or []
            if getattr(f, "organization", "") == org_id and getattr(f, "active", True)]
