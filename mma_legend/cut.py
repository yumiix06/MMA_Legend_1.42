"""0.7 The Cut — physique, weight, injury, school, weekly costs."""
from __future__ import annotations

import random
from typing import Optional

from . import constants as C

PHYSIQUES = {
    "Lean": {"cut": 0.85, "gas": 1.08, "bully": 0.85},
    "Athletic": {"cut": 1.0, "gas": 1.0, "bully": 1.0},
    "Stocky": {"cut": 1.15, "gas": 0.92, "bully": 1.15},
    "Tall": {"cut": 1.05, "gas": 1.02, "bully": 1.08},
    "Heavy-built": {"cut": 1.25, "gas": 0.88, "bully": 1.22},
    "Compact": {"cut": 0.95, "gas": 1.04, "bully": 0.95},
}

CLASS_LIMIT = {
    "Flyweight": 56.7, "Bantamweight": 61.2, "Featherweight": 65.8,
    "Lightweight": 70.3, "Welterweight": 77.1, "Middleweight": 83.9,
    "Light Heavyweight": 93.0, "Heavyweight": 120.2,
}

# How much of the final reduction is intentionally left for fight-week water.
# The strategy changes the risk/size trade-off, not a hidden flat combat buff.
WEIGHT_STRATEGIES = {
    "performance": {"label": "Performance cut", "final_cut": 0.040,
                    "desc": "Lose real mass in camp; small water cut, best gas."},
    "balanced": {"label": "Balanced cut", "final_cut": 0.070,
                 "desc": "Moderate camp loss and moderate rehydration size."},
    "bully": {"label": "Weight bully", "final_cut": 0.105,
              "desc": "Stay heavier; bigger cage body, higher miss/gas risk."},
}

def weight_strategy(fighter) -> str:
    flags = getattr(fighter, "story_flags", None) or {}
    key = str(flags.get("weight_strategy") or "performance")
    return key if key in WEIGHT_STRATEGIES else "performance"

def target_walk_weight(fighter, strategy: str | None = None) -> float:
    """Desired pre-weigh-in walking mass, never a command to bulk for a cut.

    A weight strategy decides how much of an existing over-limit gap can be
    left for fight-week water. If the athlete already walks at/below the
    limit, the cut system is inactive and their current walking mass is target.
    """
    strategy = strategy or weight_strategy(fighter)
    frac = float(WEIGHT_STRATEGIES.get(strategy, WEIGHT_STRATEGIES["performance"])["final_cut"])
    wc = getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", None)
    walk = float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 70)) or getattr(fighter, "weight", 70))
    cap = float(CLASS_LIMIT.get(wc, walk))
    if walk <= cap + 0.15:
        return round(walk, 2)
    water_target = cap / max(0.82, 1.0 - frac)
    return round(min(walk, water_target), 2)

def meaningful_cut(fighter, margin: float = 0.75) -> bool:
    """True only when the booked/home division actually requires a cut."""
    fs = cut_feasibility(fighter)
    return bool(float(fs.get("gap", 0.0) or 0.0) >= float(margin))

def ensure_weight_campaign(fighter, reset: bool = False) -> dict:
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}; flags = fighter.story_flags
    camp = flags.get("weight_camp") if isinstance(flags.get("weight_camp"), dict) else None
    booked = getattr(fighter, "booked_fight", None) or {}
    fight_week = int(booked.get("date_week") or 0)
    if reset or camp is None or (fight_week and int(camp.get("fight_week") or 0) != fight_week):
        walk = float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 70)) or getattr(fighter, "weight", 70))
        wc = getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", None)
        camp = {
            "start_week": int(getattr(fighter, "week", 1) or 1),
            "fight_week": fight_week,
            "class": wc,
            "limit_kg": float(CLASS_LIMIT.get(wc, walk)),
            "start_walk_kg": round(walk, 2),
            "strategy": weight_strategy(fighter),
            "target_walk_kg": target_walk_weight(fighter),
            "history": [],
            "final": None,
        }
        flags["weight_camp"] = camp
    else:
        # v1.31 repair for legacy campaigns: old "bully" logic could cache a
        # target ABOVE the athlete's actual walking mass, fabricating kilograms
        # before the weigh-in. Campaign state is derived from the body now.
        walk = float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 70)) or getattr(fighter, "weight", 70))
        wc = getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", None)
        camp["class"] = wc
        camp["limit_kg"] = float(CLASS_LIMIT.get(wc, walk))
        camp["strategy"] = weight_strategy(fighter)
        camp["target_walk_kg"] = target_walk_weight(fighter, camp["strategy"])
        if float(camp.get("start_walk_kg", walk) or walk) > max(walk + 8.0, 130.0):
            camp["start_walk_kg"] = round(walk, 2)
    return camp

def set_weight_strategy(fighter, key: str) -> dict:
    key = key if key in WEIGHT_STRATEGIES else "performance"
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}; flags = fighter.story_flags
    flags["weight_strategy"] = key
    camp = ensure_weight_campaign(fighter)
    camp["strategy"] = key
    camp["target_walk_kg"] = target_walk_weight(fighter, key)
    return camp

def weight_campaign_summary(fighter) -> dict:
    camp = ensure_weight_campaign(fighter)
    walk = float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 70)) or getattr(fighter, "weight", 70))
    start = float(camp.get("start_walk_kg", walk) or walk)
    target = float(camp.get("target_walk_kg", target_walk_weight(fighter)) or target_walk_weight(fighter))
    now = int(getattr(fighter, "week", 1) or 1)
    start_week = int(camp.get("start_week", now) or now)
    fight_week = int(camp.get("fight_week", 0) or 0)
    weeks_left = max(0, fight_week - now) if fight_week else 0
    total_weeks = max(1, fight_week - start_week) if fight_week else 1
    elapsed = max(0, now - start_week)
    total_needed = max(0.0, start - target)
    progress_frac = min(1.0, elapsed / max(1.0, float(total_weeks)))
    expected = start - total_needed * progress_frac
    remaining = max(0.0, walk - target)
    behind = max(0.0, walk - expected)
    ahead = max(0.0, expected - walk)
    required_weekly = remaining / max(1, weeks_left) if remaining > 0 else 0.0
    actual_weekly = max(0.0, start - walk) / max(1, elapsed) if elapsed > 0 else 0.0
    if remaining <= 0.15:
        pace = "ready"
    elif behind > 0.35:
        pace = "behind %.1fkg" % behind
    elif ahead > 0.35:
        pace = "ahead %.1fkg" % ahead
    else:
        pace = "on track"
    return {
        "strategy": camp.get("strategy") or weight_strategy(fighter),
        "start": round(start, 1), "current": round(walk, 1), "target": round(target, 1),
        "lost": round(start - walk, 1), "remaining": round(remaining, 1),
        "limit": round(float(camp.get("limit_kg", CLASS_LIMIT.get(getattr(fighter, "fight_weight_class", None) or fighter.weight_class, walk))), 1),
        "start_week": start_week, "fight_week": fight_week, "weeks_left": weeks_left,
        "expected": round(expected, 1), "behind": round(behind, 1), "ahead": round(ahead, 1),
        "required_weekly": round(required_weekly, 2), "actual_weekly": round(actual_weekly, 2),
        "pace": pace,
    }

def pick_weight_strategy(console, fighter) -> None:
    console.header("WEIGHT STRATEGY", "Real camp loss vs fight-night size")
    letters = "ABC"
    keys = ["performance", "balanced", "bully"]
    walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
    fs = cut_feasibility(fighter)
    if fs["gap"] <= 0.15:
        console.good("No cut required: %.1fkg walking is already within the %.1fkg %s limit." % (walk, fs["cap"], fs["class"]))
        console.info("Meal plans may change real body mass over time; the cut strategy will not bulk you toward the limit.")
        return
    for i, key in enumerate(keys):
        spec = WEIGHT_STRATEGIES[key]
        target = target_walk_weight(fighter, key)
        direction = "lose %.1fkg" % max(0.0, walk - target) if walk > target else "already within target"
        console.print("  %s) %s — %s" % (letters[i], spec["label"], direction))
        console.print("     " + spec["desc"])
    raw = (console.ask("Strategy > ") or "").strip().upper()
    if raw not in letters:
        return
    key = keys[letters.index(raw)]
    set_weight_strategy(fighter, key)
    console.good("Weight strategy: %s." % WEIGHT_STRATEGIES[key]["label"])
    if key == "bully":
        console.warn("Bigger cage weight is earned through a harder final cut. Miss risk and gas tax still apply.")

BIG_SPONSORS = {
    "Nike", "Adidas", "Under Armour", "UFC Official Sponsor", "Mercedes-Benz",
    "BMW", "Lamborghini", "Rolex", "Amazon", "Meta / Facebook",
}
MID_SPONSORS = {
    "Monster Energy", "Reebok", "Venum", "Gatorade", "Puma", "Hayabusa",
    "Modelo", "Everlast", "Fairtex", "Gymshark",
}


def pick_home_class(console, fighter) -> None:
    """Player picks the division they live in. Weigh-ins aim at the upper limit."""
    from . import constants as C
    walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
    cur = getattr(fighter, "fight_weight_class", None) or fighter.weight_class
    console.print("Walking %.1fkg. Current home class: %s" % (walk, cur))
    letters = "ABCDEFGH"
    for i, name in enumerate(C.WEIGHT_CLASSES):
        cap = CLASS_LIMIT.get(name, 0)
        mark = "  <- now" if name == cur else ""
        console.print("  %s) %s  limit %.1fkg%s" % (letters[i], name, cap, mark))
    raw = (console.ask("Home class > ") or "").strip().upper()
    pick = None
    if raw.isdigit() and 1 <= int(raw) <= len(C.WEIGHT_CLASSES):
        pick = C.WEIGHT_CLASSES[int(raw) - 1]
    elif raw and raw[0] in letters:
        pick = C.WEIGHT_CLASSES[letters.index(raw[0])]
    if not pick:
        console.warn("Kept %s." % cur)
        return
    probe = cut_feasibility(fighter, pick)
    if not probe["makeable"]:
        low = lowest_class_for(walk)
        console.warn("You cannot make %s at %.1fkg. That is a %.0f%% cut." % (
            pick, walk, probe["frac"] * 100))
        console.print("The lowest division your frame can make is %s (%.1fkg)." % (
            low, CLASS_LIMIT.get(low, 0)))
        console.print("Lose real mass over months if you want to go lower.")
        return
    if probe["band"] in ("brutal", "hard"):
        console.warn("%.1fkg to make %s — %s" % (probe["gap"], pick, probe["label"]))
        if (console.ask("Commit to that division? A yes / B no > ") or "B").strip().upper() != "A":
            console.print("Kept %s." % cur)
            return
    fighter.fight_weight_class = pick
    fighter.weight_class = pick
    cap = CLASS_LIMIT.get(pick, walk)
    console.good("Home division: %s. Target %.1fkg on the scale — %s" % (
        pick, cap, probe["label"]))
    console.print("Aim to weigh in AT the limit, not under it.")


def physique_from_letter(letter: str) -> str:
    return {
        "A": "Lean", "B": "Athletic", "C": "Stocky", "D": "Tall",
        "E": "Heavy-built", "F": "Compact",
    }.get(letter, "Athletic")



# --- how much weight a human can actually shed for a fight ----------------
# Fight-week cutting is mostly water. A well-run camp moves real mass over
# weeks; the last few days move water and it is capped by physiology, not by
# willpower. Roughly: a fighter can make a limit around 8% below their walking
# weight comfortably, ~13% at serious cost, and beyond ~18% they simply cannot
# make it — which is why a 118kg man is not a Flyweight no matter how hard he
# diets.
CUT_COMFORTABLE = 0.08
CUT_HARD = 0.13
CUT_IMPOSSIBLE = 0.18


def lowest_class_for(walk: float, allow_hard: bool = True) -> str:
    """The lowest division this walking weight could physically make."""
    from . import constants as C
    limit_frac = CUT_IMPOSSIBLE if allow_hard else CUT_HARD
    floor = float(walk) * (1.0 - limit_frac)
    best = C.WEIGHT_CLASSES[-1]
    for name in C.WEIGHT_CLASSES:
        cap = CLASS_LIMIT.get(name, 0.0)
        if cap >= floor:
            best = name
            break
    return best


def cut_feasibility(fighter, wc: str = None) -> dict:
    """How hard is making this division, in physical terms."""
    walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
    wc = wc or getattr(fighter, "fight_weight_class", None) or fighter.weight_class
    cap = float(CLASS_LIMIT.get(wc, walk))
    gap = max(0.0, walk - cap)
    frac = (gap / walk) if walk > 0 else 0.0
    if frac <= 0.02:
        band, label = "natural", "walks around at the limit"
    elif frac <= CUT_COMFORTABLE:
        band, label = "routine", "a normal camp cut"
    elif frac <= CUT_HARD:
        band, label = "hard", "a hard cut — it will cost you in the cage"
    elif frac <= CUT_IMPOSSIBLE:
        band, label = "brutal", "brutal. Real chance you miss weight or gas out"
    else:
        band, label = "impossible", "not physically makeable"
    return {
        "class": wc, "cap": cap, "walk": walk, "gap": gap, "frac": frac,
        "band": band, "label": label,
        "makeable": band != "impossible",
    }


def weigh_in(fighter, console=None) -> dict:
    """Resolve scale/cage weights from real walking mass.

    Invariants: scale <= pre-weigh-in walking mass; no dehydration/drain when
    the athlete already walks within the division; rehydration cannot create
    mass above the pre-cut walking weight.
    """
    import random as _r
    fs = cut_feasibility(fighter)
    walk, cap = float(fs["walk"]), float(fs["cap"])
    nutrition = max(0, min(100, int(getattr(fighter, "nutrition", 50) or 50)))
    cut_health = max(0, min(100, int(getattr(fighter, "weight_cut_health", 100) or 100)))
    gap = max(0.0, walk - cap)
    frac = gap / walk if walk > 0 else 0.0

    if gap <= 0.15:
        # Natural heavyweight / under-limit fighter: no synthetic climb to the
        # cap and no fictional water cut. Day-to-day scale noise is downward
        # only so the displayed value can never exceed actual body mass.
        scale = max(0.0, walk - _r.uniform(0.0, min(0.25, walk * 0.0025)))
        made, over, miss_p, drain = True, 0.0, 0.0, 0
        cage = walk
    else:
        prep = nutrition * 0.55 + cut_health * 0.45
        phy = PHYSIQUES.get(getattr(fighter, "physique_type", "Athletic"), PHYSIQUES["Athletic"])
        effective_frac = frac * max(0.80, min(1.25, float(phy.get("cut", 1.0) or 1.0)))
        if effective_frac <= 0.04: miss_p = 0.01
        elif effective_frac <= 0.08: miss_p = 0.02 + (effective_frac - 0.04) / 0.04 * 0.05
        elif effective_frac <= 0.10: miss_p = 0.07 + (effective_frac - 0.08) / 0.02 * 0.10
        elif effective_frac <= 0.13: miss_p = 0.17 + (effective_frac - 0.10) / 0.03 * 0.28
        elif effective_frac <= 0.16: miss_p = 0.45 + (effective_frac - 0.13) / 0.03 * 0.30
        elif effective_frac <= CUT_IMPOSSIBLE: miss_p = 0.75 + (effective_frac - 0.16) / max(0.001, CUT_IMPOSSIBLE - 0.16) * 0.20
        else: miss_p = 1.0
        miss_p += (75.0 - prep) * 0.0125
        if int(getattr(fighter, "hangover_weeks", 0) or 0) > 0: miss_p += 0.15
        if cut_health < 55: miss_p += (55 - cut_health) / 180.0
        miss_p = max(0.005, min(1.0, miss_p))
        made = _r.random() >= miss_p
        if made:
            scale = max(0.0, min(walk, cap - _r.uniform(0.0, min(0.35, cap * 0.003))))
            over = 0.0
        else:
            over = min(gap, max(0.1, _r.uniform(0.2, min(1.4, max(0.2, gap)))))
            scale = min(walk, cap + over)
        drain = max(0, int(round(max(0.0, frac - 0.055) * 118)))
        if fs["band"] == "impossible": drain = max(drain, 20)
        if not made: drain += 2
        drain = min(24, drain)
        lost = max(0.0, walk - scale)
        rehydrate = max(0.45, min(0.90, 0.62 + nutrition / 500.0 + cut_health / 1000.0 - drain / 180.0))
        cage = min(walk, scale + lost * rehydrate)

    over = round(float(over), 1)
    penalty = 0
    if not made:
        penalty = 20 if over <= 1.0 else 30
        if console:
            console.warn("MISSED WEIGHT: %.1fkg, %.1f over the %s limit." % (scale, over, fs["class"]))
        flags = getattr(fighter, "story_flags", None)
        if not isinstance(flags, dict): fighter.story_flags = {}; flags = fighter.story_flags
        flags["missed_weight"] = int(flags.get("missed_weight", 0) or 0) + 1
    elif console:
        if gap <= 0.15:
            console.good("Made weight naturally: %.1fkg walking / %.1fkg scale (%s limit %.1f)." % (walk, scale, fs["class"], cap))
        else:
            console.good("Made weight: %.1fkg (%s limit %.1f)." % (scale, fs["class"], cap))

    fighter.cut_drain = int(drain)
    fighter.cut_fatigue = 0 if gap <= 0.15 else min(30, max(int(getattr(fighter, "cut_fatigue", 0) or 0), drain + int(frac * 30)))
    if drain:
        fighter.energy = max(10, int(getattr(fighter, "energy", 70) or 70) - drain)
        fighter.weight_cut_health = max(0, cut_health - max(1, drain // 2))
    fighter._scale_weight = round(scale, 1)
    fighter._fight_night_weight = round(cage, 1)
    bully_kg = max(0.0, cage - cap)
    bully_label = "natural" if gap <= 0.15 or bully_kg < 1.5 else ("sized" if bully_kg < 4.0 else ("weight bully" if bully_kg < 7.0 else "extreme bully"))
    try:
        camp_state = ensure_weight_campaign(fighter)
        start_walk = float(camp_state.get("start_walk_kg", walk) or walk)
        camp_state["final"] = {
            "week": int(getattr(fighter, "week", 0) or 0), "pre_weighin_walk_kg": round(walk, 2),
            "scale_kg": round(scale, 1), "cage_kg": round(cage, 1),
            "real_mass_lost_kg": round(start_walk - walk, 2), "water_cut_kg": round(max(0.0, walk - scale), 2),
            "rehydrated_kg": round(max(0.0, cage - scale), 2), "bully_kg_over_limit": round(bully_kg, 2),
            "made": bool(made), "cut_required": bool(gap > 0.15),
        }
    except Exception:
        pass
    return {"made": made, "scale_kg": round(scale, 1), "over_kg": over, "penalty": penalty,
            "band": fs["band"], "cut_drain": int(drain), "cage_kg": round(cage, 1),
            "cut_pct": round(frac * 100, 1), "rehydrated_kg": round(max(0.0, cage - scale), 1),
            "bully_kg": round(bully_kg, 1), "bully_label": bully_label, "cut_required": bool(gap > 0.15)}


def cut_risk(fighter) -> int:
    limit = CLASS_LIMIT.get(fighter.fight_weight_class or fighter.weight_class, 70.3)
    walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
    gap = max(0.0, walk - limit)
    if gap <= 0.15:
        return 0
    phy = PHYSIQUES.get(getattr(fighter, "physique_type", "Athletic"), PHYSIQUES["Athletic"])
    nutr = 100 - int(fighter.nutrition)
    plan_delta = plan_weight_change(getattr(fighter, "meal_plan", "") or "")
    plan_mod = 0.85 if plan_delta <= -0.20 else (1.15 if plan_delta >= 0.20 else 1.0)
    raw = (gap * 8.0 * phy["cut"] + nutr * 0.15) * plan_mod
    if getattr(fighter, "hangover_weeks", 0) > 0:
        raw += 8
    bf = float(getattr(fighter, "bodyfat", 12.0) or 12.0)
    raw += max(0.0, (bf - 12.0) * 1.2)
    return int(max(0, min(95, raw)))


def size_gap(a, b) -> int:
    """Positive = a is bigger than b at fight night."""
    try:
        from .physiology import fight_night_weight
        dw = int(round(fight_night_weight(a) - fight_night_weight(b)))
    except Exception:
        dw = int(getattr(a, "walking_weight", a.weight) or a.weight) - int(getattr(b, "walking_weight", b.weight) or b.weight)
    dh = int(a.height) - int(b.height)
    return dw + dh // 4


def bully_mod(fighter, opponent) -> float:
    gap = size_gap(fighter, opponent)
    phy = PHYSIQUES.get(getattr(fighter, "physique_type", "Athletic"), PHYSIQUES["Athletic"])
    ophy = PHYSIQUES.get(getattr(opponent, "physique_type", "Athletic"), PHYSIQUES["Athletic"])
    raw = (gap / 40.0) * phy["bully"] / max(0.7, ophy["bully"])
    return max(-0.12, min(0.12, raw))


def decay_damage(fighter) -> None:
    d = getattr(fighter, "damage", None) or {}
    heal = 8
    if getattr(fighter, "camp_focus", "") == "Rehab":
        heal += 6
    if getattr(fighter, "hangover_weeks", 0) > 0:
        heal -= 3
    inj = getattr(fighter, "injury", None) or {}
    if inj.get("weeks", 0) > 0:
        heal -= 2
    for k in ("cuts", "nose", "eyes", "body", "legs", "head"):
        d[k] = max(0, int(d.get(k, 0)) - heal)
    d["total"] = min(100, sum(d.get(k, 0) for k in ("cuts", "nose", "eyes", "body", "legs", "head")))
    fighter.damage = d


def rehab(fighter, console=None) -> str:
    """Paid clinic week. Cuts injury time and lingering damage."""
    inj = getattr(fighter, "injury", None) or {}
    dmg = int((getattr(fighter, "damage", None) or {}).get("total", 0) or 0)
    if not inj.get("weeks") and dmg < 8:
        return "Nothing to rehab."
    cost = 80 + 40 * int(inj.get("sev", 1) or 1)
    try:
        from .education import degree_benefit
        cost = int(round(cost * float(degree_benefit(fighter, "rehab_mult", 1.0))))
    except Exception:
        pass
    fighter.money = int(getattr(fighter, "money", 0) or 0) - cost
    fighter.energy = max(8, int(getattr(fighter, "energy", 50) or 50) - 6)
    if inj.get("weeks"):
        inj["weeks"] = max(0, int(inj["weeks"]) - 2)
        fighter.injury = inj if inj["weeks"] > 0 else {}
    decay_damage(fighter)
    decay_damage(fighter)
    fighter.health = min(100, int(getattr(fighter, "health", 80) or 80) + 8)
    if console:
        console.good("Rehab −$%s. Injury %sw left." % (cost, (fighter.injury or {}).get("weeks", 0)))
    return "Rehab done."


def tick_injury(fighter, console=None) -> None:
    # The locational-damage system owns structured injuries.  Do not tick the
    # legacy mirror as well or one calendar week heals two injury weeks.
    structured = (getattr(fighter, "story_flags", None) or {}).get("injuries")
    if isinstance(structured, list) and any(int(i.get("weeks", 0) or 0) > 0 for i in structured):
        return
    inj = getattr(fighter, "injury", None) or {}
    weeks = int(inj.get("weeks", 0) or 0)
    if weeks <= 0:
        fighter.injury = {}
        return
    weeks -= 1
    inj["weeks"] = weeks
    fighter.injury = inj
    fighter.energy = max(0, fighter.energy - 3 * int(inj.get("sev", 1)))
    if weeks <= 0 and console:
        console.info("Injury cleared: %s" % inj.get("area", "niggle"))
        fighter.injury = {}


def parents_help(fighter) -> bool:
    """Under-18 secondary-school careers receive basic parent support."""
    if fighter.pro_debut or int(getattr(fighter, "age", 16) or 16) >= 18:
        return False
    try:
        from .education import ensure
        ensure(fighter)
        return fighter.education_stage == "secondary"
    except Exception:
        return getattr(fighter, "school_status", "none") == "school"


def weekly_costs(fighter, console=None) -> int:
    """Apply the exact weekly ledger to cash once.

    1.24 had two different economy models: ``weekly_costs`` deducted $138 in
    the playtest while ``economy.apply_weekly`` displayed $188 expenses and
    $65 of income that was never credited.  This is now one transaction.
    """
    from . import economy
    income, expenses = economy.weekly_breakdown(fighter)
    expense_total = sum(int(v) for v in expenses.values())
    covered = 0
    allowance = 0
    if parents_help(fighter):
        covered = expense_total
        allowance = 35 if fighter.week <= 12 else 25
        # Show the same expenses, then offset them with actual parent support.
        income = dict(income)
        income["parents covered living"] = covered
        income["allowance"] = allowance
        led = economy.record(fighter, income, expenses)
        fighter.money = int(getattr(fighter, "money", 0) or 0) + int(led.get("net", 0) or 0)
    else:
        led = economy.apply_weekly(fighter, apply_cash=True)
        if fighter.money < 0:
            fighter.happiness = max(0, fighter.happiness - 3)
        if fighter.money < 15:
            fighter.nutrition = max(0, fighter.nutrition - 3)
            fighter.happiness = max(0, fighter.happiness - 2)
    fighter.last_costs = expense_total
    fighter.last_tax = expense_total
    fighter.last_allowance = allowance
    fighter.parents_covered = covered
    fighter.weekly_spend = getattr(fighter, "weekly_spend", 0) + expense_total
    if console:
        if covered:
            console.print("Parents covered $%s living. Allowance $%s." % (covered, allowance))
        else:
            inc = sum(int(v) for v in (led.get("income") or {}).values())
            net = int(led.get("net", 0) or 0)
            console.print("Money week: expenses $%s · income $%s · net %s$%s." % (
                expense_total, inc, "+" if net >= 0 else "-", abs(net)))
    return expense_total


def sponsor_allowed(fighter, sponsor: dict) -> bool:
    """Sponsor gate on one coherent 0-100 fame scale plus real pro résumé.

    1.23 used *total* wins, so a decorated amateur could turn pro 0-2 and
    immediately qualify for global brands. Followers are stored/displayed in
    thousands, so 20 means roughly 20k.
    """
    name = str(sponsor.get("name", "") or "")
    fame = max(0, min(100, int(getattr(fighter, "fame", 0) or 0)))
    followers_k = max(0, int(getattr(fighter, "followers", 0) or 0))
    pro = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    pro_wins = int(pro[0] or 0)
    req_fame = int(sponsor.get("min_fame", sponsor.get("fame_req", 0)) or 0)
    if name in BIG_SPONSORS:
        return bool(getattr(fighter, "pro_debut", False)) and pro_wins >= 4 and fame >= max(55, req_fame) and followers_k >= 20
    if name in MID_SPONSORS:
        return bool(getattr(fighter, "pro_debut", False)) and pro_wins >= 2 and fame >= max(20, req_fame) and followers_k >= 5
    return fame >= req_fame


def apply_injury(fighter, area: str, sev: int = 1):
    """Compatibility entry point that now creates a canonical injury."""
    hist = list(getattr(fighter, "injury_history", None) or [])
    hist.append({"area": area, "sev": sev, "week": int(getattr(fighter, "week", 0) or 0)})
    fighter.injury_history = hist[-20:]
    same = sum(1 for h in hist if h.get("area") == area)
    if same >= 3:
        sev = min(3, sev + 1)
    from . import damage as _damage
    area_key = str(area or "").lower()
    names = {
        "hand": "broken hand" if sev >= 3 else "broken knuckle",
        "knee": "torn knee" if sev >= 2 else "ankle sprain",
        "eye": "orbital fracture" if sev >= 3 else "swollen eye",
        "rib": "cracked rib", "ribs": "cracked rib",
        "shoulder": "torn shoulder",
    }
    name = names.get(area_key, area_key if area_key in _damage.INJURIES else "ankle sprain")
    return _damage.add_injury(fighter, name, "training or life incident")


def plan_weight_change(plan_name: str) -> float:
    """kg per week implied by the meal-plan JSON. 0 if unknown."""
    name = str(plan_name or "")
    try:
        from . import data
        for p in list(getattr(data, "NUTRITION_PLANS", None) or []):
            if p.get("name") == name:
                return float(p.get("weekly_mass_kg", p.get("weight_change", 0)) or 0)
    except Exception:
        pass
    if any(w in name for w in ("Cut", "Strict", "Clean")):
        return -1.0
    if any(w in name for w in ("Cheat", "Comfort")):
        return 2.0
    return 0.0


def apply_plan_now(fighter, plan: dict) -> None:
    """Deprecated compatibility hook. Plans now act on weekly ticks only."""
    return None


def physique_floor(phy: str, cutting: bool) -> float:
    table = {"Lean": 7.5, "Athletic": 9.5, "Stocky": 12.0, "Tall": 9.5,
             "Heavy-built": 12.0, "Compact": 9.0}
    floor = table.get(phy or "Athletic", 9.5)
    if cutting:
        return max(6.5, floor - 4.0) if phy == "Heavy-built" else max(5.8, floor - 3.5)
    return floor


def tick_body(fighter, console=None) -> None:
    """Advance body composition one week from structured nutrition data.

    1.24 removes the old name-substring diet engine ("Clean", "Comfort",
    "Cut", etc.).  The JSON meal plan is now the source of truth for scale
    movement; camp context only adds a small goal-directed correction.
    """
    walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
    bf = float(getattr(fighter, "bodyfat", 12.0) or 12.0)
    natural = float(getattr(fighter, "natural_weight", fighter.weight) or fighter.weight)
    nutr = int(getattr(fighter, "nutrition", 50) or 50)
    plan = str(getattr(fighter, "meal_plan", "") or "")
    camp = bool(getattr(fighter, "camp_active", False) or int(getattr(fighter, "camp_for_bout", 0) or 0) > 0)
    phy = str(getattr(fighter, "physique_type", "Athletic") or "Athletic")
    home = getattr(fighter, "fight_weight_class", None) or fighter.weight_class
    cap = float(CLASS_LIMIT.get(home, 70.3))

    # Structured plan metadata. Unknown/legacy names are maintenance rather
    # than being guessed from words in the label.
    spec = {}
    try:
        from . import data
        spec = next((x for x in list(getattr(data, "NUTRITION_PLANS", None) or [])
                     if str(x.get("name") or "") == plan), {}) or {}
    except Exception:
        spec = {}
    d_w = float(spec.get("weekly_mass_kg", spec.get("weight_change", 0.0)) or 0.0)

    # Fight-target nutrition: a cutting meal plan now knows what it is trying
    # to achieve. The player still has to choose a deficit plan; maintenance
    # food will not secretly make weight for them. Performance/balanced plans
    # lose enough real mass over the remaining camp to leave only the chosen
    # fight-week water cut. Weight-bully strategy deliberately leaves more.
    booked = getattr(fighter, "booked_fight", None) or {}
    if booked and int(booked.get("date_week") or 0) > int(getattr(fighter, "week", 0) or 0):
        camp_state = ensure_weight_campaign(fighter)
        strategy = str(camp_state.get("strategy") or weight_strategy(fighter))
        target_walk = target_walk_weight(fighter, strategy)
        camp_state["target_walk_kg"] = target_walk
        camp_state["strategy"] = strategy
        weeks_left = max(1, int(booked.get("date_week") or fighter.week + 1) - int(fighter.week))
        if walk > target_walk and d_w <= -0.10:
            needed = (target_walk - walk) / weeks_left
            d_w = min(d_w, max(-0.90, needed * 1.08))
        elif walk > target_walk and d_w > -0.10:
            # No hidden loss on a maintenance/bulk plan: the UI warning is
            # meaningful because nutrition choice controls real scale change.
            pass
    cutting = d_w <= -0.20
    gaining = d_w >= 0.20
    floor_bf = physique_floor(phy, cutting)

    # Body-fat direction follows the planned scale direction, but most weekly
    # weight movement is water/glycogen/lean tissue rather than pure fat.
    d_bf = max(-0.18, min(0.20, d_w * 0.32))

    # Camp correction is small and only reinforces an already weight-losing
    # regimen. A maintenance/bulk plan cannot secretly become a cut because the
    # fighter entered camp.
    if camp and cutting:
        target = cap + 1.2
        if walk > target:
            d_w -= min(0.18, (walk - target) * 0.020)
        if nutr < 40:
            d_w -= 0.08
            fighter.energy = max(8, int(getattr(fighter, "energy", 70)) - 2)

    # Maintenance plans gently drift toward natural walking weight. This keeps
    # an old depleted save from living forever at fight-week scale weight.
    if abs(d_w) < 0.05:
        gap = natural - walk
        d_w += max(-0.10, min(0.10, gap * 0.06))
        if abs(gap) < 0.5 and bf < physique_floor(phy, False) + 0.8:
            d_bf += 0.05

    # Quality modifies composition/recovery without duplicating the meal-plan
    # mass delta itself.
    if nutr >= 80 and not cutting:
        fighter.energy = min(100, int(getattr(fighter, "energy", 70)) + 1)
        fighter.health = min(100, int(getattr(fighter, "health", 70)) + 1)
    elif nutr <= 30:
        d_w -= 0.08
        d_bf -= 0.03
        fighter.health = max(8, int(getattr(fighter, "health", 70)) - 1)

    # Gaining diets can add fat, but do not push every physique toward obesity.
    if gaining and bf >= physique_floor(phy, False) + 8.0:
        d_bf *= 0.45

    min_bf = max(5.8, floor_bf) if cutting else physique_floor(phy, False)
    fighter.bodyfat = max(min_bf, min(28.0, bf + d_bf))
    fighter.walking_weight = max(52.0, min(128.0, walk + d_w))
    if getattr(fighter, "booked_fight", None):
        try:
            camp_state = ensure_weight_campaign(fighter)
            hist = list(camp_state.get("history") or [])
            hist.append({
                "week": int(getattr(fighter, "week", 0) or 0),
                "walk_kg": round(float(fighter.walking_weight), 2),
                "bodyfat": round(float(fighter.bodyfat), 2),
                "nutrition": int(getattr(fighter, "nutrition", 0) or 0),
                "plan": str(getattr(fighter, "meal_plan", "") or ""),
            })
            camp_state["history"] = hist[-16:]
        except Exception:
            pass

    # Fade fight-night cut tax. Cut-health recovery is handled in
    # physiology.nutrition_week(), so it is not double-counted here.
    fat = int(getattr(fighter, "cut_fatigue", 0) or 0)
    if fat > 0 and not camp:
        fighter.cut_fatigue = max(0, fat - 4)


def school_tick(fighter, console=None) -> None:
    """Compatibility wrapper; v1.40 education.py owns academic progression."""
    try:
        from .education import tick
        tick(fighter, console)
    except Exception:
        return

