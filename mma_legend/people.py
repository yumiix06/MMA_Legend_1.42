"""v1.0 — The People system.

Every promotion has a promoter. Every fighter can sign a manager. Every
manager has an office culture. Every big fight gets a media cycle. None of
that used to be more than a text label; ``fighter.manager`` was a string
picked with ``random.choice`` and forgotten. This module turns those
labels into actual characters with a personality, a relationship score,
and consequences that flow back into bookings, purses and fame.

Design goals:
  * Cheap to hold in memory and trivial to save — a ``Person`` is a small
    dataclass, and relationship state is a single ``dict[str, int]`` on
    Fighter (``people_rel``), so old saves upgrade for free via setdefault.
  * Every character actually changes numbers: manager archetype shifts
    purse negotiation odds and cut %, promoter rapport shifts offer
    quality/tags in ``orgs.py``, media archetype shifts fame vs. reputation
    trade-offs on interviews.
  * Nothing here names or depicts a real person. Promoters, managers and
    media figures are original characters, not the real executives who run
    real organizations.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------
# The Person record
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class Person:
    id: str
    name: str
    role: str                      # "promoter" | "manager" | "media" | "matchmaker"
    org: Optional[str] = None      # promoters/matchmakers: home org
    agency: Optional[str] = None   # managers: firm name
    outlet: Optional[str] = None   # media: outlet name
    archetype: str = ""
    blurb: str = ""
    cut_pct: int = 12              # managers only
    negotiation: int = 50          # managers: contract/purse competency
    quirk: str = ""


# ---------------------------------------------------------------------
# Promoters — one signature figure per organization (orgs.py ORGS keys)
# ---------------------------------------------------------------------

_PROMOTERS = [
    Person("prom_ufc", "Marlon Kade", "promoter", org="UFC",
           archetype="The Ledger",
           blurb="Runs the biggest show like a hedge fund. Finishes and "
                 "storylines move you up his list faster than records do.",
           quirk="rewards_finishes"),
    Person("prom_pfl", "Talia Voss", "promoter", org="PFL",
           archetype="The Bracketeer",
           blurb="Believes in the format over the face. Wants a full "
                 "season of activity, not one big callout.",
           quirk="rewards_activity"),
    Person("prom_bellator", "Duncan Reyes", "promoter", org="Bellator",
           archetype="The Company Man",
           blurb="Old-school promoter, values loyalty and a clean record "
                 "over hype. Slow to trust, slow to drop you.",
           quirk="rewards_loyalty"),
    Person("prom_bravecf", "Nasser Al-Hadi", "promoter", org="BRAVE CF",
           archetype="The Builder",
           blurb="Building a global brand from Bahrain outward. Loves an "
                 "underdog with a flag and a story.",
           quirk="rewards_story"),
    Person("prom_ksw", "Wiktor Sobol", "promoter", org="KSW",
           archetype="The Showman",
           blurb="Sells out arenas on personality. Wants you loud at the "
                 "press conference, not just good in the cage.",
           quirk="rewards_hype"),
    Person("prom_cw", "Fionn Delaney", "promoter", org="Cage Warriors",
           archetype="The Talent Scout",
           blurb="Everyone he signs, someone else eventually poaches. He "
                 "knows it and treats prospects accordingly — get in, "
                 "prove it fast, move on.",
           quirk="rewards_prospects"),
    Person("prom_balkan", "Elitsa Marinova", "promoter", org="Balkan Combat",
           archetype="The Regional Anchor",
           blurb="Keeps the Balkan scene alive fight by fight. Fiercely "
                 "loyal to fighters who stay and build the region with her.",
           quirk="rewards_loyalty"),
    Person("prom_lfa", "Cody Marsh", "promoter", org="LFA",
           archetype="The Feeder",
           blurb="Runs the widest-known UFC feeder circuit in North "
                 "America. Blunt about who's ready and who isn't.",
           quirk="rewards_activity"),
    Person("prom_roadfc", "Han Ji-woo", "promoter", org="Road FC",
           archetype="The Technician",
           blurb="Respects clean, technical wins over wild ones. Doesn't "
                 "care about your interview, cares about your tape.",
           quirk="rewards_technical"),
    Person("prom_aresfc", "Camille Fabron", "promoter", org="ARES FC",
           archetype="The Diplomat",
           blurb="Plays a long, patient game — favors fighters and camps "
                 "who keep their word on short notice and rematch clauses.",
           quirk="rewards_reliability"),
    Person("prom_aca", "Ruslan Bekov", "promoter", org="ACA",
           archetype="The Bear",
           blurb="Grozny-to-Moscow cards. Wants wrestlers who can finish.",
           quirk="rewards_finishes"),
    Person("prom_efc", "Lerato Maseko", "promoter", org="EFC",
           archetype="The Continental",
           blurb="Johannesburg first. Builds African names, then exports them.",
           quirk="rewards_story"),
]

_PROMOTER_BY_ORG = {p.org: p for p in _PROMOTERS}
_PROMOTER_BY_ID = {p.id: p for p in _PROMOTERS}

# One matchmaker per org. Separate rapport from the promoter.
_MATCHMAKERS = [
    Person("mm_ufc", "Ellis Rowan", "matchmaker", org="UFC",
           archetype="The Chess Player",
           blurb="Builds cards like puzzles. Remembers who ducked who.",
           quirk="style_avoid"),
    Person("mm_pfl", "Grant Holm", "matchmaker", org="PFL",
           archetype="The Scheduler",
           blurb="Wants bodies on every seasonal card.",
           quirk="activity_first"),
    Person("mm_bellator", "Mara Quinn", "matchmaker", org="Bellator",
           archetype="The Sequelist",
           blurb="Lives for rematches the crowd already understands.",
           quirk="wants_rematches"),
    Person("mm_bravecf", "Yusuf Rahman", "matchmaker", org="BRAVE CF",
           archetype="The Flag Bearer",
           blurb="Puts a story on the poster before a style.",
           quirk="protects_prospects"),
    Person("mm_ksw", "Olek Baran", "matchmaker", org="KSW",
           archetype="The Crowd Reader",
           blurb="Finishes sell tickets. Decisions do not.",
           quirk="finishes_over_decisions"),
    Person("mm_cw", "Siobhan Reilly", "matchmaker", org="Cage Warriors",
           archetype="The Feeder Scout",
           blurb="Finds the next name and moves them before they go stale.",
           quirk="protects_prospects"),
    Person("mm_balkan", "Dragan Ilic", "matchmaker", org="Balkan Combat",
           archetype="The Regional Book",
           blurb="Keeps local names working. Trap nights happen when you go cold.",
           quirk="activity_first"),
    Person("mm_lfa", "Wes Collier", "matchmaker", org="LFA",
           archetype="The Volume Booker",
           blurb="Always has a local date. Quality varies with rapport.",
           quirk="activity_first"),
    Person("mm_roadfc", "Min Seo-yun", "matchmaker", org="Road FC",
           archetype="The Tape Watcher",
           blurb="Will not feed a wrestler the same brick wall three times.",
           quirk="style_avoid"),
    Person("mm_aca", "Islam Dudaev", "matchmaker", org="ACA",
           archetype="The Booker",
           blurb="Pairs Dagestan wrestling with whoever will stand and trade.",
           quirk="wrestle_bias"),
    Person("mm_efc", "Sipho Ndlovu", "matchmaker", org="EFC",
           archetype="The Booker",
           blurb="Keeps South African cards full and African prospects busy.",
           quirk="regional"),
    Person("mm_aresfc", "Luc Morel", "matchmaker", org="ARES FC",
           archetype="The Reliable Hand",
           blurb="Short notice is a test. Show up and the next card improves.",
           quirk="title_or_bust"),
    Person("mm_fixer", "Gym Fixer", "matchmaker", org="Local Fight Nights",
           archetype="The Gym Fixer",
           blurb="No manager. He finds you a body on a local card and takes a cut in goodwill.",
           quirk="activity_first"),
]
_MATCHMAKER_BY_ORG = {p.org: p for p in _MATCHMAKERS}
_MATCHMAKER_BY_ID = {p.id: p for p in _MATCHMAKERS}


def matchmaker_for(org: str) -> Optional[Person]:
    if not org:
        return _MATCHMAKER_BY_ID.get("mm_fixer")
    return _MATCHMAKER_BY_ORG.get(org) or _MATCHMAKER_BY_ID.get("mm_fixer")


def all_matchmakers() -> list:
    return list(_MATCHMAKERS)


def gym_fixer() -> Person:
    return _MATCHMAKER_BY_ID["mm_fixer"]


_GYM_COACHES = [
    Person("coach_gym", "Sasha Kolarov", "coach",
           archetype="The Pads Man",
           blurb="Runs the weekday sessions. Film night is his love language.",
           quirk="film_night"),
    Person("coach_wrestle", "Ivo Petrov", "coach",
           archetype="The Room Wrestler",
           blurb="Lives in the wrestling room. Wants chain wrestling, not highlight kicks.",
           quirk="wrestle_first"),
    Person("coach_box", "Elena Ruiz", "coach",
           archetype="The Mitts",
           blurb="Jab, feet, don't get hit. Loud when you forget.",
           quirk="jab_first"),
]


def ensure_gym_coach(fighter) -> Person:
    flags = getattr(fighter, "story_flags", None)
    if flags is None:
        fighter.story_flags = {}
        flags = fighter.story_flags
    cid = flags.get("coach_id")
    bag = {p.id: p for p in _GYM_COACHES}
    if cid in bag:
        return bag[cid]
    style = (getattr(fighter, "amateur_discipline", "") or "").lower()
    if "wrest" in style or "sambo" in style:
        pick = _GYM_COACHES[1]
    elif "box" in style:
        pick = _GYM_COACHES[2]
    else:
        pick = _GYM_COACHES[0]
    flags["coach_id"] = pick.id
    rel = getattr(fighter, "people_rel", None)
    if rel is None:
        fighter.people_rel = {}
        rel = fighter.people_rel
    rel.setdefault(pick.id, 52)
    try:
        fighter.coach_id = pick.id
    except Exception:
        pass
    return pick


def gym_coach(fighter) -> Optional[Person]:
    flags = getattr(fighter, "story_flags", None) or {}
    cid = flags.get("coach_id") or getattr(fighter, "coach_id", None)
    return next((p for p in _GYM_COACHES if p.id == cid), None)


def cool_matchmaker(fighter, org: str, delta: int = -8) -> int:
    mm = matchmaker_for(org)
    if not mm:
        return 50
    return adjust_rapport(fighter, mm.id, delta)


def warm_matchmaker(fighter, org: str, delta: int = 4) -> int:
    mm = matchmaker_for(org)
    if not mm:
        return 50
    return adjust_rapport(fighter, mm.id, delta)


def promoter_for(org: str) -> Optional[Person]:
    return _PROMOTER_BY_ORG.get(org)


def all_promoters() -> list:
    return list(_PROMOTERS)


# ---------------------------------------------------------------------
# Managers — agencies you can sign, fire and re-approach
# ---------------------------------------------------------------------

_MANAGERS = [
    Person("mgr_vale", "Rosa Calder", "manager", agency="Vale Office",
           archetype="Aggressive Closer",
           blurb="Squeezes every offer for more money before you sign "
                 "anything. Promoters find her exhausting. Fighters find "
                 "her useful.",
           cut_pct=15, negotiation=88, quirk="aggressive"),
    Person("mgr_northside", "Terrence Okoye", "manager", agency="Northside",
           archetype="Loyal Company Man",
           blurb="Won't chase the flashy offer. Keeps you working steady "
                 "and keeps promoters happy with you.",
           cut_pct=10, negotiation=62, quirk="loyal"),
    Person("mgr_karas", "Nadia Karas", "manager", agency="Karas Mgmt",
           archetype="The Matchmaking Nerd",
           blurb="Studies tape harder than most coaches. Will talk you out "
                 "of a bad style matchup even if it costs her a payday.",
           cut_pct=12, negotiation=82, quirk="analytical"),
    Person("mgr_harbor", "Sione Tui", "manager", agency="Harbor",
           archetype="The Connector",
           blurb="Knows every promoter in this book personally. Rapport "
                 "with the front office moves faster with him behind you.",
           cut_pct=13, negotiation=78, quirk="connector"),
    Person("mgr_summit", "Priya Anand", "manager", agency="Summit Athlete Group",
           archetype="The Brand Builder",
           blurb="Thinks in sponsorships and long careers, not just the "
                 "next purse. Slower money now, more of it later.",
           cut_pct=14, negotiation=72, quirk="brand"),
]

_MANAGER_BY_ID = {m.id: m for m in _MANAGERS}


def all_managers() -> list:
    return list(_MANAGERS)


def manager_candidates(fighter, n: int = 3) -> list:
    """Weighted sample. Brand and Connector stay rare at low fame."""
    fame = int(getattr(fighter, "fame", 0) or 0)
    pool = list(_MANAGERS)
    weights = []
    for m in pool:
        w = 1.0
        if m.quirk == "brand" and fame < 10:
            w = 0.08
        if m.quirk == "connector" and fame < 5:
            w = 0.15
        weights.append(w)
    picks = []
    bag = list(zip(pool, weights))
    while bag and len(picks) < n:
        names, ws = zip(*bag)
        chosen = random.choices(list(names), weights=list(ws), k=1)[0]
        picks.append(chosen)
        bag = [(m, w) for m, w in bag if m.id != chosen.id]
    return picks


# ---------------------------------------------------------------------
# Media personalities
# ---------------------------------------------------------------------

_MEDIA = [
    Person("med_insider", "Devon Wray", "media", outlet="The Fight Wire",
           archetype="The Insider",
           blurb="Trades in locker-room leaks and matchmaking rumors. "
                 "Low-risk interview, modest fame either way.",
           quirk="insider"),
    Person("med_skeptic", "Halima Noor", "media", outlet="Cage Critique",
           archetype="The Skeptic",
           blurb="Pushes back on every claim you make. Rough interview, "
                 "but she rewards a humble, credible answer with real "
                 "reputation.",
           quirk="skeptic"),
    Person("med_hype", "Bo 'Loudmouth' Castillo", "media", outlet="RingSide Live",
           archetype="The Hype Man",
           blurb="Wants a soundbite, not a scouting report. Big fame swings "
                 "if you bring the fire — but promoters notice when your "
                 "mouth outruns your record.",
           quirk="hype"),
    Person("med_historian", "Elin Sorensen", "media", outlet="The Long Count",
           archetype="The Historian",
           blurb="Cares about your whole body of work. Rewards experience "
                 "and a long memory over a hot streak.",
           quirk="historian"),
]

_MEDIA_BY_ID = {m.id: m for m in _MEDIA}


def all_media() -> list:
    return list(_MEDIA)


def media_candidates(fighter, n: int = 2) -> list:
    pool = list(_MEDIA)
    random.shuffle(pool)
    return pool[:n]


# ---------------------------------------------------------------------
# Rapport storage — a single dict on Fighter, lazily populated
# ---------------------------------------------------------------------

def _rel(fighter) -> dict:
    d = getattr(fighter, "people_rel", None)
    if not isinstance(d, dict):
        d = {}
        fighter.people_rel = d
    return d


def rapport(fighter, person_id: str) -> int:
    return int(_rel(fighter).get(person_id, 50))


def adjust_rapport(fighter, person_id: str, delta: int) -> int:
    rel = _rel(fighter)
    cur = int(rel.get(person_id, 50))
    cur = max(0, min(100, cur + int(delta)))
    rel[person_id] = cur
    return cur


def by_id(person_id: str) -> Optional[Person]:
    return (_PROMOTER_BY_ID.get(person_id) or _MANAGER_BY_ID.get(person_id)
            or _MEDIA_BY_ID.get(person_id) or _MATCHMAKER_BY_ID.get(person_id))


# ---------------------------------------------------------------------
# Manager lifecycle
# ---------------------------------------------------------------------

def current_manager(fighter) -> Optional[Person]:
    mid = getattr(fighter, "manager_id", None)
    return _MANAGER_BY_ID.get(mid) if mid else None


def sign_manager(fighter, person: Person) -> None:
    fighter.manager_id = person.id
    fighter.manager = person.agency          # back-compat display field
    fighter.manager_cut = person.cut_pct
    rel = _rel(fighter)
    rel.setdefault(person.id, 55)


def fire_manager(fighter) -> None:
    person = current_manager(fighter)
    if person:
        adjust_rapport(fighter, person.id, -15)
    fighter.manager_id = None
    fighter.manager = None
    fighter.manager_cut = 0


def manager_purse_multiplier(fighter) -> float:
    """Passive offer-quality effect from manager skill, personality and trust."""
    person = current_manager(fighter)
    if not person:
        return 1.0
    rel = rapport(fighter, person.id)
    skill = int(getattr(person, "negotiation", 50) or 50)
    base = 0.99 + (skill - 50) / 500.0
    if person.quirk == "aggressive":
        base += 0.04
    elif person.quirk == "brand":
        base -= 0.015
    trust_bonus = (rel - 50) / 500.0
    return max(0.88, min(1.18, base + trust_bonus))

def negotiate_purse(fighter, booked: dict) -> tuple:
    """Manager calls the promoter. Competency, personality and relationship all matter."""
    person = current_manager(fighter)
    purse = int(booked.get("purse_win", 0))
    if not person:
        return False, purse, "No manager to make the call. Sign one first."
    rel = rapport(fighter, person.id)
    skill = int(getattr(person, "negotiation", 50) or 50)
    chance = 0.18 + skill / 180.0 + (rel - 50) / 300.0
    if person.quirk == "aggressive": chance += 0.10
    elif person.quirk == "loyal": chance -= 0.05
    chance = max(0.10, min(0.90, chance))
    org = str(booked.get("org") or getattr(fighter, "organization", "") or "")
    try:
        from . import memory
        promoter = promoter_for(org)
        if promoter:
            chance += memory.score(fighter, promoter.id) / 100.0
    except Exception:
        promoter = None
    if random.random() < max(0.08, min(0.92, chance)):
        lo = 0.05 + max(0, skill - 50) / 1000.0
        hi = 0.11 + max(0, skill - 50) / 600.0
        if person.quirk == "aggressive": hi += 0.05
        bump = random.uniform(lo, hi)
        new_purse = int(purse * (1 + bump))
        booked["purse_win"] = new_purse
        booked["purse_show"] = max(40, int(new_purse * 0.20))
        adjust_rapport(fighter, person.id, 2)
        if promoter:
            try:
                memory.remember(fighter, promoter.id, "professional_negotiation", "%s moved purse" % person.name)
            except Exception:
                pass
        return True, new_purse, "%s got the promoter to move. Purse now $%s." % (person.name, new_purse)
    adjust_rapport(fighter, person.id, -1)
    if promoter:
        try:
            memory.remember(fighter, promoter.id, "hard_negotiation", "%s pushed purse" % person.name)
        except Exception:
            pass
    return False, purse, "%s pushed, promoter didn't budge this time." % person.name


# ---------------------------------------------------------------------
# Promoter-side effects on booking (used by orgs.py)
# ---------------------------------------------------------------------

def promoter_purse_multiplier(fighter, org: str) -> float:
    promoter = promoter_for(org)
    if not promoter:
        return 1.0
    rel = rapport(fighter, promoter.id)
    try:
        from . import memory
        mem = memory.score(fighter, promoter.id)
    except Exception:
        mem = 0
    return max(0.80, min(1.22, 0.85 + (rel / 100.0) * 0.30 + mem / 200.0))


def promoter_trap_bias(fighter, org: str) -> float:
    """Positive = more likely to get thrown a bad-style 'trap' fight,
    negative = promoter is looking out for you."""
    promoter = promoter_for(org)
    if not promoter:
        return 0.0
    rel = rapport(fighter, promoter.id)
    try:
        from . import memory
        mem = memory.score(fighter, promoter.id)
    except Exception:
        mem = 0
    return max(-0.20, min(0.35, (50 - rel) / 200.0 - mem / 100.0))


def promoter_first_meeting_bonus(fighter, org: str) -> None:
    """Call once, the first time a fighter signs with an org, to seed a
    reasonable starting rapport instead of a flat 50 for everyone."""
    promoter = promoter_for(org)
    if not promoter:
        return
    fame = int(getattr(fighter, "fame", 0) or 0)
    start = 45 + min(15, fame // 4)
    rel = _rel(fighter)
    rel.setdefault(promoter.id, start)


# ---------------------------------------------------------------------
# Interactive scenes
# ---------------------------------------------------------------------

def meet_promoter_menu(console, fighter) -> None:
    """The E) Life / People -> Promoters screen. Talk to the head of the
    org you currently fight for, or the org whose home turf you're from
    if you're not yet signed anywhere."""
    org = getattr(fighter, "organization", None) or None
    if not org:
        from . import orgs as orgs_mod
        org = orgs_mod.home_org(getattr(fighter, "country", "") or "")
    promoter = promoter_for(org)
    if not promoter:
        console.warn("No promoter contact yet. Turn pro and sign with an org first.")
        console.pause(0.6)
        return
    promoter_first_meeting_bonus(fighter, org)
    rel = rapport(fighter, promoter.id)
    console.header("PROMOTER — %s" % org)
    if hasattr(console, "person_card"):
        console.person_card("promoter", promoter.name, promoter.quirk, rel, promoter.blurb)
    else:
        console.print(promoter.blurb)
        console.print("Rapport: %d/100" % rel)
    console.print("  A) Make small talk (safe, small rapport gain)")
    console.print("  B) Pitch yourself for a bigger fight (risk/reward)")
    console.print("  C) Ask about a title picture (needs strong rapport + record)")
    console.print("  D) Sign a multi-fight contract")
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    if ch == "A":
        adjust_rapport(fighter, promoter.id, random.randint(2, 5))
        console.good("%s appreciates you showing up in person." % promoter.name)
    elif ch == "B":
        rec = fighter.pro_record or [0, 0, 0]
        confident = rec[0] >= rec[1] and rel >= 40
        if confident and random.random() < 0.55:
            adjust_rapport(fighter, promoter.id, random.randint(6, 10))
            from .notoriety import add_fame
            add_fame(fighter, 2, "promoter meeting")
            console.good("%s likes the confidence. Fame +2." % promoter.name)
        else:
            adjust_rapport(fighter, promoter.id, -random.randint(4, 8))
            console.warn("%s thinks you're getting ahead of yourself." % promoter.name)
    elif ch == "C":
        if rel >= 70 and (fighter.pro_record or [0, 0])[0] >= 6:
            console.gold("%s: \"Keep winning and we'll talk.\" Title path noted." % promoter.name)
            flags = getattr(fighter, "story_flags", None)
            if isinstance(flags, dict):
                flags["promoter_title_track_%s" % org] = True
        else:
            console.warn("%s isn't ready to have that conversation yet." % promoter.name)
    elif ch == "D":
        if not fighter.pro_debut:
            console.warn("Turn pro first.")
        else:
            from .systems15 import sign_contract
            console.good(sign_contract(fighter, org, fights=4))
            adjust_rapport(fighter, promoter.id, 4)
    console.pause(0.6)


def media_menu(console, fighter) -> None:
    """A dedicated interview scene with a named media personality, distinct
    from the flavor-only post-fight interview in story.py."""
    candidates = media_candidates(fighter, n=3)
    console.header("MEDIA", "Pick who gets the interview")
    for i, m in enumerate(candidates):
        console.print("  %s) %s — %s (%s)" % ("ABC"[i], m.name, m.outlet, m.archetype))
    console.print("  X) Back")
    raw = console.ask("Choice > ").strip().upper()
    idx = "ABC".find(raw)
    if idx < 0 or idx >= len(candidates):
        return
    person = candidates[idx]
    console.print(person.blurb)
    console.print("  A) Humble — credit the work, deflect the spotlight")
    console.print("  B) Fire — sell yourself, call out a name")
    console.print("  C) Cold — short answers, get out")
    ch = console.ask("Approach > ").strip().upper()
    rel = rapport(fighter, person.id)
    fame_gain, rep_gain, rel_gain = 0, 0, 0
    if person.quirk == "skeptic":
        fame_gain, rep_gain, rel_gain = (1, 5, 6) if ch == "A" else ((3, -2, -3) if ch == "B" else (0, 1, -1))
    elif person.quirk == "hype":
        fame_gain, rep_gain, rel_gain = (1, 2, 2) if ch == "A" else ((6, -3, 5) if ch == "B" else (0, 0, -2))
    elif person.quirk == "historian":
        rec = fighter.pro_record or [0, 0, 0]
        exp_bonus = min(4, (rec[0] + rec[1]) // 3)
        fame_gain, rep_gain, rel_gain = (1 + exp_bonus, 3, 4) if ch == "A" else ((2, 0, 1) if ch == "B" else (0, 1, 0))
    else:  # insider
        fame_gain, rep_gain, rel_gain = (2, 2, 3) if ch == "A" else ((3, 0, 2) if ch == "B" else (1, 0, 0))
    from .notoriety import add_fame
    add_fame(fighter, fame_gain, "media appearance")
    if hasattr(fighter, "reputation"):
        fighter.reputation = max(0, int(getattr(fighter, "reputation", 0)) + rep_gain)
    adjust_rapport(fighter, person.id, rel_gain)
    console.good("%s: fame +%d, reputation %+d." % (person.outlet, fame_gain, rep_gain))
    console.pause(0.6)


def manager_office_menu(console, fighter) -> None:
    """Pick / meet a manager candidate, with a personality-driven pitch
    instead of a flat random.choice assignment."""
    note = (fighter.story_flags or {}).get("manager_note")
    if note:
        console.info(note)
    console.header("SIGN A MANAGER")
    candidates = manager_candidates(fighter, n=3)
    for i, m in enumerate(candidates):
        console.print("  %s) %s — %s (%s, %d%% cut)" % ("ABC"[i], m.name, m.agency, m.archetype, m.cut_pct))
        console.print("     %s" % m.blurb)
    console.print("  X) Back")
    raw = console.ask("Choice > ").strip().upper()
    idx = "ABC".find(raw)
    if idx < 0 or idx >= len(candidates):
        return
    person = candidates[idx]
    sign_manager(fighter, person)
    console.good("Signed with %s (%s), %d%% cut." % (person.agency, person.name, person.cut_pct))
    console.pause(0.6)
