"""Contextual fighter nicknames. All are short enough for the phone UI."""
from __future__ import annotations

import random


NICKNAMES = (
    "Ace", "Anvil", "Apex", "Assassin", "Avalanche", "Badger", "Bandit", "Bear",
    "Beast", "Berserker", "Big Dog", "Black Ice", "Blizzard", "Boa", "Body Snatcher",
    "Bonecrusher", "Boom", "Brick", "Bruiser", "Bulldog", "Bullet", "Bull", "Buzzsaw",
    "Cannon", "Card Shark", "Caveman", "Chaos", "Chief", "Cobra", "Cold Blood",
    "Comet", "Crusher", "Cyclone", "Dagger", "Daredevil", "Dark Horse", "Deadshot",
    "Destroyer", "Diesel", "Doctor", "Dragon", "Dynamo", "Eagle", "Executioner",
    "Falcon", "Firestorm", "Flash", "Freight Train", "Frost", "Ghost", "Giant",
    "Gladiator", "Golden Boy", "Gorilla", "Gravedigger", "Grinder", "Hammer", "Havoc",
    "Hawk", "Head Hunter", "Hitman", "Hurricane", "Ice Man", "Iron", "Jaguar",
    "Juggernaut", "King", "Kraken", "Last Samurai", "Lion", "Lone Wolf", "Machine",
    "Maestro", "Marauder", "Matador", "Mauler", "Maverick", "Menace", "Mercenary",
    "Nightmare", "Nomad", "Outlaw", "Panther", "Pitbull", "Predator", "Prince",
    "Punisher", "Python", "Razor", "Reaper", "Redline", "Rhino", "Rock", "Ronin",
    "Ruthless", "Savage", "Scorpion", "Shadow", "Shark", "Sledgehammer", "Sniper",
    "Spartan", "Spider", "Steamroller", "Storm", "Striker", "Tank", "Technician",
    "Terminator", "Thunder", "Tiger", "Titan", "Tornado", "Trouble", "Viking",
    "Viper", "War Horse", "Warrior", "Wildcat", "Wolf", "Wolverine", "Wrecking Ball",
    "Young Gun", "The Anchor", "The Artist", "The Answer", "The Blade", "The Butcher",
    "The Captain", "The Cat", "The Chosen", "The Collector", "The General", "The Hunter",
    "The Natural", "The Phenom", "The Professor", "The Prospect", "The Surgeon",
    "The Tsunami", "The Wall", "The Wizard", "The Workhorse", "Zero Mercy",
)


def eligible(fighter) -> bool:
    pro = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    medals = getattr(fighter, "sport_medals", None) or {}
    gold = sum(int(v.get("gold", 0) or 0) for v in medals.values() if isinstance(v, dict))
    return bool(pro[0] >= 3 or int(getattr(fighter, "fame", 0) or 0) >= 10 or gold)


def suggestions(fighter, used=None, count: int = 3) -> list[str]:
    used = {str(x).lower() for x in (used or []) if x}
    preferred = []
    if int(getattr(fighter, "ko_power", 0) or 0) >= 65:
        preferred += ["Cannon", "Hammer", "Body Snatcher", "Wrecking Ball", "Thunder"]
    if int(getattr(fighter, "submissions", 0) or 0) >= 65:
        preferred += ["Boa", "Python", "Spider", "The Surgeon", "The Wizard"]
    if int(getattr(fighter, "grappling", 0) or 0) >= 65:
        preferred += ["Anvil", "The Anchor", "Grinder", "Steamroller", "The Wall"]
    if int(getattr(fighter, "speed", 0) or 0) >= 65:
        preferred += ["Bullet", "Flash", "Comet", "Dagger", "Redline"]
    bag = [x for x in preferred + list(NICKNAMES) if x.lower() not in used]
    # Stable de-duplication before sampling.
    bag = list(dict.fromkeys(bag))
    random.shuffle(bag)
    return bag[:max(1, count)]


def used_in_org(pool, organization: str) -> set[str]:
    return {str(getattr(f, "nickname", "") or "") for f in getattr(pool, "fighters", [])
            if getattr(f, "organization", None) == organization and getattr(f, "nickname", None)}


def assign_npc(fighter, pool=None) -> str | None:
    if getattr(fighter, "nickname", None) or not eligible(fighter):
        return getattr(fighter, "nickname", None)
    used = used_in_org(pool, getattr(fighter, "organization", "")) if pool else set()
    picks = suggestions(fighter, used, 1)
    if picks:
        fighter.nickname = picks[0]
    return getattr(fighter, "nickname", None)


def offer_player(console, fighter, pool=None) -> bool:
    if getattr(fighter, "nickname", None) or not eligible(fighter):
        return False
    flags = getattr(fighter, "story_flags", None) or {}
    if int(flags.get("nickname_offer_week", -99) or -99) + 12 > int(getattr(fighter, "week", 0) or 0):
        return False
    used = used_in_org(pool, getattr(fighter, "organization", "")) if pool else set()
    picks = suggestions(fighter, used, 3)
    fighter.nickname_choices = picks
    console.header("FIGHTER IDENTITY", "The crowd is trying out a name")
    for i, name in enumerate(picks, 1):
        console.print("  %s) %s" % (i, name))
    console.print("  C) Enter a custom nickname")
    console.print("  X) Not yet")
    raw = console.ask("Nickname > ").strip()
    chosen = None
    if raw.upper() == "C":
        custom = console.ask("Custom (max 18 chars) > ").strip()
        if custom:
            chosen = custom[:18]
    elif raw.isdigit() and 1 <= int(raw) <= len(picks):
        chosen = picks[int(raw) - 1]
    flags["nickname_offer_week"] = int(getattr(fighter, "week", 0) or 0)
    fighter.story_flags = flags
    if chosen:
        fighter.nickname = chosen
        console.gold('%s "%s" %s' % (fighter.name.split()[0], chosen, fighter.name.split()[-1]))
        return True
    return False


def display_name(fighter) -> str:
    nick = str(getattr(fighter, "nickname", "") or "").strip()
    name = str(getattr(fighter, "name", "Fighter") or "Fighter")
    if not nick:
        return name
    parts = name.split()
    return '%s "%s" %s' % (parts[0], nick, parts[-1]) if len(parts) > 1 else '%s "%s"' % (name, nick)
