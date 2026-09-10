"""Overseas camps (1.19.3).

The old version was a stat potion: pay money, receive +1 to three skills per
week, get handed a `connection` dict that **nothing in the game ever read**.
Weeks passed and nothing about your career changed except some numbers.

A camp abroad should cost you something real and give you something the gym at
home cannot:

* **Weeks you cannot fight.** You are on another continent. Bookings pause.
* **A named room** with its own culture, and fighters better than you in one
  specific area. Getting beaten up in Dagestan is the point.
* **Techniques you cannot learn at home.** Each destination teaches things its
  own tradition owns.
* **People.** A connection is a real NPC — a coach who will corner you, a
  matchmaker who now takes your calls, a training partner who becomes a name.
  These are the things that actually move a career.
* **Adaptation.** Language, food, altitude, homesickness. The first weeks hurt,
  the later weeks pay. Leaving early wastes the money.
"""
from __future__ import annotations

import random

DESTINATIONS = {
    "A": {
        "id": "dagestan",
        "name": "Makhachkala, Dagestan",
        "room": "a freezing wrestling hall with no heating and forty men in it",
        "country": "Russia",
        "weeks": 6,
        "quality": 4,
        "network": 3,
        "travel_premium": 300,
        "focus": ("grappling", "takedown_def", "strength", "cardio"),
        "teaches": ("Chain Wrestling", "Leg Ride", "Front Headlock"),
        "hardship": 3,
        "style": "Wrestling",
        "note": "They will not speak to you for two weeks. Then they will.",
    },
    "B": {
        "id": "thailand",
        "name": "Phuket, Thailand",
        "room": "an open-air camp, two sessions a day, forty degrees",
        "country": "Thailand",
        "weeks": 5,
        "quality": 4,
        "network": 2,
        "travel_premium": 250,
        "focus": ("kicks", "striking", "cardio", "durability"),
        "teaches": ("Teep", "Switch Kick", "Clinch Knees", "Elbow"),
        "hardship": 2,
        "style": "Muay Thai",
        "note": "Runs at 6am. Pads until your shins stop being yours.",
    },
    "C": {
        "id": "brazil",
        "name": "Rio de Janeiro, Brazil",
        "room": "a mat room above a shop, no air conditioning, everyone is a black belt",
        "country": "Brazil",
        "weeks": 5,
        "quality": 4,
        "network": 3,
        "travel_premium": 400,
        "focus": ("submissions", "ground_control", "fight_iq", "adaptability"),
        "teaches": ("Berimbolo", "Guard Retention", "Back Take", "Triangle"),
        "hardship": 2,
        "style": "BJJ",
        "note": "You will tap a hundred times. That is the tuition.",
    },
    "D": {
        "id": "usa",
        "name": "Las Vegas, USA",
        "room": "a fight-team gym full of ranked professionals",
        "country": "USA",
        "weeks": 4,
        "quality": 5,
        "network": 5,
        "travel_premium": 1000,
        "focus": ("striking", "grappling", "fight_iq", "speed"),
        "teaches": ("Level Change", "Cage Wrestling", "Southpaw Switch"),
        "hardship": 1,
        "style": "MMA",
        "note": "Expensive, professional, and full of people with your job.",
    },
    "E": {
        "id": "kyrgyzstan",
        "name": "Bishkek, Kyrgyzstan",
        "room": "a combat sambo club at altitude where nobody has heard of you",
        "country": "Kyrgyzstan",
        "weeks": 6,
        "quality": 3,
        "network": 2,
        "travel_premium": -300,
        "focus": ("cardio", "strength", "grappling", "durability"),
        "teaches": ("Ouchi Gari", "Belt-Grip O-Goshi", "Straight Ankle Lock"),
        "hardship": 3,
        "style": "Combat Sambo",
        "note": "Cheap, brutal, and the altitude does half the work.",
    },
}


def _quoted_cost(spec: dict) -> int:
    """Price camps by time, room quality and expected career upside.

    The old prices were hand-entered and therefore drifted away from what a
    destination actually rewarded.  This quote intentionally prices not only
    accommodation/time but the things the player can bring home: rare
    techniques and a useful network.  Rounded hundreds keep the UI readable.
    """
    weeks = int(spec.get("weeks", 4) or 4)
    quality = max(1, min(5, int(spec.get("quality", 3) or 3)))
    network = max(1, min(5, int(spec.get("network", 2) or 2)))
    techniques = len(tuple(spec.get("teaches") or ()))
    raw = (
        weeks * 300
        + quality * 450
        + techniques * 180
        + network * 250
        + int(spec.get("travel_premium", 0) or 0)
    )
    return max(1800, int(round(raw / 100.0) * 100))


# Keep ``spec['cost']`` for older callers/tests, but derive it from the reward
# profile so future edits to a camp cannot silently leave its price stale.
for _spec in DESTINATIONS.values():
    _spec["cost"] = _quoted_cost(_spec)


CAMP_WEEK_EVENTS = {
    "dagestan": (
        ("Chain wrestling gauntlet", "The room makes you finish three attacks in sequence.", "grappling", "cardio"),
        ("Wall-wrestling rounds", "Every round starts with your back on the wall.", "takedown_def", "ground_control"),
    ),
    "thailand": (
        ("Pad-round correction", "The trainer rebuilds your kick entries behind the jab.", "kicks", "distance_management"),
        ("Clinch shark tank", "Fresh partners rotate through the clinch.", "striking", "cardio"),
    ),
    "brazil": (
        ("Positional escape rounds", "You start mounted or with your back taken.", "submission_def", "grappling"),
        ("Guard passing lab", "The room makes you solve the same guard five different ways.", "ground_control", "fight_iq"),
    ),
    "usa": (
        ("Pro sparring day", "A ranked room forces you to connect phases instead of winning one exchange.", "fight_iq", "adaptability"),
        ("Cage scenario rounds", "Score, defend the return, exit safely. Repeat.", "grappling", "distance_management"),
    ),
    "kyrgyzstan": (
        ("Sambo throw ladder", "Every round begins in grips and ends only after a clean score.", "grappling", "strength"),
        ("Combat sambo pressure round", "Strikes must create the throw; the throw must create the finish.", "fight_iq", "submissions"),
    ),
}

def _camp_week_event(fighter, spec: dict, done: int, total: int, console=None) -> None:
    """Contextual camp training beat. It never spends another week."""
    # Guaranteed early/mid/late beats plus occasional extra room-specific work.
    if done not in {2, max(2, total // 2), max(2, total - 1)} and random.random() >= 0.28:
        return
    choices = CAMP_WEEK_EVENTS.get(spec.get("id"), ())
    if not choices:
        return
    title, desc, primary, secondary = random.choice(choices)
    hard = random.random() < 0.58
    if console:
        console.section("CAMP TRAINING · %s" % title.upper())
        console.print(desc)
        console.print("  A) Take the hard rounds  B) Technical reps / recover")
        try:
            hard = (console.ask("Camp choice > ") or "B").strip().upper() == "A"
        except Exception:
            hard = False
    amount = 2 if hard else 1
    for skill in (primary, secondary):
        if hasattr(fighter, skill):
            try:
                from .physiology import gain_stat
                gain_stat(fighter, skill, amount)
            except Exception:
                setattr(fighter, skill, min(99, int(getattr(fighter, skill, 40) or 40) + amount))
    if hard:
        fighter.energy = max(5, int(getattr(fighter, "energy", 50) or 50) - 6)
        fighter.camp_technique_xp = int(getattr(fighter, "camp_technique_xp", 0) or 0) + 2
        if console: console.good("You stayed in. The room got something out of you.")
    else:
        fighter.energy = min(100, int(getattr(fighter, "energy", 50) or 50) + 3)
        fighter.health = min(100, int(getattr(fighter, "health", 80) or 80) + 1)
        if console: console.info("Cleaner reps, less damage. You banked the lesson.")

CONNECTION_ROLES = ("coach", "training partner", "matchmaker", "gym owner")


def _flags(fighter) -> dict:
    f = getattr(fighter, "story_flags", None)
    if not isinstance(f, dict):
        fighter.story_flags = {}
        f = fighter.story_flags
    return f


def active(fighter) -> dict:
    """The camp currently being attended, or {}."""
    cid = getattr(fighter, "intl_camp", None)
    if not cid:
        return {}
    for spec in DESTINATIONS.values():
        if spec["id"] == cid:
            return spec
    return {}


def can_go(fighter) -> tuple:
    """(ok, reason). A camp abroad is weeks of your life."""
    if getattr(fighter, "intl_camp", None):
        return (False, "You are already abroad.")
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week"):
        return (False, "You have a date booked. Camps abroad are between fights.")
    if int(getattr(fighter, "suspension_weeks", 0) or 0) > 0:
        return (False, "Suspended. You are not flying anywhere to train.")
    inj = getattr(fighter, "injury", None)
    if isinstance(inj, dict) and int(inj.get("weeks", 0) or 0) > 3:
        return (False, "Too hurt to survive a camp abroad.")
    return (True, "")


def preview(fighter, key: str) -> dict:
    spec = DESTINATIONS.get(key)
    if not spec:
        return {}
    cost = int(spec["cost"])
    money = int(getattr(fighter, "money", 0) or 0)
    return {
        "spec": spec,
        "cost": cost,
        "affordable": money >= cost,
        "shortfall": max(0, cost - money),
        "weeks": int(spec["weeks"]),
        "quality": int(spec.get("quality", 3) or 3),
        "network": int(spec.get("network", 2) or 2),
        "reward_count": len(tuple(spec.get("teaches") or ())),
    }


def start(fighter, key: str, console=None) -> str:
    ok, why = can_go(fighter)
    if not ok:
        return why
    spec = DESTINATIONS.get(key)
    if not spec:
        return "No such camp."
    cost = int(spec["cost"])
    # Cash may go negative — flying out broke is a decision, not a block.
    fighter.money = int(getattr(fighter, "money", 0) or 0) - cost
    fighter.intl_camp = spec["id"]
    fighter.intl_camp_weeks = int(spec["weeks"])
    fighter.camp_active = True
    fighter.camp_focus = spec["name"]
    fl = _flags(fighter)
    fl["camp_progress"] = 0
    fl["camp_total"] = int(spec["weeks"])
    if console:
        console.banner(spec["name"])
        console.print(spec["room"].capitalize() + ".")
        console.print(spec["note"])
        console.print("%s weeks. $%s gone. No fights while you are out there." % (
            spec["weeks"], cost))
    return "Flying out: %s (%sw)." % (spec["name"], spec["weeks"])


def tick(fighter, console=None) -> None:
    """One week abroad. Early weeks hurt; later weeks pay."""
    left = int(getattr(fighter, "intl_camp_weeks", 0) or 0)
    if left <= 0:
        return
    spec = active(fighter)
    if not spec:
        fighter.intl_camp = None
        fighter.intl_camp_weeks = 0
        return

    fl = _flags(fighter)
    done = int(fl.get("camp_progress", 0) or 0) + 1
    fl["camp_progress"] = done
    total = int(fl.get("camp_total", spec["weeks"]) or spec["weeks"])
    fighter.intl_camp_weeks = left - 1

    # Adaptation curve: the first third is survival, the rest is learning.
    settling = done <= max(1, total // 3)
    hardship = int(spec.get("hardship", 2))
    drain = 8 + hardship * 2 if settling else 5 + hardship
    fighter.energy = max(6, int(getattr(fighter, "energy", 60) or 60) - drain)

    if settling:
        fighter.happiness = max(0, int(getattr(fighter, "happiness", 50) or 50) - hardship * 2)
        gains = 1
        if console and done == 1:
            console.print("Week 1: you are the outsider. Everything hurts.")
    else:
        gains = 2
        fighter.happiness = min(100, int(getattr(fighter, "happiness", 50) or 50) + 1)

    for sk in spec["focus"]:
        if hasattr(fighter, sk) and random.random() < 0.7:
            try:
                from .physiology import gain_stat
                gain_stat(fighter, sk, gains)
            except Exception:
                setattr(fighter, sk, min(95, int(getattr(fighter, sk) or 40) + gains))

    _camp_week_event(fighter, spec, done, total, console)

    # Techniques the home gym cannot teach.
    if not settling and random.random() < 0.45:
        pool = [t for t in spec["teaches"]
                if t not in (getattr(fighter, "techniques", None) or [])]
        if pool:
            name = random.choice(pool)
            learned = False
            if hasattr(fighter, "learn_technique"):
                learned = bool(fighter.learn_technique(name))
            if learned and console:
                console.good("They showed you the %s." % name)

    # Injury risk is real in a hard room.
    if random.random() < 0.02 * hardship:
        try:
            from .cut import apply_injury
            apply_injury(fighter, random.choice(("rib", "knee", "shoulder")), 1)
            if console:
                console.warn("Banged up in sparring. It will follow you home.")
        except Exception:
            pass

    if fighter.intl_camp_weeks <= 0:
        _finish(fighter, spec, console)


def _finish(fighter, spec: dict, console=None) -> None:
    """Come home with people, not just numbers."""
    fl = _flags(fighter)
    conns = list(getattr(fighter, "connections", None) or [])
    role = random.choice(CONNECTION_ROLES)
    name = _person_name(spec)
    conn = {
        "place": spec["id"],
        "place_name": spec["name"],
        "who": name,
        "role": role,
        "style": spec.get("style", "MMA"),
        "week": int(getattr(fighter, "week", 0) or 0),
        "strength": random.randint(45, 80),
    }
    conns.append(conn)
    fighter.connections = conns

    from .notoriety import add_fame
    add_fame(fighter, 2, "completed international camp")
    fighter.adaptability = min(95, int(getattr(fighter, "adaptability", 40) or 40) + 2)
    visited = list(fl.get("camps_visited") or [])
    if spec["id"] not in visited:
        visited.append(spec["id"])
    fl["camps_visited"] = visited

    fighter.intl_camp = None
    fighter.intl_camp_weeks = 0
    fighter.camp_active = False

    if console:
        console.section("HOME FROM %s" % spec["name"].upper())
        console.print("You came back with a %s: %s." % (role, name))
        if role == "coach":
            console.print("He will corner you if you ask.")
        elif role == "matchmaker":
            console.print("He takes your calls now. Dates in %s are possible." % spec["country"])
        elif role == "training partner":
            console.print("Somebody in %s answers when you need work." % spec["country"])
        else:
            console.print("A door in %s that stays open." % spec["country"])


_FIRST = {
    "dagestan": ("Ruslan", "Magomed", "Shamil", "Islam", "Zubaira"),
    "thailand": ("Somchai", "Anan", "Kiet", "Nattapong"),
    "brazil": ("Rafael", "Bruno", "Thiago", "Vinicius"),
    "usa": ("Marcus", "Dwayne", "Cody", "Tyrell"),
    "kyrgyzstan": ("Aibek", "Nurlan", "Ulan", "Erlan"),
}
_LAST = {
    "dagestan": ("Gadzhiev", "Nurmagomedov", "Abdulaev", "Magomedov"),
    "thailand": ("Sitthichai", "Kaewsamrit", "Petchyindee"),
    "brazil": ("Almeida", "Ferreira", "Souza", "Barbosa"),
    "usa": ("Hall", "Rivera", "Brooks", "Coleman"),
    "kyrgyzstan": ("Toktogulov", "Osmonov", "Bekturov"),
}


def _person_name(spec: dict) -> str:
    cid = spec["id"]
    return "%s %s" % (random.choice(_FIRST.get(cid, ("Alex",))),
                      random.choice(_LAST.get(cid, ("Petrov",))))


def connection_bonus(fighter, org: str = "", country: str = "") -> int:
    """What your contacts abroad are actually worth.

    This is the payoff the old system never had: connections now feed
    matchmaking reach and cornering quality instead of sitting unread.
    """
    total = 0
    for c in (getattr(fighter, "connections", None) or []):
        if not isinstance(c, dict):
            continue
        s = int(c.get("strength", 50) or 50)
        if country and str(c.get("place_name", "")).endswith(country):
            total += s // 10
        if c.get("role") == "matchmaker":
            total += s // 20
    return int(total)


def corner_quality(fighter) -> int:
    """A coach met abroad improves your corner between rounds."""
    best = 0
    for c in (getattr(fighter, "connections", None) or []):
        if isinstance(c, dict) and c.get("role") == "coach":
            best = max(best, int(c.get("strength", 50) or 50))
    return best


def summary(fighter) -> str:
    conns = [c for c in (getattr(fighter, "connections", None) or []) if isinstance(c, dict)]
    if not conns:
        return "No contacts abroad."
    bits = []
    for c in conns[-4:]:
        bits.append("%s (%s, %s)" % (c.get("who", "?"), c.get("role", "?"),
                                     str(c.get("place_name", "")).split(",")[-1].strip()))
    return "; ".join(bits)
