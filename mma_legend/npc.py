"""Unified NPC layer (1.10).

Everyone in this world who is not the player — promoters, managers,
matchmakers, media, coaches and fighters — is an NPC with the same underlying
shape. What differs is the ROLE they currently occupy, not the kind of thing
they are. A fighter who retires can become a coach; a coach with contacts can
become a manager; a manager who buys a promotion becomes a promoter. This
module is the common ground that makes those transitions possible later
without rewriting every system.

Design notes:

* **Traits are derived, not stored.** A person's personality comes from a
  seeded RNG keyed on their stable id, so the same id always yields the same
  character. That means no new save fields, no migration, and NPCs stay
  consistent across sessions for free. `Person` can stay a frozen dataclass.
* **One vocabulary.** `profile()` returns the same structure whether you hand
  it a `Person` or a `Fighter`, so UI and AI code can treat any NPC the same
  way.
* **Roles are data.** `ROLES` describes what each role cares about, which is
  what lets a role change be a data change rather than a class change.
"""
from __future__ import annotations

import random

# ---------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------

ROLES = {
    "fighter": {
        "label": "Fighter",
        "cares": ("winning", "purse", "ranking"),
        "color": "cyan",
    },
    "coach": {
        "label": "Coach",
        "cares": ("development", "loyalty", "gym"),
        "color": "green",
    },
    "manager": {
        "label": "Manager",
        "cares": ("purse", "career arc", "leverage"),
        "color": "yellow",
    },
    "promoter": {
        "label": "Promoter",
        "cares": ("ticket sales", "storylines", "loyalty"),
        "color": "magenta",
    },
    "matchmaker": {
        "label": "Matchmaker",
        "cares": ("competitive cards", "activity", "reliability"),
        "color": "blue",
    },
    "media": {
        "label": "Media",
        "cares": ("access", "a quote", "narrative"),
        "color": "gray",
    },
}

# Which roles a given role can plausibly move into. Used by the (future)
# career-transition system; kept here so the data lives with the roles.
ROLE_TRANSITIONS = {
    "fighter": ("coach", "manager", "promoter", "media"),
    "coach": ("manager", "promoter"),
    "manager": ("promoter",),
    "matchmaker": ("promoter",),
    "media": ("promoter",),
    "promoter": (),
}

# ---------------------------------------------------------------------
# Personality
# ---------------------------------------------------------------------

# Traits are paired opposites; an NPC gets one from each axis it rolls for.
TRAIT_AXES = [
    ("blunt", "diplomatic"),
    ("loyal", "opportunistic"),
    ("patient", "impatient"),
    ("generous", "tight-fisted"),
    ("calm", "hot-headed"),
    ("meticulous", "improvisational"),
    ("humble", "arrogant"),
    ("superstitious", "clinical"),
]

# Flavour traits that are not on an axis — an NPC may have none of these.
COLOUR_TRAITS = (
    "old-school", "film junkie", "gym rat", "night owl", "family first",
    "grudge holder", "talent spotter", "workaholic", "gambler",
    "straight talker", "showman", "quiet", "late bloomer", "film-study nerd",
    "weight-cut gremlin", "crowd worker", "silent assassin", "gym politician",
)

# What an NPC is actually good at. Same keys for everyone; a fighter and a
# manager simply score very differently.
COMPETENCIES = (
    "judgement",      # reads a situation correctly
    "negotiation",    # gets a better number
    "technical",      # understands the sport itself
    "politics",       # works the organisation
    "loyalty",        # sticks by people
    "hustle",         # makes things happen
)

ROLE_COMPETENCY_BIAS = {
    "fighter": {"technical": 18, "hustle": 8},
    "coach": {"technical": 22, "judgement": 12, "loyalty": 10},
    "manager": {"negotiation": 22, "politics": 14, "hustle": 12},
    "promoter": {"politics": 20, "negotiation": 14, "hustle": 14},
    "matchmaker": {"judgement": 22, "technical": 12, "politics": 10},
    "media": {"hustle": 16, "politics": 12, "judgement": 8},
}


def _seed_for(npc_id: str) -> int:
    """Stable numeric seed from any id string."""
    h = 0
    for ch in str(npc_id or "anon"):
        h = (h * 131 + ord(ch)) & 0x7FFFFFFF
    return h


def npc_id(obj) -> str:
    """The stable id of any NPC, Person or Fighter."""
    for attr in ("id", "fid"):
        val = getattr(obj, attr, None)
        if val:
            return str(val)
    return str(getattr(obj, "name", "anon"))


def role_of(obj) -> str:
    role = getattr(obj, "role", None)
    if role:
        return str(role)
    # A Fighter has no `role` field; if it walks like a fighter, it is one.
    if hasattr(obj, "pro_record") or hasattr(obj, "amateur_record"):
        return "fighter"
    return "fighter"


def traits(obj, n: int = 5) -> list:
    """Deterministic personality traits. Player included — same function."""
    stored = getattr(obj, "traits", None)
    if isinstance(stored, list) and len(stored) >= 3:
        return stored
    rng = random.Random(_seed_for(npc_id(obj)) ^ 0xA5A5)
    axes = list(TRAIT_AXES)
    rng.shuffle(axes)
    out = [rng.choice(pair) for pair in axes[:max(2, min(n, len(axes)))]]
    extra = 1 if rng.random() < 0.75 else 2
    bag = list(COLOUR_TRAITS)
    rng.shuffle(bag)
    out.extend(bag[:extra])
    try:
        obj.traits = out
    except Exception:
        pass
    return out


def competencies(obj) -> dict:
    """Deterministic 0-100 competency scores, biased by role."""
    rid = npc_id(obj)
    rng = random.Random(_seed_for(rid) ^ 0x5EED)
    role = role_of(obj)
    bias = ROLE_COMPETENCY_BIAS.get(role, {})
    out = {}
    for key in COMPETENCIES:
        base = rng.randint(25, 70) + bias.get(key, 0)
        out[key] = max(5, min(99, base))
    # A fighter's technical score should reflect their actual skills, not a
    # dice roll, when we have them.
    try:
        from . import constants as C
        vals = [int(getattr(obj, s)) for s in C.SKILLS if hasattr(obj, s)]
        if vals:
            out["technical"] = max(5, min(99, int(sum(vals) / len(vals))))
    except Exception:
        pass
    return out


def temperament(obj) -> str:
    """One-word summary used in short UI lines."""
    t = traits(obj, 3)
    for key in ("hot-headed", "arrogant", "opportunistic", "blunt"):
        if key in t:
            return key
    for key in ("calm", "patient", "loyal", "diplomatic"):
        if key in t:
            return key
    return t[0] if t else "even"


def profile(obj) -> dict:
    """The common NPC view. Works for Person and Fighter alike."""
    role = role_of(obj)
    spec = ROLES.get(role, ROLES["fighter"])
    return {
        "id": npc_id(obj),
        "name": getattr(obj, "name", "?"),
        "role": role,
        "role_label": spec["label"],
        "color": spec["color"],
        "cares": spec["cares"],
        "traits": traits(obj),
        "competencies": competencies(obj),
        "temperament": temperament(obj),
        "archetype": getattr(obj, "archetype", "") or "",
        "quirk": getattr(obj, "quirk", "") or "",
        "org": getattr(obj, "org", None) or getattr(obj, "organization", None),
        "country": getattr(obj, "country", None),
        "style": getattr(obj, "style", None),
        "techniques": list(getattr(obj, "techniques", None) or []),
    }


def trait_line(obj) -> str:
    """Comma-joined traits for a one-line display."""
    return ", ".join(traits(obj))


def describe(obj) -> str:
    """A short human sentence about any NPC."""
    p = profile(obj)
    bits = [p["role_label"]]
    if p["archetype"]:
        bits.append(p["archetype"])
    if p["org"]:
        bits.append(str(p["org"]))
    if p["style"] and p["role"] == "fighter":
        bits.append(str(p["style"]))
    return "%s — %s. %s." % (p["name"], " · ".join(bits), ", ".join(p["traits"]).capitalize())


def top_competencies(obj, n: int = 2) -> list:
    c = competencies(obj)
    return sorted(c, key=lambda k: c[k], reverse=True)[:n]


def can_become(obj, new_role: str) -> bool:
    """Whether this NPC could plausibly move into `new_role` later."""
    return new_role in ROLE_TRANSITIONS.get(role_of(obj), ())


def transition_role(obj, new_role: str) -> bool:
    """Move an NPC into a new role in place, where the object allows it.

    Frozen records (Person) cannot be mutated, so this returns False for them;
    the caller should build a replacement. Kept here so the rule lives in one
    place when the retire-into-coaching system arrives.
    """
    if new_role not in ROLES:
        return False
    try:
        object.__setattr__(obj, "role", new_role)
        return True
    except Exception:
        return False
