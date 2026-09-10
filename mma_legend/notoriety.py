"""One public-notoriety service for fame, audience, hype and media gates."""
from __future__ import annotations


def add_fame(fighter, amount: int, reason: str = "") -> int:
    before = max(0, min(100, int(getattr(fighter, "fame", 0) or 0)))
    after = max(0, min(100, before + int(amount or 0)))
    fighter.fame = after
    if reason and after != before:
        flags = getattr(fighter, "story_flags", None)
        if not isinstance(flags, dict):
            fighter.story_flags = {}
            flags = fighter.story_flags
        log = list(flags.get("fame_log") or [])
        log.append({"week": int(getattr(fighter, "week", 0) or 0),
                    "delta": after - before, "reason": str(reason)[:60]})
        flags["fame_log"] = log[-30:]
    return after - before


def add_followers(fighter, amount: int) -> int:
    before = max(0, int(getattr(fighter, "followers", 0) or 0))
    fighter.followers = max(0, before + int(amount or 0))
    return fighter.followers - before


def decay_week(fighter) -> None:
    """Fame is recognition, followers are audience, hype is temporary heat."""
    week = int(getattr(fighter, "week", 1) or 1)
    if week % 6 == 0 and int(getattr(fighter, "fame", 0) or 0) > 0:
        protected = 8 if getattr(fighter, "pro_debut", False) else 0
        fighter.fame = max(protected, int(fighter.fame) - 1)
    if week % 2 == 0:
        fighter.press_hype = max(0, int(getattr(fighter, "press_hype", 0) or 0) - 2)


def media_tier(fighter, booked=None) -> str:
    booked = booked or getattr(fighter, "booked_fight", None) or {}
    if not getattr(fighter, "pro_debut", False):
        return "amateur"
    org = str(booked.get("org") or getattr(fighter, "organization", "") or "")
    fame = int(getattr(fighter, "fame", 0) or 0)
    if booked.get("title") or org == "UFC" and (booked.get("slot") in ("main", "co-main") or fame >= 35):
        return "major"
    if org in ("UFC", "PFL", "Bellator", "KSW", "Cage Warriors") or fame >= 16:
        return "featured"
    return "low"


def should_press(fighter, booked=None) -> bool:
    return media_tier(fighter, booked) == "major"


def should_interview(fighter, booked=None) -> bool:
    return media_tier(fighter, booked) in ("featured", "major")


def bout_fame(fighter, opponent, *, result: str, finish: bool, booked=None) -> int:
    tier = media_tier(fighter, booked)
    base = {"amateur": 0, "low": 0, "featured": 1, "major": 2}[tier]
    if str(result).lower().startswith("w"):
        base += 1
        if finish:
            base += 1
        my_wins = int((getattr(fighter, "pro_record", [0]) or [0])[0])
        opp_wins = int((getattr(opponent, "pro_record", [0]) or [0])[0])
        if opp_wins >= my_wins + 5:
            base += 1
    elif tier == "major":
        base += 1
    if (booked or {}).get("title"):
        base += 3 if str(result).lower().startswith("w") else 1
    return max(0, min(7, base))


def amateur_title_fame(label: str) -> int:
    """Amateur success creates recognition, but cannot manufacture stardom."""
    name = str(label or "").lower()
    if "world" in name or "immaf" in name:
        return 8
    if "europe" in name or "continental" in name:
        return 5
    if "national" in name:
        return 3
    if "adcc" in name:
        return 4
    return 1
