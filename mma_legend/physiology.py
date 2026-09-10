"""Weight-class physiology and fight readiness (1.24).

This is the single source of truth for how body size, nutrition, weight cutting,
physique and injuries affect combat.  Raw skill attributes still represent what
a fighter has learned/developed; this module turns them into *effective* fight-
night attributes and enforces realistic ceilings on the physical attributes.

Design rules:
- Technical skill is trainable to 100 in every division.
- Mass raises strength/impact potential but taxes speed and sustained work.
- A weight class is not a free buff: every advantage has a trade-off.
- Nutrition/cuts/injuries alter current performance, never permanently rewrite
  learned technique.
- Matchup-size effects are deliberately small and capped so skill remains king.
"""
from __future__ import annotations

from typing import Dict

PHYSICAL_STATS = frozenset({"strength", "ko_power", "cardio", "speed"})

# Caps + expression multipliers.  The cap spread is intentionally meaningful
# but not enormous: an exceptional Heavyweight can still be fast, and an
# exceptional Flyweight can still hit hard; their biological ceilings differ.
WEIGHT_PROFILES: Dict[str, dict] = {
    "Flyweight":          {"strength": 88, "ko_power": 90,  "cardio": 100, "speed": 100, "impact": 0.95, "gas": 0.93, "start": (-5, -4,  5,  5)},
    "Bantamweight":       {"strength": 90, "ko_power": 92,  "cardio": 100, "speed": 100, "impact": 0.97, "gas": 0.95, "start": (-4, -3,  4,  4)},
    "Featherweight":      {"strength": 92, "ko_power": 94,  "cardio": 99,  "speed": 99,  "impact": 0.985,"gas": 0.97, "start": (-2, -2,  3,  3)},
    "Lightweight":        {"strength": 94, "ko_power": 96,  "cardio": 98,  "speed": 98,  "impact": 1.00, "gas": 0.99, "start": ( 0,  0,  2,  2)},
    "Welterweight":       {"strength": 96, "ko_power": 98,  "cardio": 96,  "speed": 96,  "impact": 1.02, "gas": 1.02, "start": ( 2,  1,  0,  0)},
    "Middleweight":       {"strength": 98, "ko_power": 100, "cardio": 94,  "speed": 94,  "impact": 1.04, "gas": 1.06, "start": ( 4,  3, -2, -2)},
    "Light Heavyweight":  {"strength": 100,"ko_power": 100, "cardio": 91,  "speed": 91,  "impact": 1.065,"gas": 1.10, "start": ( 6,  5, -4, -4)},
    "Heavyweight":        {"strength": 100,"ko_power": 100, "cardio": 88,  "speed": 88,  "impact": 1.09, "gas": 1.14, "start": ( 8,  7, -6, -6)},
}

DEFAULT_PROFILE = WEIGHT_PROFILES["Lightweight"]

# Physique modifies ceilings very slightly.  It must never overwhelm division.
PHYSIQUE_CAP_MOD = {
    "Lean":        {"strength": -2, "ko_power": -1, "cardio": 1, "speed": 1},
    "Athletic":    {},
    "Stocky":      {"strength": 2, "ko_power": 1, "cardio": -1, "speed": -2},
    "Tall":        {"strength": -1, "cardio": 1, "speed": 1},
    "Heavy-built": {"strength": 3, "ko_power": 2, "cardio": -3, "speed": -3},
    "Compact":     {"strength": 1, "cardio": 1, "speed": 1},
}

# Injury -> affected combat stats and maximum penalty at severity 3.  Severity
# scales linearly.  Minor injuries may be fought through; serious ones are
# already blocked by damage.can_fight().
INJURY_PENALTIES = {
    "broken hand": {"striking": 18, "ko_power": 14, "grappling": 5},
    "broken knuckle": {"striking": 12, "ko_power": 10},
    "torn knee": {"speed": 18, "kicks": 18, "grappling": 12, "strength": 7},
    "dead leg": {"speed": 10, "kicks": 13, "grappling": 7},
    "ankle sprain": {"speed": 10, "kicks": 8, "grappling": 5},
    "cracked rib": {"cardio": 14, "durability": 10, "strength": 5},
    "torn shoulder": {"grappling": 16, "submissions": 12, "striking": 8, "strength": 9},
    "concussion": {"durability": 18, "speed": 8, "fight_iq": 8},
    "orbital fracture": {"durability": 15, "fight_iq": 6, "speed": 5},
    "jaw fracture": {"durability": 16, "fight_iq": 4},
    "broken nose": {"cardio": 5, "durability": 4},
    "deep cut": {"fight_iq": 3},
    "swollen eye": {"fight_iq": 5, "speed": 3},
    "bruised shin": {"kicks": 6, "speed": 3},
}


def weight_class(fighter) -> str:
    return str(getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", None) or "Lightweight")


def profile(fighter_or_wc) -> dict:
    wc = fighter_or_wc if isinstance(fighter_or_wc, str) else weight_class(fighter_or_wc)
    return WEIGHT_PROFILES.get(str(wc), DEFAULT_PROFILE)


def stat_cap(fighter, stat: str) -> int:
    """Development ceiling for a stat. Technical attributes remain 100."""
    if stat not in PHYSICAL_STATS:
        return 100
    p = profile(fighter)
    cap = int(p.get(stat, 100))
    phy = str(getattr(fighter, "physique_type", "Athletic") or "Athletic")
    cap += int(PHYSIQUE_CAP_MOD.get(phy, {}).get(stat, 0) or 0)
    return max(75, min(100, cap))


def clamp_stat(fighter, stat: str, value) -> int:
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        value = 0
    return max(0, min(stat_cap(fighter, stat), value))


def gain_stat(fighter, stat: str, amount) -> int:
    """Apply permanent training gain while respecting physical ceilings.

    Returns the actual amount gained. Non-combat fields are left to callers.
    """
    if not hasattr(fighter, stat):
        return 0
    try:
        cur = int(getattr(fighter, stat) or 0)
        amt = int(round(float(amount)))
    except (TypeError, ValueError):
        return 0
    new = clamp_stat(fighter, stat, cur + amt)
    setattr(fighter, stat, new)
    return new - cur


def class_start_adjustment(wc: str) -> dict:
    st, ko, ca, sp = WEIGHT_PROFILES.get(wc, DEFAULT_PROFILE)["start"]
    return {"strength": st, "ko_power": ko, "cardio": ca, "speed": sp}


def apply_class_baseline(fighter) -> None:
    """Creation-only physical identity for a division."""
    for stat, delta in class_start_adjustment(weight_class(fighter)).items():
        if hasattr(fighter, stat):
            setattr(fighter, stat, clamp_stat(fighter, stat, int(getattr(fighter, stat) or 0) + delta))


def target_stat_for_class(wc: str, stat: str, target: float) -> float:
    """Shape generated NPCs around the same target *quality* without making
    every division physically identical."""
    return float(target) + float(class_start_adjustment(wc).get(stat, 0))


def _nutrition_penalty(fighter, stat: str) -> float:
    n = max(0, min(100, int(getattr(fighter, "nutrition", 50) or 50)))
    if n >= 85:
        return -1.0 if stat in ("cardio", "speed", "durability") else 0.0  # negative penalty = small bonus
    if n >= 50:
        return 0.0
    deficit = (50 - n) / 10.0
    scale = {
        "cardio": 1.8, "speed": 1.0, "durability": 1.2,
        "strength": 0.6, "ko_power": 0.4, "fight_iq": 0.5,
    }.get(stat, 0.25)
    return deficit * scale


def _condition_penalty(fighter, stat: str) -> float:
    health = max(0, min(100, int(getattr(fighter, "health", 100) or 100)))
    cut = max(0, int(getattr(fighter, "cut_drain", 0) or 0))
    cut_health = max(0, min(100, int(getattr(fighter, "weight_cut_health", 100) or 100)))
    p = 0.0
    if health < 70:
        d = (70 - health) / 10.0
        p += d * {"cardio": 1.6, "durability": 1.7, "speed": 0.9,
                  "strength": 0.8, "ko_power": 0.5}.get(stat, 0.25)
    if cut:
        p += cut * {"cardio": 0.65, "speed": 0.32, "durability": 0.38,
                    "strength": 0.18, "ko_power": 0.12, "fight_iq": 0.08}.get(stat, 0.04)
    if cut_health < 70:
        d = (70 - cut_health) / 10.0
        p += d * {"cardio": 1.3, "durability": 1.1, "speed": 0.7,
                  "strength": 0.4}.get(stat, 0.15)
    return p


def _bodyfat_penalty(fighter, stat: str) -> float:
    try:
        bf = float(getattr(fighter, "bodyfat", 12.0) or 12.0)
    except (TypeError, ValueError):
        bf = 12.0
    phy = str(getattr(fighter, "physique_type", "Athletic") or "Athletic")
    floor = {"Lean": 7.5, "Athletic": 9.5, "Stocky": 12.0, "Tall": 9.5,
             "Heavy-built": 12.0, "Compact": 9.0}.get(phy, 9.5)
    p = 0.0
    # Too lean: depleted, fragile, weak.  Slightly above the physique floor is
    # healthy, so we do not reward starvation.
    if bf < floor - 1.2:
        d = (floor - 1.2 - bf)
        p += d * {"cardio": 1.3, "durability": 1.5, "strength": 0.8,
                  "ko_power": 0.5, "speed": 0.5}.get(stat, 0.1)
    # Excess fat mostly taxes locomotion and sustained output.
    soft_ceiling = floor + 7.0
    if bf > soft_ceiling:
        d = bf - soft_ceiling
        p += d * {"cardio": 0.9, "speed": 0.8, "durability": 0.15}.get(stat, 0.05)
    return p


def _injury_penalty(fighter, stat: str) -> float:
    inj = getattr(fighter, "injury", None) or {}
    name = str(inj.get("area", "") or "").lower()
    if not name:
        return 0.0
    sev = max(1, min(3, int(inj.get("severity", inj.get("sev", 1)) or 1)))
    table = INJURY_PENALTIES.get(name, {})
    return float(table.get(stat, 0)) * (sev / 3.0)


def _legacy_damage_penalty(fighter, stat: str) -> float:
    d = getattr(fighter, "damage", None) or {}
    head = max(0, int(d.get("head", 0) or 0))
    body = max(0, int(d.get("body", 0) or 0))
    legs = max(0, int(d.get("legs", 0) or 0))
    eyes = max(0, int(d.get("eyes", 0) or 0))
    p = 0.0
    if legs > 30:
        p += ((legs - 30) / 12.0) * ({"speed": 1.5, "kicks": 1.7, "grappling": 0.9}.get(stat, 0.0))
    if body > 30:
        p += ((body - 30) / 14.0) * ({"cardio": 1.5, "durability": 0.8}.get(stat, 0.0))
    if head > 30:
        p += ((head - 30) / 14.0) * ({"durability": 1.2, "fight_iq": 0.6, "speed": 0.4}.get(stat, 0.0))
    if eyes > 20:
        p += ((eyes - 20) / 12.0) * ({"fight_iq": 0.8, "striking": 0.5}.get(stat, 0.0))
    return p


def effective_stat(fighter, stat: str, default=40) -> int:
    """Fight-night value after class ceiling + current condition."""
    try:
        raw = int(getattr(fighter, stat, default) or default)
    except (TypeError, ValueError):
        raw = int(default)
    raw = min(raw, stat_cap(fighter, stat))
    penalty = (_nutrition_penalty(fighter, stat) + _condition_penalty(fighter, stat)
               + _bodyfat_penalty(fighter, stat) + _injury_penalty(fighter, stat)
               + _legacy_damage_penalty(fighter, stat))
    # v1.40 temporary performance modifiers affect fight-night expression only;
    # they never mutate the trained/raw attribute.
    temp_mod = 0
    try:
        from .performance import stat_modifier
        temp_mod = int(stat_modifier(fighter, stat))
    except Exception:
        temp_mod = 0
    value = int(round(raw + temp_mod - penalty))
    return max(5, min(stat_cap(fighter, stat), value))


def impact_multiplier(fighter) -> float:
    """Mass-expression multiplier on landed strike damage.

    Kept narrow because KO power already represents individual punching power.
    """
    p = float(profile(fighter).get("impact", 1.0))
    # Small physique expression, not a second stat system.
    phy = str(getattr(fighter, "physique_type", "Athletic") or "Athletic")
    p *= {"Lean": 0.985, "Athletic": 1.0, "Stocky": 1.015, "Tall": 1.0,
          "Heavy-built": 1.025, "Compact": 1.005}.get(phy, 1.0)
    return max(0.92, min(1.13, p))


def gas_cost_multiplier(fighter) -> float:
    p = float(profile(fighter).get("gas", 1.0))
    phy = str(getattr(fighter, "physique_type", "Athletic") or "Athletic")
    p *= {"Lean": 0.97, "Athletic": 1.0, "Stocky": 1.03, "Tall": 0.99,
          "Heavy-built": 1.05, "Compact": 0.98}.get(phy, 1.0)
    return max(0.88, min(1.20, p))


def fight_night_weight(fighter) -> float:
    """Rehydrated cage weight, if a weigh-in has been resolved."""
    val = getattr(fighter, "_fight_night_weight", None)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    try:
        return float(getattr(fighter, "walking_weight", None) or getattr(fighter, "weight", 70) or 70)
    except (TypeError, ValueError):
        return 70.0


def size_matchup_modifier(attacker, defender) -> float:
    """Small grappling/clinch advantage for fight-night size + height.

    ±0.08 is large enough to matter but nowhere near enough to erase skill.
    """
    dw = fight_night_weight(attacker) - fight_night_weight(defender)
    try:
        dh = float(getattr(attacker, "height", 175) or 175) - float(getattr(defender, "height", 175) or 175)
    except (TypeError, ValueError):
        dh = 0.0
    raw = dw / 85.0 + dh / 700.0
    phy = str(getattr(attacker, "physique_type", "Athletic") or "Athletic")
    raw *= {"Lean": 0.92, "Athletic": 1.0, "Stocky": 1.08, "Tall": 1.03,
            "Heavy-built": 1.10, "Compact": 1.04}.get(phy, 1.0)
    return max(-0.08, min(0.08, raw))


def scouting_accuracy_bonus(fighter) -> float:
    read = max(0, min(20, int(getattr(fighter, "opponent_read", 0) or 0)))
    return read / 800.0  # max +2.5 percentage points


def camp_accuracy_bonus(fighter) -> float:
    sharp = max(0, min(12, int(getattr(fighter, "camp_bonus", 0) or 0)))
    return sharp / 600.0  # max +2 pp; preparation matters, does not dominate


def technique_level_bonus(fighter, action: str, catalog: dict) -> float:
    """Accuracy bonus from the best learned technique mapped to this action."""
    levels = dict(getattr(fighter, "technique_levels", None) or {})
    best = 0
    for name, lvl in levels.items():
        spec = catalog.get(str(name).lower())
        if spec and spec[0] == action:
            try:
                best = max(best, int(lvl or 0))
            except (TypeError, ValueError):
                pass
    # L1 = familiar, L5 = mastered. Small enough to preserve attribute primacy.
    return {0: 0.0, 1: 0.0, 2: 0.010, 3: 0.020, 4: 0.032, 5: 0.045}.get(min(5, best), 0.0)


def action_skill(fighter, action: str) -> int:
    """The technical attribute that actually powers a standing strike."""
    if action in ("low_kick", "head_kick", "teep", "body_kick", "knee_body", "side_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
        return effective_stat(fighter, "kicks")
    if action in ("jab", "cross", "hook", "uppercut", "liver", "dirty_box", "gnp", "body_punch"):
        return effective_stat(fighter, "striking")
    return 0


def nutrition_week(fighter) -> dict:
    """Advance one week of the selected diet without instant-potion effects.

    Plans target a nutrition quality and produce gradual mass/recovery changes.
    Returns deltas for diagnostics/UI.
    """
    try:
        from . import data
        plans = list(getattr(data, "NUTRITION_PLANS", None) or [])
    except Exception:
        plans = []
    name = str(getattr(fighter, "meal_plan", None) or "Balanced Athlete")
    spec = next((p for p in plans if str(p.get("name")) == name), None) or {}
    target = int(spec.get("quality_target", 72) or 72)
    try:
        from .education import degree_benefit
        target = min(100, target + int(degree_benefit(fighter, "nutrition_bonus", 0) or 0))
    except Exception:
        pass
    current = max(0, min(100, int(getattr(fighter, "nutrition", 50) or 50)))
    step = max(1, int(spec.get("quality_step", 3) or 3))
    if current < target:
        new_n = min(target, current + step)
    elif current > target:
        new_n = max(target, current - step)
    else:
        new_n = current
    fighter.nutrition = new_n

    e = int(spec.get("weekly_energy", 0) or 0)
    h = int(spec.get("weekly_health", 0) or 0)
    happy = int(spec.get("weekly_happiness", 0) or 0)
    fighter.energy = max(0, min(100, int(getattr(fighter, "energy", 70) or 70) + e))
    fighter.health = max(0, min(100, int(getattr(fighter, "health", 70) or 70) + h))
    fighter.happiness = max(0, min(100, int(getattr(fighter, "happiness", 50) or 50) + happy))

    # Cut-health restores when fed/recovered and erodes under harsh dieting.
    cut_h = int(getattr(fighter, "weight_cut_health", 100) or 100)
    delta_cut = int(spec.get("cut_health", 0) or 0)
    if target >= 75 and not bool(getattr(fighter, "camp_active", False)):
        delta_cut += 1
    fighter.weight_cut_health = max(0, min(100, cut_h + delta_cut))
    return {"nutrition": new_n - current, "energy": e, "health": h,
            "happiness": happy, "cut_health": delta_cut}
