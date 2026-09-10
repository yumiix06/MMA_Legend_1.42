"""Auto-granted fight perks. Cap 3. No take/skip screen."""
from __future__ import annotations

PERKS = {
    "cut_artist": "Cut Artist",
    "grinder": "Grinder",
    "first_min": "First Minute",
    "wrestle_chain": "Chain Wrestler",
    "body_work": "Body Work",
    "iron_chin": "Iron Chin",
    "home_crowd": "Home Card",
    "film_room": "Film Room",
    "late_gas": "Late Gas",
    "glass": "Glass",
}

CAP = 3


def has(fighter, pid: str) -> bool:
    return pid in list(getattr(fighter, "perks", None) or [])


def grant(fighter, pid: str, console=None) -> bool:
    cur = list(getattr(fighter, "perks", None) or [])
    if pid in cur or len(cur) >= CAP:
        return False
    if pid == "glass" and len(cur) >= CAP:
        return False
    cur.append(pid)
    fighter.perks = cur
    label = PERKS.get(pid, pid)
    if console:
        console.gold("Perk: %s" % label)
    # Do not erase the fight result from last_week_note.  The 1.23 playtest
    # ended a KO loss as "perk Glass", which made session logs/save headers
    # forget what actually consumed the week.  Keep perk identity separately.
    flags = fighter.story_flags if isinstance(getattr(fighter, "story_flags", None), dict) else {}
    flags["last_perk"] = {"id": pid, "label": label, "week": int(getattr(fighter, "week", 0) or 0)}
    fighter.story_flags = flags
    try:
        from . import telemetry
        telemetry.system("perk_granted", perk=pid, label=label, week=int(getattr(fighter, "week", 0) or 0))
    except Exception:
        pass
    return True


def evaluate(fighter, console=None, bout=None) -> None:
    """Call after a fight. Silent except a gold line when granted."""
    flags = fighter.story_flags if isinstance(getattr(fighter, "story_flags", None), dict) else {}
    fighter.story_flags = flags
    am = sum(fighter.amateur_record or [0, 0, 0])
    pro = sum(fighter.pro_record or [0, 0, 0])

    if flags.get("made_weight_streak", 0) >= 3:
        grant(fighter, "cut_artist", console)
    if flags.get("decision_wins", 0) >= 3:
        grant(fighter, "grinder", console)
    if flags.get("r1_finishes", 0) >= 2:
        grant(fighter, "first_min", console)
    if flags.get("td_career", 0) >= 5:
        grant(fighter, "wrestle_chain", console)
    if flags.get("body_shots", 0) >= 40:
        grant(fighter, "body_work", console)
    if flags.get("kd_survive_wins", 0) >= 2:
        grant(fighter, "iron_chin", console)
    if flags.get("home_wins", 0) >= 3:
        grant(fighter, "home_crowd", console)
    if int(getattr(fighter, "fight_iq", 0) or 0) >= 55 and am + pro >= 6:
        grant(fighter, "film_room", console)
    if flags.get("comeback_wins", 0) >= 1:
        grant(fighter, "late_gas", console)
    if flags.get("ko_losses", 0) >= 2 and len(getattr(fighter, "perks", None) or []) < CAP:
        grant(fighter, "glass", console)


def note_bout(fighter, bout, result: str, opponent) -> None:
    flags = fighter.story_flags if isinstance(getattr(fighter, "story_flags", None), dict) else {}
    if result == "Win":
        if bout and not getattr(bout, "finish_label", None):
            flags["decision_wins"] = int(flags.get("decision_wins", 0)) + 1
        if bout and getattr(bout, "end_period", 0) == 1 and getattr(bout, "finish_label", None):
            flags["r1_finishes"] = int(flags.get("r1_finishes", 0)) + 1
        if getattr(opponent, "country", "") == getattr(fighter, "country", ""):
            flags["home_wins"] = int(flags.get("home_wins", 0)) + 1
        if bout and getattr(bout, "f_stats", None) and getattr(bout.f_stats, "knockdowns", 0) == 0:
            if getattr(bout, "o_stats", None) and bout.o_stats.knockdowns:
                flags["kd_survive_wins"] = int(flags.get("kd_survive_wins", 0)) + 1
        if bout and getattr(bout, "end_period", 0) >= 3:
            flags["comeback_wins"] = int(flags.get("comeback_wins", 0)) + 1
    if result == "Loss" and bout and (bout.method or "") in ("KO", "TKO"):
        flags["ko_losses"] = int(flags.get("ko_losses", 0)) + 1
    if bout and getattr(bout, "f_stats", None):
        flags["td_career"] = int(flags.get("td_career", 0)) + int(bout.f_stats.takedowns_landed or 0)
        flags["body_shots"] = int(flags.get("body_shots", 0)) + int(bout.f_stats.body_landed or 0)
    if not getattr(fighter, "_chose_cut", False):
        flags["made_weight_streak"] = int(flags.get("made_weight_streak", 0)) + 1
    elif "weight_trouble" in list(getattr(fighter, "narrative_tags", None) or []):
        flags["made_weight_streak"] = 0
    else:
        flags["made_weight_streak"] = int(flags.get("made_weight_streak", 0)) + 1
    fighter.story_flags = flags

# ---------------------------------------------------------------------------
# 1.24 gameplay consumption
# ---------------------------------------------------------------------------
# Perks are intentionally *small*.  They reward demonstrated habits without
# replacing the attributes that caused those habits in the first place.

def accuracy_bonus(fighter, action: str, period: int = 1) -> float:
    bonus = 0.0
    if has(fighter, "film_room"):
        bonus += 0.010
    if has(fighter, "wrestle_chain") and action in ("double_leg", "single_leg", "trip", "throw"):
        bonus += 0.020
    if has(fighter, "body_work") and action in ("liver", "body_kick", "side_kick", "spin_back_kick", "knee_body", "teep"):
        bonus += 0.018
    if has(fighter, "first_min") and int(period or 1) == 1 and action in ("cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
        bonus += 0.012
    return min(0.045, bonus)


def action_weight_multiplier(fighter, action: str, period: int = 1) -> float:
    m = 1.0
    if has(fighter, "wrestle_chain") and action in ("double_leg", "single_leg", "trip", "throw"):
        m *= 1.12
    if has(fighter, "body_work") and action in ("liver", "body_kick", "side_kick", "spin_back_kick", "knee_body", "teep"):
        m *= 1.12
    if has(fighter, "first_min") and int(period or 1) == 1 and action in ("cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
        m *= 1.08
    return m


def gas_cost_multiplier(fighter, period: int = 1) -> float:
    m = 1.0
    if has(fighter, "grinder"):
        m *= 0.975
    if has(fighter, "late_gas") and int(period or 1) >= 3:
        m *= 0.93
    return max(0.90, m)


def round_recovery_bonus(fighter, completed_period: int) -> int:
    bonus = 1 if has(fighter, "grinder") else 0
    if has(fighter, "late_gas") and int(completed_period or 1) >= 2:
        bonus += 2
    return bonus


def ko_received_multiplier(fighter) -> float:
    m = 1.0
    if has(fighter, "iron_chin"):
        m *= 0.88
    if has(fighter, "glass"):
        m *= 1.15
    return max(0.82, min(1.20, m))


def cut_chance_multiplier(fighter) -> float:
    return 1.30 if has(fighter, "cut_artist") else 1.0


def post_bout_career_bonus(fighter, opponent, result: str) -> dict:
    """Career-facing perk effects that do not belong in the combat engine."""
    out = {"fame": 0, "reputation": 0}
    if result == "Win" and has(fighter, "home_crowd"):
        if str(getattr(fighter, "country", "") or "") == str(getattr(opponent, "country", "") or ""):
            from .notoriety import add_fame
            add_fame(fighter, 1, "earned performance perk")
            fighter.reputation = min(100, int(getattr(fighter, "reputation", 0) or 0) + 1)
            out = {"fame": 1, "reputation": 1}
    return out
