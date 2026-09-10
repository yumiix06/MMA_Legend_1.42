"""1.5 helpers: names, continents, belts, camps, jobs, debt, contracts."""
from __future__ import annotations

import random

EUROPE = {
    "Netherlands", "UK", "France", "Germany", "Sweden", "Poland", "Ireland",
    "Italy", "Spain", "Ukraine", "Norway", "Czech Republic", "Georgia",
    "Armenia", "Belarus", "Serbia", "Croatia", "Finland", "Denmark",
    "Iceland", "Bulgaria", "Romania", "Hungary", "Greece", "Portugal",
    "Austria", "Russia", "Turkey",
}
AFRICA = {
    "South Africa", "Nigeria", "Egypt", "Morocco", "Ghana", "Senegal", "Cameroon",
}
ASIA = {
    "Thailand", "Japan", "China", "South Korea", "Iran", "India", "Kazakhstan",
    "Philippines", "Indonesia", "Mongolia", "Uzbekistan",
}

BELTS = ("white", "blue", "purple", "brown", "black")
BELT_WEEKS = {"white": 20, "blue": 36, "purple": 48, "brown": 60}

CAMPS = {
    "A": {"id": "dagestan", "name": "Dagestan (wrestling)", "weeks": 4, "cost": 900,
          "skills": ("grappling", "takedown_def", "strength"), "style": "Wrestling"},
    "B": {"id": "thailand", "name": "Phuket (Muay Thai)", "weeks": 4, "cost": 700,
          "skills": ("kicks", "striking", "cardio"), "style": "Muay Thai"},
    "C": {"id": "brazil", "name": "Rio (BJJ)", "weeks": 4, "cost": 800,
          "skills": ("submissions", "ground_control", "fight_iq"), "style": "BJJ"},
    "D": {"id": "usa", "name": "Vegas (MMA camp)", "weeks": 3, "cost": 1200,
          "skills": ("striking", "grappling", "fight_iq"), "style": "MMA"},
}

JOBS = {
    "A": {"name": "Delivery driver", "pay": 140, "energy": 9, "risk": 1, "effect": "Flexible; low fight-camp interference"},
    "B": {"name": "Waiter", "pay": 160, "energy": 12, "risk": 1, "effect": "People skills; occasional tips", "stat": "charisma"},
    "C": {"name": "Warehouse worker", "pay": 190, "energy": 17, "risk": 2, "effect": "Physical work; strength exposure", "stat": "strength"},
    "D": {"name": "Construction worker", "pay": 240, "energy": 22, "risk": 4, "effect": "Best early cash; tiring and injury-prone", "stat": "strength"},
    "E": {"name": "Security guard", "pay": 220, "energy": 14, "risk": 2, "effect": "Steady money; reputation exposure", "stat": "confidence"},
    "F": {"name": "Bouncer", "pay": 280, "energy": 20, "risk": 5, "effect": "High cash; confrontation risk", "stat": "confidence", "requires": "strength40"},
    "G": {"name": "Lifeguard", "pay": 180, "energy": 13, "risk": 2, "effect": "Cardio-friendly seasonal work", "stat": "cardio", "requires": "cardio35"},
    "H": {"name": "Martial arts assistant", "pay": 200, "energy": 12, "risk": 1, "effect": "Technical teaching reinforces fight IQ", "stat": "fight_iq", "requires": "combat40"},
    "I": {"name": "Personal trainer", "pay": 310, "energy": 15, "risk": 1, "effect": "Good pay once your athletic reputation is real", "stat": "charisma", "requires": "trainer"},
    "J": {"name": "Private combat coach", "pay": 390, "energy": 16, "risk": 1, "effect": "Premium work for established fighters", "stat": "fight_iq", "requires": "coach"},
}



def opp_label(booked) -> str:
    if not isinstance(booked, dict):
        if booked is None:
            return "the date"
        return getattr(booked, "name", None) or str(booked)
    opp = booked.get("opponent")
    if opp is not None and not isinstance(opp, dict):
        return getattr(opp, "name", None) or "opponent"
    snap = booked.get("opponent_snap") or {}
    if isinstance(snap, dict) and snap.get("name"):
        return snap["name"]
    if isinstance(booked.get("opp"), str):
        return booked["opp"]
    return booked.get("org") or "the date"


def continent(country: str) -> str:
    c = country or ""
    if c in EUROPE:
        return "Europe"
    if c in AFRICA:
        return "Africa"
    if c in ASIA:
        return "Asia"
    if c in ("USA", "Canada", "Mexico", "Cuba"):
        return "North America"
    if c in ("Brazil", "Colombia", "Argentina", "Peru", "Chile", "Venezuela"):
        return "South America"
    if c in ("Australia", "New Zealand"):
        return "Oceania"
    return "Other"


def europe_ok(fighter) -> bool:
    return continent(getattr(fighter, "country", "") or "") == "Europe"


def next_belt(current: str | None) -> str | None:
    cur = (current or "").lower()
    if cur not in BELTS:
        return "white"
    i = BELTS.index(cur)
    if i >= len(BELTS) - 1:
        return None
    return BELTS[i + 1]


def tick_belts(fighter, console=None) -> None:
    belt = (getattr(fighter, "bjj_belt", None) or "").lower()
    if belt not in BELTS or belt == "black":
        return
    if getattr(fighter, "specialty_gym_type", "") not in ("bjj", "sambo", ""):
        if getattr(fighter, "style", "") not in ("BJJ", "Sambo"):
            return
    weeks = int(getattr(fighter, "bjj_weeks", 0) or 0) + 1
    fighter.bjj_weeks = weeks
    need = BELT_WEEKS.get(belt, 40)
    stripes = int(getattr(fighter, "bjj_stripes", 0) or 0)
    if weeks % 8 == 0 and stripes < 4:
        fighter.bjj_stripes = stripes + 1
        if console:
            console.good("BJJ stripe. %s belt, %s." % (belt, fighter.bjj_stripes))
    if weeks >= need and int(getattr(fighter, "bjj_stripes", 0) or 0) >= 4:
        nxt = next_belt(belt)
        if nxt:
            fighter.bjj_belt = nxt
            fighter.bjj_stripes = 0
            fighter.bjj_weeks = 0
            flags = getattr(fighter, "story_flags", None) or {}
            flags["bjj_%s" % nxt] = True
            fighter.story_flags = flags
            _grant_belt_techs(fighter, nxt, console)
            if console:
                console.gold("Promoted to %s belt." % nxt)


BELT_TECHS = {
    "blue": ["Closed Guard", "Sweep", "Armbar", "Triangle"],
    "purple": ["Kimura", "Guard Pass", "Butterfly Sweep", "Arm Triangle"],
    "brown": ["Rear Naked Choke", "Rear Naked", "Anaconda", "Back Take", "Take The Back", "Mount Up"],
    "black": ["Darce Choke", "Body Lock", "Peel the Hands", "Wrist Ride"],
}

BELT_RANK = {"white": 0, "blue": 1, "purple": 2, "brown": 3, "black": 4}
JUDO_RANK = {"white": 0, "yellow": 1, "orange": 2, "green": 3,
             "blue": 4, "brown": 5, "black": 6}


def belt_rank(fighter) -> int:
    return BELT_RANK.get((getattr(fighter, "bjj_belt", None) or "").lower(), 0)


def belt_accuracy(fighter, action: str) -> float:
    """Small in-cage bonus so a belt is not just a menu unlock."""
    rank = belt_rank(fighter)
    grap = {
        "sweep", "guard_pass", "escape", "scramble", "mount_up", "take_back",
        "armbar", "kimura", "triangle", "guillotine", "anaconda", "rear_naked",
    }
    if action in grap and rank > 0:
        return 0.03 * rank
    judo = JUDO_RANK.get((getattr(fighter, "judo_belt", None) or "").lower(), 0)
    if action in ("clinch_entry", "trip", "throw") and judo:
        return min(0.08, 0.014 * judo)
    return 0.0


def _grant_belt_techs(fighter, belt: str, console=None) -> None:
    names = BELT_TECHS.get((belt or "").lower(), [])
    learned = []
    for name in names:
        if hasattr(fighter, "learn_technique") and fighter.learn_technique(name):
            learned.append(name)
        elif hasattr(fighter, "level_up_technique"):
            fighter.level_up_technique(name)
    # Sharpen the grappling they already know.
    lv = dict(getattr(fighter, "technique_levels", None) or {})
    for name, lvl in list(lv.items()):
        low = name.lower()
        if any(w in low for w in ("guard", "sweep", "armbar", "triangle", "choke", "pass", "kimura")):
            lv[name] = min(5, int(lvl or 1) + 1)
    fighter.technique_levels = lv
    if getattr(fighter, "submissions", None) is not None:
        fighter.submissions = min(99, int(fighter.submissions) + 2)
        fighter.ground_control = min(99, int(fighter.ground_control) + 2)
    if console and learned:
        console.good("New belt work: %s." % ", ".join(learned))


def start_camp(fighter, key: str, console=None) -> str:
    """Delegates to camps.py — the old stat-potion version is gone."""
    from . import camps
    return camps.start(fighter, key, console)


def _legacy_start_camp(fighter, key: str) -> str:
    spec = CAMPS.get(key)
    if not spec:
        return "No camp."
    if int(getattr(fighter, "money", 0) or 0) < spec["cost"]:
        return "Need $%s." % spec["cost"]
    fighter.money -= spec["cost"]
    fighter.intl_camp = spec["id"]
    fighter.intl_camp_weeks = spec["weeks"]
    fighter.camp_active = True
    fighter.camp_focus = spec["name"]
    fighter.camp_weeks_remaining = spec["weeks"]
    return "Fly out: %s (%sw)." % (spec["name"], spec["weeks"])


def tick_camp(fighter, console=None) -> None:
    from . import camps
    camps.tick(fighter, console)


def _legacy_tick_camp(fighter, console=None) -> None:
    left = int(getattr(fighter, "intl_camp_weeks", 0) or 0)
    if left <= 0:
        return
    spec = next((c for c in CAMPS.values() if c["id"] == getattr(fighter, "intl_camp", "")), None)
    fighter.intl_camp_weeks = left - 1
    fighter.energy = max(8, int(getattr(fighter, "energy", 50) or 50) - 6)
    if spec:
        for sk in spec["skills"]:
            if hasattr(fighter, sk):
                setattr(fighter, sk, min(95, int(getattr(fighter, sk) or 40) + 1))
    if fighter.intl_camp_weeks <= 0:
        fighter.connections = list(getattr(fighter, "connections", None) or [])
        who = random.choice(("local prospect", "gym owner", "regional promoter"))
        fighter.connections.append({"place": getattr(fighter, "intl_camp", ""), "who": who})
        from .notoriety import add_fame
        add_fame(fighter, 1, "contract milestone")
        if console:
            console.good("Camp over. You met a %s." % who)
        fighter.intl_camp = None
        fighter.camp_active = False


def _job_requirement(fighter, spec: dict) -> tuple[bool, str]:
    req = str(spec.get("requires") or "")
    if not req:
        return True, ""
    if req == "strength40":
        ok = int(getattr(fighter, "strength", 0) or 0) >= 40
        return ok, "Requires Strength 40."
    if req == "cardio35":
        ok = int(getattr(fighter, "cardio", 0) or 0) >= 35
        return ok, "Requires Cardio 35."
    if req == "combat40":
        best = max(int(getattr(fighter, k, 0) or 0) for k in ("striking", "grappling", "submissions", "kicks"))
        belt = bool(getattr(fighter, "bjj_belt", None) or getattr(fighter, "judo_belt", None))
        return (best >= 40 or belt), "Requires a 40+ combat skill or a martial-arts belt."
    if req == "trainer":
        ok = int(getattr(fighter, "strength", 0) or 0) + int(getattr(fighter, "cardio", 0) or 0) >= 85
        return ok, "Requires Strength + Cardio of at least 85."
    if req == "coach":
        best = max(int(getattr(fighter, k, 0) or 0) for k in ("striking", "grappling", "submissions", "kicks"))
        ok = bool(getattr(fighter, "pro_debut", False)) and int(getattr(fighter, "fame", 0) or 0) >= 8 and best >= 55
        return ok, "Requires pro status, Fame 8 and a 55+ combat skill."
    return True, ""


def job_rows(fighter) -> list[tuple[str, dict, bool, str]]:
    rows = []
    for key, spec in JOBS.items():
        ok, why = _job_requirement(fighter, spec)
        rows.append((key, spec, ok, why))
    return rows


def work_shift(fighter, key: str) -> str:
    spec = JOBS.get(key)
    if not spec:
        return "No shift."
    if getattr(fighter, "intl_camp", None):
        return "You are abroad in an international camp. Your home job cannot be worked this week."
    ok, why = _job_requirement(fighter, spec)
    if not ok:
        return why

    name = str(spec["name"]); base_pay = int(spec["pay"]); tired = int(spec["energy"]); risk = int(spec.get("risk", 1))
    shifts = dict(getattr(fighter, "job_shifts", None) or {})
    n = int(shifts.get(name, 0) or 0) + 1
    shifts[name] = n
    fighter.job_shifts = shifts
    # Reliability produces raises, but side work never becomes a better career
    # than fighting. The cap is deliberately modest.
    raise_pct = min(0.25, (n // 6) * 0.05)
    pay = int(round(base_pay * (1.0 + raise_pct)))
    try:
        from .education import degree_benefit
        pay = int(round(pay * float(degree_benefit(fighter, "job_mult", 1.0))))
    except Exception:
        pass
    fighter.money = int(getattr(fighter, "money", 0) or 0) + pay
    fighter.energy = max(0, int(getattr(fighter, "energy", 50) or 50) - tired)
    fighter.side_job = name
    fighter.job_reputation = min(100, int(getattr(fighter, "job_reputation", 0) or 0) + 1)

    notes = ["%s +$%s" % (name, pay)]
    stat = spec.get("stat")
    # Teaching/physical exposure is slow progression, not a free training week.
    if stat and n % 4 == 0 and hasattr(fighter, stat):
        setattr(fighter, stat, min(99, int(getattr(fighter, stat, 0) or 0) + 1))
        notes.append("%s +1 from repeated work" % str(stat).replace("_", " "))

    roll = random.random()
    if risk >= 4 and roll < 0.06:
        hurt = 4 + risk
        fighter.health = max(20, int(getattr(fighter, "health", 100) or 100) - hurt)
        notes.append("rough shift: health -%s" % hurt)
    elif risk >= 2 and roll < 0.12:
        tip = 35 + 10 * risk
        fighter.money += tip
        notes.append("extra/overtime +$%s" % tip)
    elif name == "Bouncer" and roll < 0.24:
        fighter.confidence = min(100, int(getattr(fighter, "confidence", 50) or 50) + 1)
        notes.append("handled a confrontation: confidence +1")
    elif name in ("Waiter", "Personal trainer", "Private combat coach") and roll < 0.22:
        fighter.charisma = min(100, int(getattr(fighter, "charisma", 50) or 50) + 1)
        notes.append("good client interaction: charisma +1")

    debt = int(getattr(fighter, "debt", 0) or 0)
    if int(getattr(fighter, "age", 16) or 16) < 18:
        fighter.debt = 0
    elif debt > 0:
        take = min(debt, pay // 3)
        fighter.debt = debt - take
        fighter.money -= take
        notes.append("debt payment $%s ($%s left)" % (take, fighter.debt))

    history = list(getattr(fighter, "job_history", None) or [])
    history.append({"week": int(getattr(fighter, "week", 0) or 0), "job": name, "pay": pay, "energy": tired})
    fighter.job_history = history[-30:]
    return ". ".join(notes) + "."


def take_loan(fighter, amount: int = 400) -> str:
    if int(getattr(fighter, "age", 16) or 16) < 18:
        fighter.debt = 0
        return "Loans are unavailable before age 18."
    amount = max(0, int(amount or 0))
    debt = int(getattr(fighter, "debt", 0) or 0)
    # Stop the loan button becoming infinite free liquidity. Existing debt can
    # still grow through interest/overdraft, but new voluntary borrowing has a
    # visible ceiling.
    room = str(getattr(fighter, "room", "") or "")
    cap = 12000 if room == "ufc" else (6000 if getattr(fighter, "pro_debut", False) else 1800)
    room_left = max(0, cap - debt)
    amount = min(amount, room_left)
    if amount <= 0:
        return "Loan limit reached. Repay debt before borrowing more."
    fighter.debt = debt + amount
    fighter.money = int(getattr(fighter, "money", 0) or 0) + amount
    return "Borrowed $%s. Cash $%s · debt $%s." % (amount, fighter.money, fighter.debt)


def repay_debt(fighter, amount: int | None = None) -> str:
    debt = max(0, int(getattr(fighter, "debt", 0) or 0))
    cash = max(0, int(getattr(fighter, "money", 0) or 0))
    if debt <= 0:
        return "No debt to repay."
    want = debt if amount is None else max(0, int(amount or 0))
    pay = min(debt, cash, want)
    if pay <= 0:
        return "No available cash to repay debt."
    fighter.money = int(getattr(fighter, "money", 0) or 0) - pay
    fighter.debt = debt - pay
    return "Paid $%s. Cash $%s · debt $%s." % (pay, fighter.money, fighter.debt)


def tick_debt(fighter, console=None) -> None:
    if int(getattr(fighter, "age", 16) or 16) < 18:
        fighter.debt = 0
        return
    debt = int(getattr(fighter, "debt", 0) or 0)
    if debt <= 0:
        return
    # weekly slice of 5% monthly
    interest = max(1, int(debt * 0.012))
    fighter.debt = debt + interest
    if fighter.week % 4 == 0 and console:
        console.warn("Debt $%s (interest $%s)." % (fighter.debt, interest))


def sign_contract(fighter, org: str, fights: int = 4) -> str:
    try:
        from . import orgs
        orgs.sign_org(fighter, org, fights=fights)
        return "Signed %s, %s-fight deal." % (org, fights)
    except Exception:
        fighter.organization = org
        fighter.org_contract = {"org": org, "fights_left": fights, "signed_week": fighter.week}
        from . import identity
        fighter.room = identity.band_for(org, "regional")
        return "Signed %s, %s-fight deal." % (org, fights)


def can_compete(fighter) -> str:
    """Empty string = allowed. Otherwise a reason."""
    weeks = int(getattr(fighter, "suspension_weeks", 0) or 0)
    if weeks > 0:
        return "Suspended %sw. No fights, no cards." % weeks
    inj = getattr(fighter, "injury", None) or {}
    if int(inj.get("weeks", 0) or 0) > 0 and str(inj.get("severity") or inj.get("sev") or "") in ("serious", "3", "2"):
        if int(inj.get("sev", 0) or 0) >= 2 or inj.get("severity") == "serious":
            return "Hurt (%s, %sw). Rehab first." % (inj.get("area", "injury"), inj.get("weeks"))
    if int(getattr(fighter, "health", 100) or 100) < 12:
        return "Health too low."
    return ""


def clamp_money(fighter) -> None:
    """Keep UI cash and formal debt as one coherent balance sheet.

    Negative wallet balances used to coexist with loan debt, making the player
    owe the same shortfall in two different-looking places.  Any overdraft is
    now capitalised into debt and cash returns to zero.
    """
    cash = int(getattr(fighter, "money", 0) or 0)
    if int(getattr(fighter, "age", 16) or 16) < 18:
        fighter.debt = 0
        fighter.money = max(0, cash)
        return
    if cash < 0:
        fighter.debt = min(25000, int(getattr(fighter, "debt", 0) or 0) + abs(cash))
        fighter.money = 0
    else:
        fighter.money = cash


def contract_line(fighter) -> str:
    c = getattr(fighter, "org_contract", None) or {}
    if not c:
        return ""
    return "%s · %s fights left" % (c.get("org"), c.get("fights_left"))
