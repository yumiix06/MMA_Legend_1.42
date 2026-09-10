"""v1.40 performance systems: legal supplements and abstract anti-doping.

The system deliberately avoids real-world detection/clearance timing. Prohibited
programs are gameplay states with temporary performance effects, health burden,
scrutiny and anti-doping consequences.
"""
from __future__ import annotations

import random
from typing import Iterable

LEGAL_PRODUCTS = {
    "Creatine": {
        "cost": 40, "weeks": 4,
        "description": "Supports repeated high-intensity work and strength adaptation.",
        "training": {"strength": 1.10, "ko_power": 1.05},
        "stats": {"strength": 2, "ko_power": 1}, "recovery": 0.4,
    },
    "Protein & Recovery": {
        "cost": 45, "weeks": 4,
        "description": "Small recovery and general training support.",
        "training_all": 1.05, "recovery": 1.0,
    },
    "Electrolytes": {
        "cost": 25, "weeks": 4,
        "description": "Improves weekly energy recovery and fight-night cardio expression.",
        "stats": {"cardio": 1}, "energy_recovery": 2.0,
    },
    "Caffeine / Pre-Workout": {
        "cost": 25, "weeks": 3,
        "description": "Small short-term speed/cardio expression and training support.",
        "training_all": 1.03, "stats": {"speed": 1, "cardio": 1},
    },
    "Omega-3": {
        "cost": 30, "weeks": 4,
        "description": "Small recovery support and slightly lower training-injury risk.",
        "recovery": 0.5, "injury_mult": 0.96,
    },
    "Multivitamin": {
        "cost": 20, "weeks": 4,
        "description": "Small recovery benefit when diet quality is not ideal.",
        "recovery": 0.35,
    },
    "Sleep Support": {
        "cost": 35, "weeks": 4,
        "description": "Improves weekly energy recovery and modestly supports health recovery.",
        "recovery": 0.5, "energy_recovery": 2.0,
    },
    "Joint Support": {
        "cost": 35, "weeks": 4,
        "description": "Modestly reduces training-injury risk.",
        "injury_mult": 0.92,
    },
    "Unverified Performance Blend": {
        "cost": 45, "weeks": 4,
        "description": "Small legal-style benefit, but quality control is uncertain.",
        "training_all": 1.04, "stats": {"cardio": 1}, "contamination": 0.025,
    },
}

PROHIBITED_PROGRAMS = {
    "Anabolic Program": {
        "cost": 500, "weeks": 8,
        "description": "Strong strength/recovery enhancement with significant health and testing consequences.",
        "stats": {"strength": 5, "ko_power": 4, "durability": 2},
        "training": {"strength": 1.20, "ko_power": 1.15, "durability": 1.10},
        "training_all": 1.05, "recovery": 1.5, "scrutiny": 34, "burden": 2.0,
    },
    "Blood-Boosting Program": {
        "cost": 600, "weeks": 8,
        "description": "Major cardio expression with a high health/testing burden.",
        "stats": {"cardio": 7, "speed": 2},
        "training": {"cardio": 1.18, "speed": 1.08},
        "scrutiny": 38, "burden": 2.5,
    },
    "Growth / Recovery Program": {
        "cost": 700, "weeks": 8,
        "description": "Recovery and durability enhancement with significant anti-doping exposure.",
        "stats": {"strength": 3, "durability": 4},
        "training_all": 1.08, "recovery": 2.0, "scrutiny": 32, "burden": 2.0,
    },
    "Prohibited Stimulant Program": {
        "cost": 300, "weeks": 4,
        "description": "Short-term speed/cardio expression with health and testing consequences.",
        "stats": {"speed": 4, "cardio": 2, "fight_iq": -1},
        "training": {"speed": 1.10, "cardio": 1.08},
        "energy_recovery": 2.0, "scrutiny": 30, "burden": 2.0,
    },
}


def ensure(fighter) -> None:
    if not isinstance(getattr(fighter, "supplement_stack", None), dict):
        fighter.supplement_stack = {}
    if not isinstance(getattr(fighter, "doping_program", None), dict):
        fighter.doping_program = {}
    if not isinstance(getattr(fighter, "doping_sample", None), dict):
        fighter.doping_sample = {}
    if not isinstance(getattr(fighter, "doping_history", None), list):
        fighter.doping_history = []
    fighter.doping_scrutiny = max(0, min(100, int(getattr(fighter, "doping_scrutiny", 0) or 0)))
    fighter.doping_health_burden = max(0, min(100, int(getattr(fighter, "doping_health_burden", 0) or 0)))
    fighter.doping_violations = max(0, int(getattr(fighter, "doping_violations", 0) or 0))
    fighter.contamination_weeks = max(0, int(getattr(fighter, "contamination_weeks", 0) or 0))


def active_legal(fighter) -> list[tuple[str, dict]]:
    ensure(fighter)
    out = []
    for name, weeks in list(fighter.supplement_stack.items()):
        if int(weeks or 0) > 0 and name in LEGAL_PRODUCTS:
            out.append((name, LEGAL_PRODUCTS[name]))
    return out


def active_program(fighter) -> tuple[str, dict] | tuple[None, None]:
    ensure(fighter)
    row = fighter.doping_program or {}
    name = str(row.get("name") or "")
    if name in PROHIBITED_PROGRAMS and int(row.get("weeks", 0) or 0) > 0:
        return name, PROHIBITED_PROGRAMS[name]
    return None, None


def buy_legal(fighter, name: str, covered: bool = False) -> str:
    ensure(fighter)
    spec = LEGAL_PRODUCTS.get(name)
    if not spec:
        return "Unknown product."
    cost = 0 if covered else int(spec.get("cost", 0) or 0)
    if int(getattr(fighter, "money", 0) or 0) < cost:
        return "Not enough cash."
    fighter.money = int(getattr(fighter, "money", 0) or 0) - cost
    weeks = int(spec.get("weeks", 4) or 4)
    fighter.supplement_stack[name] = weeks
    # Legacy mirrors remain synchronized for old authored UI/events. They are
    # not the source of effects and never alter raw attributes.
    fighter.supplement_active = list(dict.fromkeys(list(getattr(fighter, "supplement_active", None) or []) + [name]))
    fighter.supplement_duration = dict(getattr(fighter, "supplement_duration", None) or {})
    fighter.supplement_duration[name] = weeks
    # Quality-control risk is intentionally abstract and very small.
    if float(spec.get("contamination", 0.0) or 0.0) > 0 and random.random() < float(spec["contamination"]):
        fighter.contamination_weeks = max(fighter.contamination_weeks, int(spec.get("weeks", 4) or 4))
        fighter.doping_scrutiny = min(100, fighter.doping_scrutiny + 4)
    return "%s active for %s weeks%s." % (name, spec.get("weeks", 4), " (sponsor supplied)" if covered else "")


def start_program(fighter, name: str) -> str:
    ensure(fighter)
    spec = PROHIBITED_PROGRAMS.get(name)
    if not spec:
        return "Unknown prohibited program."
    if active_program(fighter)[0]:
        return "Finish or stop the current prohibited program first."
    cost = int(spec.get("cost", 0) or 0)
    if int(getattr(fighter, "money", 0) or 0) < cost:
        return "Not enough cash."
    fighter.money -= cost
    fighter.doping_program = {"name": name, "weeks": int(spec.get("weeks", 4) or 4), "started_week": int(getattr(fighter, "week", 0) or 0)}
    fighter.doping_used = True
    fighter.doping_scrutiny = min(100, fighter.doping_scrutiny + int(spec.get("scrutiny", 30) or 30))
    fighter.doping_risk = fighter.doping_scrutiny  # legacy display/event compatibility
    return "%s started. Effects are temporary; health burden and testing scrutiny rise while active." % name


def stop_program(fighter) -> str:
    ensure(fighter)
    name, _ = active_program(fighter)
    if not name:
        return "No prohibited program is active."
    fighter.doping_program = {}
    return "%s stopped. Scrutiny and accumulated health burden do not disappear immediately." % name


def training_multiplier(fighter, stat: str | None = None) -> float:
    mult = 1.0
    for _name, spec in active_legal(fighter):
        mult *= float(spec.get("training_all", 1.0) or 1.0)
        if stat:
            mult *= float((spec.get("training") or {}).get(stat, 1.0) or 1.0)
    _name, spec = active_program(fighter)
    if spec:
        mult *= float(spec.get("training_all", 1.0) or 1.0)
        if stat:
            mult *= float((spec.get("training") or {}).get(stat, 1.0) or 1.0)
    return max(0.85, min(1.35, mult))


def injury_risk_multiplier(fighter) -> float:
    mult = 1.0
    for _name, spec in active_legal(fighter):
        mult *= float(spec.get("injury_mult", 1.0) or 1.0)
    # High health burden can make training less robust even if a program improves recovery.
    burden = int(getattr(fighter, "doping_health_burden", 0) or 0)
    mult *= 1.0 + min(0.20, burden / 500.0)
    return max(0.75, min(1.30, mult))


def stat_modifier(fighter, stat: str) -> int:
    mod = 0
    for _name, spec in active_legal(fighter):
        mod += int((spec.get("stats") or {}).get(stat, 0) or 0)
    _name, spec = active_program(fighter)
    if spec:
        mod += int((spec.get("stats") or {}).get(stat, 0) or 0)
    burden = int(getattr(fighter, "doping_health_burden", 0) or 0)
    if burden >= 35 and stat in ("cardio", "durability", "speed"):
        mod -= 1 + (1 if burden >= 70 else 0)
    return max(-4, min(8, mod))


def recovery_bonus(fighter) -> tuple[float, float]:
    health = 0.0
    energy = 0.0
    for _name, spec in active_legal(fighter):
        health += float(spec.get("recovery", 0.0) or 0.0)
        energy += float(spec.get("energy_recovery", 0.0) or 0.0)
    _name, spec = active_program(fighter)
    if spec:
        health += float(spec.get("recovery", 0.0) or 0.0)
        energy += float(spec.get("energy_recovery", 0.0) or 0.0)
    burden = int(getattr(fighter, "doping_health_burden", 0) or 0)
    health -= min(3.0, burden / 25.0)
    return health, energy


def testing_profile(fighter) -> tuple[str, float]:
    """Abstract weekly selection pressure, not real-world testing frequency."""
    if int(getattr(fighter, "suspension_weeks", 0) or 0) > 0:
        return "Suspended", 0.0
    if bool(getattr(fighter, "national_team", False)):
        base = 0.018
        label = "National-team pool"
    elif not bool(getattr(fighter, "pro_debut", False)):
        tier = int(getattr(fighter, "promotion_tier", 0) or 0)
        if tier <= 0:
            return "Local amateur", 0.001
        if tier == 1:
            return "National amateur", 0.009
        return "International amateur", 0.018
    else:
        org = str(getattr(fighter, "organization", "") or "")
        room = str(getattr(fighter, "room", "") or "")
        if org == "UFC" or room == "ufc":
            base, label = 0.030, "Major international"
        elif room in ("elite", "global") or org in ("PFL", "Bellator", "ONE"):
            base, label = 0.020, "International professional"
        else:
            base, label = 0.009, "Regional professional"
    if isinstance(getattr(fighter, "booked_fight", None), dict):
        base *= 1.25
    return label, min(0.08, base)


def _record_history(fighter, kind: str, detail: str) -> None:
    ensure(fighter)
    fighter.doping_history.append({"week": int(getattr(fighter, "week", 0) or 0), "kind": kind, "detail": detail})
    fighter.doping_history = fighter.doping_history[-40:]


def _violation(fighter, console=None) -> None:
    ensure(fighter)
    fighter.doping_violations += 1
    n = fighter.doping_violations
    suspension = 26 if n == 1 else (52 if n == 2 else 104)
    fine = 1500 if not getattr(fighter, "pro_debut", False) else min(15000, 2500 * n)
    fighter.suspension_weeks = max(int(getattr(fighter, "suspension_weeks", 0) or 0), suspension)
    fighter.doping_fines_paid = int(getattr(fighter, "doping_fines_paid", 0) or 0) + fine
    fighter.money = int(getattr(fighter, "money", 0) or 0) - fine
    fighter.reputation = max(0, int(getattr(fighter, "reputation", 0) or 0) - (15 + 5 * n))
    fighter.legacy_score = max(0, int(getattr(fighter, "legacy_score", 0) or 0) - (8 + 4 * n))
    fighter.confidence = max(0, int(getattr(fighter, "confidence", 50) or 50) - 6)
    try:
        from .notoriety import add_fame
        add_fame(fighter, -(8 + 4 * n), "anti-doping violation")
    except Exception:
        fighter.fame = max(0, int(getattr(fighter, "fame", 0) or 0) - (8 + 4 * n))
    if getattr(fighter, "sponsors", None):
        fighter.sponsors = list(fighter.sponsors)[:1] if n == 1 else []
    fighter.doping_program = {}
    fighter.doping_scrutiny = min(100, max(45, fighter.doping_scrutiny))
    fighter.doping_risk = fighter.doping_scrutiny
    _record_history(fighter, "violation", "Adverse finding; %sw suspension; $%s fine" % (suspension, fine))
    if console:
        console.warn("ANTI-DOPING VIOLATION — suspended %s weeks and fined $%s." % (suspension, format(fine, ",")))


def tick(fighter, console=None) -> None:
    ensure(fighter)
    # Legal products expire; they never modify raw trained attributes.
    for name in list(fighter.supplement_stack.keys()):
        fighter.supplement_stack[name] = int(fighter.supplement_stack[name] or 0) - 1
        if name in getattr(fighter, "supplement_duration", {}):
            fighter.supplement_duration[name] = fighter.supplement_stack[name]
        if fighter.supplement_stack[name] <= 0:
            del fighter.supplement_stack[name]
            getattr(fighter, "supplement_duration", {}).pop(name, None)
            if name in getattr(fighter, "supplement_active", []):
                fighter.supplement_active.remove(name)
    if fighter.contamination_weeks > 0:
        fighter.contamination_weeks -= 1

    name, spec = active_program(fighter)
    if name and spec:
        fighter.doping_program["weeks"] = int(fighter.doping_program.get("weeks", 0) or 0) - 1
        fighter.doping_health_burden = min(100, int(round(fighter.doping_health_burden + float(spec.get("burden", 2.0) or 2.0))))
        fighter.doping_scrutiny = min(100, fighter.doping_scrutiny + 2)
        if fighter.doping_program["weeks"] <= 0:
            fighter.doping_program = {}
            if console:
                console.info("Prohibited performance program ended. Scrutiny/health burden will fade gradually.")
    else:
        fighter.doping_scrutiny = max(0, fighter.doping_scrutiny - (1 if fighter.week % 2 == 0 else 0))
        if fighter.week % 3 == 0:
            fighter.doping_health_burden = max(0, fighter.doping_health_burden - 1)
    fighter.doping_risk = fighter.doping_scrutiny
    fighter.doping_health = max(0, 100 - fighter.doping_health_burden)

    # Pending samples resolve later. Probability is frozen at collection; there
    # is no clearance-window mechanic to optimize around.
    sample = fighter.doping_sample or {}
    if sample and sample.get("status") == "pending" and int(getattr(fighter, "week", 0) or 0) >= int(sample.get("result_week", 999999) or 999999):
        adverse = random.random() < float(sample.get("adverse_probability", 0.0) or 0.0)
        if adverse:
            sample["status"] = "adverse"
            fighter.doping_sample = sample
            _violation(fighter, console)
        else:
            sample["status"] = "clean"
            fighter.doping_sample = sample
            _record_history(fighter, "test", "Sample passed")
            if console:
                console.good("Anti-doping result: PASSED.")

    if fighter.doping_sample and fighter.doping_sample.get("status") == "pending":
        return
    label, base = testing_profile(fighter)
    if base <= 0:
        return
    scrutiny = fighter.doping_scrutiny / 100.0
    chance = min(0.12, base * (1.0 + scrutiny * 1.5))
    if random.random() < chance:
        active = bool(active_program(fighter)[0])
        contam = fighter.contamination_weeks > 0
        adverse_probability = 0.82 if active else (0.22 if contam else 0.002)
        fighter.doping_sample = {
            "status": "pending", "collected_week": int(getattr(fighter, "week", 0) or 0),
            "result_week": int(getattr(fighter, "week", 0) or 0) + random.randint(1, 3),
            "profile": label, "adverse_probability": adverse_probability,
        }
        fighter.drug_test_weeks = int(getattr(fighter, "drug_test_weeks", 0) or 0) + 1
        _record_history(fighter, "sample", "%s sample collected" % label)
        if console:
            console.warn("Anti-doping sample collected — result pending.")


def status_lines(fighter) -> list[str]:
    ensure(fighter)
    lines = []
    if active_legal(fighter):
        lines.append("Legal stack: " + ", ".join("%s %sw" % (n, int(fighter.supplement_stack[n])) for n, _ in active_legal(fighter)))
    else:
        lines.append("Legal stack: none")
    name, _spec = active_program(fighter)
    lines.append("Prohibited program: %s" % (name or "none"))
    profile, _chance = testing_profile(fighter)
    lines.append("Testing profile: %s · scrutiny %s/100 · health burden %s/100" % (profile, fighter.doping_scrutiny, fighter.doping_health_burden))
    sample = fighter.doping_sample or {}
    if sample:
        lines.append("Latest sample: %s" % str(sample.get("status", "none")).upper())
    if fighter.doping_violations:
        lines.append("Violations: %s" % fighter.doping_violations)
    return lines
