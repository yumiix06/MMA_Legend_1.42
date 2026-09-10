"""Loads the game's external JSON content (countries, opponents, events, ...).

Keeping this in one module means the rest of the codebase never has to know
or care whether a JSON file failed to load — it just gets a sane default.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


def load_json(filename: str, default: Any) -> Any:
    path = DATA_DIR / filename
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return default
        return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
        return default


COUNTRIES = load_json("countries.json", [
    {"name": "USA", "flag": "🇺🇸", "bonus": {"wrestling": 3, "striking": 1}},
])

OPPONENTS = load_json("opponents.json", [
    {"firstName": "John", "lastName": "Doe", "country": "USA", "team": "Team Alpha",
     "style": "Balanced", "personality": "balanced", "baseWins": 2, "baseLosses": 1},
])

EVENT_DATABASE = load_json("events.json", [
    {"id": 1, "title": "Family Support", "description": "Your family calls.",
     "category": "life", "trigger": {"type": "random", "chance": 0.3},
     "effects": {"happiness": 10, "confidence": 5}, "choices": None, "min_age": 0},
])

_TECHNIQUES_RAW = load_json("techniques.json", [
    {"id": 1, "name": "Jab", "discipline": "Boxing", "prerequisite": None,
     "bonus": {"striking": 2}, "cost": 1},
])
from .techniques import playable_rows
TECHNIQUES_DB = playable_rows(_TECHNIQUES_RAW)

GYM_AND_PROMOTIONS = load_json("gym_and_promotions.json", {})
COACHES_DB = GYM_AND_PROMOTIONS.get("coaches", [
    {"id": 1, "name": "Striking Coach", "cost": 200, "boost": "striking", "boost_percent": 50},
])
PROMOTIONS = GYM_AND_PROMOTIONS.get("promotions", [])

CAREER_AND_SPONSORS = load_json("career_and_sponsors.json", {})
SPONSORS_DB = CAREER_AND_SPONSORS.get("sponsors", [
    {"id": 1, "name": "Local Gym", "min_fame": 0, "money": 100,
     "obligation": "post logo", "fame_req": 0},
])
TOURNAMENTS_DB = CAREER_AND_SPONSORS.get("amateur_tournaments", [
    {"level": "Local", "min_wins": 0, "min_reputation": 0,
     "prize": 200, "fame": 5, "opponents": 3},
])
PRO_ORGS = CAREER_AND_SPONSORS.get("pro_organizations", [])

COACH_PROFILES = load_json("coaches.json", {"personalities": ["Tactical"], "pools": {}})

ARCHETYPES = load_json("fighter_archetypes.json", [])
COMBAT_MOMENTS = load_json("combat_moments.json", [])
NUTRITION_PLANS = load_json("nutrition.json", {}).get("meal_plans", [])
TRAINING_CAMPS = load_json("training_camps.json", {})
DOPING_RULES = load_json("doping_rules.json", {})


def country_by_name(name: str) -> dict:
    return next((c for c in COUNTRIES if c["name"] == name), COUNTRIES[0])


def archetype_by_name(name: str | None) -> dict | None:
    if not name:
        return None
    return next((a for a in ARCHETYPES if a["name"] == name), None)


def _validate_data_core() -> list[str]:
    errors=[]
    country_names={c.get("name") for c in COUNTRIES}
    seen=set()
    for o in OPPONENTS:
        name=f"{o.get('firstName','')} {o.get('lastName','')}".strip()
        if name in seen: errors.append(f"duplicate opponent: {name}")
        seen.add(name)
        if o.get("country") not in country_names: errors.append(f"unknown opponent country: {o.get('country')}")
    tech_names={t.get("name") for t in TECHNIQUES_DB}
    for t in TECHNIQUES_DB:
        if t.get("prerequisite") and t["prerequisite"] not in tech_names: errors.append(f"missing technique prerequisite: {t['name']} -> {t['prerequisite']}")
    return errors

def sponsor_conflict(sponsor_name: str, current: list[str]) -> bool:
    groups=[{"Pepsi","Coca-Cola"},{"Nike","Adidas","Puma","Under Armour"},{"Monster Energy","Gatorade","Coca-Cola","Pepsi"}]
    for group in groups:
        if sponsor_name in group and any(x in group and x != sponsor_name for x in current): return True
    return False


EVENTS_V06 = load_json("events_v06.json", [])
EVENTS_V07 = load_json("events_v07.json", [])
EVENTS_V08 = load_json("events_v08.json", [])
EVENTS_V14 = load_json("events_v14.json", [])
EVENTS_V15 = load_json("events_v15.json", [])
EVENTS_V19 = load_json("events_v19.json", [])
EVENTS_V111 = load_json("events_v111.json", [])
EVENTS_V121 = load_json("events_v121.json", [])
EVENTS_V123 = load_json("events_v123.json", [])
EVENTS_V125 = load_json("events_v125.json", [])
EVENTS_V127 = load_json("events_v127.json", [])
EVENTS_V141 = load_json("events_v141.json", [])
EVENTS_V142 = load_json("events_v142.json", [])


def event_packs() -> list[tuple[str, list]]:
    """Every event source, in stable oldest-to-newest order."""
    return [
        ("events", list(EVENT_DATABASE)),
        ("v06", list(EVENTS_V06)), ("v07", list(EVENTS_V07)),
        ("v08", list(EVENTS_V08)), ("v14", list(EVENTS_V14)),
        ("v15", list(EVENTS_V15)), ("v19", list(EVENTS_V19)),
        ("v111", list(EVENTS_V111)), ("v121", list(EVENTS_V121)),
        ("v123", list(EVENTS_V123)), ("v125", list(EVENTS_V125)),
        ("v127", list(EVENTS_V127)), ("v141", list(EVENTS_V141)), ("v142", list(EVENTS_V142)),
    ]


def all_events(newest_first: bool = False) -> list[dict]:
    packs = event_packs()
    if newest_first:
        packs.reverse()
    return [event for _label, pack in packs for event in pack]

_STORY = load_json("story_chains.json", {"chains": []})
STORY_CHAINS = _STORY.get("chains", []) if isinstance(_STORY, dict) else []

BJJ_GYMS = GYM_AND_PROMOTIONS.get("bjj_gyms", [])
KB_GYMS = GYM_AND_PROMOTIONS.get("kb_gyms", [])
JUDO_GYMS = GYM_AND_PROMOTIONS.get("judo_gyms", [])
TKD_GYMS = GYM_AND_PROMOTIONS.get("tkd_gyms", [])


def validate_data() -> list[str]:
    errors = _validate_data_core()
    trigger_types = {"random", "nutrition", "doping", "record", "fame", "national_team", "conditional"}
    for _label, pack in event_packs():
        for e in pack:
            typ = (e.get("trigger") or {}).get("type")
            if typ and typ not in trigger_types:
                errors.append("unknown event trigger: %s" % typ)
    known_bonus = {
        "kickboxing", "kicks", "wrestling", "grappling", "bjj", "submissions", "judo", "sambo",
        "muaythai", "boxing", "taekwondo", "kungfu", "discipline", "adaptability", "fight_iq",
        "speed", "durability", "strength", "cardio", "striking", "ko_power", "takedown_def",
        "ground_control", "health", "confidence", "happiness",
    }
    for c in COUNTRIES:
        for k in (c.get("bonus") or {}):
            if k.lower() not in known_bonus:
                errors.append("unknown country bonus key %s:%s" % (c.get("name"), k))
    ids = set()
    for m in COMBAT_MOMENTS:
        mid = str(m.get("id"))
        if mid in ids:
            errors.append("duplicate combat moment id %s" % mid)
        ids.add(mid)
    return errors
