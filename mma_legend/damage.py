"""Locational damage, cuts and injuries (1.20).

Damage used to be two scalars, `f_dmg` and `o_dmg`. Everything funnelled into
one number, so a body kick and a head kick differed only in magnitude and the
only way to end a fight early was a head knockout.

The model here is a body map where **each location feeds a different system**,
which is what makes targeting a decision rather than a damage label:

    head   -> knockdowns, concussive KO, and it is the only KO by strikes
    body   -> steals gas; a wrecked body is how liver shots end fights late
    legs   -> mobility, kick power and takedown entries; a dead leg is a TKO
    cuts   -> a separate layer that threatens a doctor stoppage on its own

Checked kicks damage the KICKER'S leg, which is what makes checking a real
defensive skill rather than a flavour line.

Injuries carry out of the cage. A bad night leaves you with weeks of rest, and
serious trauma — a broken hand, an orbital fracture, a blown knee — needs
surgery or physio and real money.
"""
from __future__ import annotations

import random

LOCATIONS = ("head", "body", "lead_leg", "rear_leg")

# Where each action lands, and how hard, as a multiplier on raw damage.
ACTION_TARGET = {
    "jab": ("head", 0.7), "cross": ("head", 1.0), "hook": ("head", 1.15),
    "uppercut": ("head", 1.15), "head_kick": ("head", 1.5), "spin_hook_kick": ("head", 1.65), "axe_kick": ("head", 1.4), "tornado_kick": ("head", 1.7), "elbow": ("head", 1.1),
    "liver": ("body", 1.3), "knee_body": ("body", 1.35), "teep": ("body", 0.6),
    "body_kick": ("body", 1.25), "body_punch": ("body", 0.65), "side_kick": ("body", 1.0), "spin_back_kick": ("body", 1.6),
    "low_kick": ("lead_leg", 1.2), "calf_kick": ("lead_leg", 1.35),
    "gnp": ("head", 0.85), "dirty_box": ("head", 0.8),
}

# Thresholds on a 0-100 scale per location.
HURT = 45          # visibly compromised
CRITICAL = 75      # one more good shot
FAILING = 92       # the limb / the fighter is done

CUT_ZONES = ("left brow", "right brow", "forehead", "cheek", "nose")


class BodyMap:
    """Per-location damage for one fighter in one fight."""

    def __init__(self):
        self.loc = {k: 0.0 for k in LOCATIONS}
        self.concussive = 0.0     # recovers a little between rounds, never fully
        self.cuts = {}            # zone -> severity 0-100
        self.gas_penalty = 0
        self.knockdowns = 0
        self.leg_checks_taken = 0

    # ---------- accumulation ----------

    def worst_leg(self) -> tuple:
        """Return (location, damage) for the more compromised leg.

        Keeping the side matters for tactical AI: a fighter who has clearly
        damaged the rear leg should not magically keep chopping the healthy
        lead leg just because the old target API only knew ``"leg"``.
        """
        lead = float(self.loc.get("lead_leg", 0) or 0)
        rear = float(self.loc.get("rear_leg", 0) or 0)
        if rear > lead:
            return ("rear_leg", rear)
        return ("lead_leg", lead)

    def hit(self, action: str, dmg: float, target_hint: str = "") -> str:
        """Apply a landed strike. Returns the location hit."""
        loc, mult = ACTION_TARGET.get(action, ("head", 0.9))
        # A smart fighter can now select the actual compromised leg.  The
        # generic ``leg`` hint remains supported for old callers/player moves.
        if target_hint in ("lead_leg", "rear_leg"):
            loc, mult = target_hint, 1.1
        if target_hint == "body" and loc == "head":
            loc, mult = "body", 0.9
        if target_hint == "leg":
            loc, mult = "lead_leg", 1.1
        if str(target_hint).startswith("cut:"):
            # The strike still causes normal head trauma; cut worsening is a
            # separate layer handled by worsen_cut().
            loc = "head"
        # Calibrated against measured 15-minute fights so that at the final
        # bell a typical decision sits mid-range and only a genuinely one-sided
        # beating approaches the thresholds. Head was saturating at 100 in
        # every single fight before this.
        scale = {"head": 0.85, "body": 6.5, "lead_leg": 8.0, "rear_leg": 8.0}.get(loc, 1.0)
        amount = max(0.0, float(dmg)) * mult * scale
        self.loc[loc] = min(100.0, self.loc[loc] + amount)
        if loc == "head":
            self.concussive = min(100.0, self.concussive + amount * 0.8)
        if loc == "body":
            # Body work is a gas tax, not a knockout threat.
            self.gas_penalty = min(30, int(self.loc["body"] / 4))
        return loc

    def check_kick(self, attacker_map: "BodyMap") -> None:
        """This fighter checked a kick: the KICKER's leg pays."""
        attacker_map.loc["lead_leg"] = min(100.0, attacker_map.loc["lead_leg"] + random.uniform(3.0, 7.0))
        attacker_map.leg_checks_taken += 1

    def open_cut(self, action: str) -> str:
        """A cut opens, or an existing one worsens."""
        zone = random.choice(CUT_ZONES)
        if action == "elbow":
            zone = random.choice(("left brow", "right brow", "forehead"))
        cur = self.cuts.get(zone, 0)
        self.cuts[zone] = min(100, cur + random.randint(18, 38))
        return zone

    def worsen_cut(self, zone: str, action: str = "", dmg: float = 0) -> int:
        """Work an existing cut instead of opening a random new one.

        Returns the new severity.  Sharp/short-range attacks get a little more
        leverage, but cut targeting is intentionally less explosive than a
        fresh cut opening so intelligent AI does not create doctor-stoppage
        spam the instant a brow is marked.
        """
        if not zone or zone not in self.cuts:
            return 0
        sharp = action in ("elbow", "cross", "hook", "uppercut", "gnp")
        base = 5 + min(6, max(0, int(float(dmg)))) + (3 if sharp else 0)
        bump = random.randint(max(2, base - 3), base + 3)
        self.cuts[zone] = min(100, int(self.cuts.get(zone, 0) or 0) + bump)
        return int(self.cuts[zone])

    def worst_cut(self) -> tuple:
        if not self.cuts:
            return ("", 0)
        z = max(self.cuts, key=lambda k: self.cuts[k])
        return (z, self.cuts[z])

    # ---------- consequences ----------

    def leg_penalty(self) -> float:
        """0.0 - 1.0 multiplier on kicks, takedown entries and movement."""
        worst = max(self.loc["lead_leg"], self.loc["rear_leg"])
        if worst < HURT:
            return 1.0
        if worst < CRITICAL:
            return 0.75
        if worst < FAILING:
            return 0.45
        return 0.2

    def gas_drain(self) -> int:
        return int(self.gas_penalty)

    def ko_bonus(self) -> float:
        """Accumulated head trauma makes the next one more likely to land fatal."""
        return min(0.22, self.concussive / 420.0)

    def leg_tko(self) -> bool:
        """A leg that will not hold weight."""
        return max(self.loc["lead_leg"], self.loc["rear_leg"]) >= FAILING

    def body_tko(self) -> bool:
        return self.loc["body"] >= FAILING

    def cut_stoppage(self) -> bool:
        _z, sev = self.worst_cut()
        return sev >= 85

    def doctor_look(self) -> bool:
        _z, sev = self.worst_cut()
        return 60 <= sev < 85

    def between_rounds(self) -> None:
        """The corner works. Some of it comes back; trauma does not."""
        self.concussive = max(0.0, self.concussive - 6.0)
        for k in ("lead_leg", "rear_leg"):
            self.loc[k] = max(0.0, self.loc[k] - 1.5)
        self.loc["body"] = max(0.0, self.loc["body"] - 3.0)
        for z in list(self.cuts):
            self.cuts[z] = max(0, self.cuts[z] - 4)

    def status_line(self) -> str:
        bits = []
        if self.loc["head"] >= HURT:
            bits.append("head marked")
        if self.loc["body"] >= HURT:
            bits.append("body hurting")
        if max(self.loc["lead_leg"], self.loc["rear_leg"]) >= HURT:
            bits.append("leg compromised")
        z, sev = self.worst_cut()
        if sev >= 40:
            bits.append("cut %s" % z)
        return ", ".join(bits)

    def bars(self) -> list:
        """(label, 0-100 damage) for the HUD."""
        return [("hd", self.loc["head"]), ("bd", self.loc["body"]),
                ("lg", max(self.loc["lead_leg"], self.loc["rear_leg"]))]


# ------------------------------------------------------------------
# Injuries that survive the fight
# ------------------------------------------------------------------

# name -> (weeks, severity 1-3, surgery_cost, physio_weeks_saved, blurb)
INJURIES = {
    "bruised shin": (1, 1, 0, 1, "Shin is a mess. It will settle."),
    "swollen eye": (1, 1, 0, 1, "You cannot see out of it for a few days."),
    "deep cut": (3, 2, 400, 1, "Stitches. It will open again if you rush."),
    "broken nose": (3, 2, 900, 1, "Set it, breathe through your mouth for a month."),
    "broken hand": (10, 3, 2600, 3, "Boxer's fracture. Nothing loads through it."),
    "broken knuckle": (7, 2, 1500, 2, "The knuckle is flattened. Every bag session hurts."),
    "orbital fracture": (14, 3, 4200, 4, "Around the eye. Nobody argues with this one."),
    "torn knee": (24, 3, 7000, 6, "ACL. This is the one that ends people."),
    "torn shoulder": (16, 3, 5200, 4, "Labrum. You cannot even sleep on it."),
    "cracked rib": (5, 2, 700, 2, "Every breath reminds you."),
    "concussion": (6, 3, 0, 0, "Neurological. Rest is the only treatment."),
    "dead leg": (2, 1, 0, 1, "Corked. It will not hold a stance for a week."),
    "jaw fracture": (12, 3, 3800, 3, "Wired. Soup for a month."),
    "ankle sprain": (3, 1, 300, 1, "Rolled it. Watch the footwork."),
}

# Rare, memorable, outside the cage.
LIFE_INJURIES = (
    ("broken hand", "a street altercation you should have walked away from"),
    ("broken knuckle", "punching a wall after the decision"),
    ("ankle sprain", "a pothole on a morning run"),
    ("cracked rib", "a car door and a slippery kerb"),
    ("torn shoulder", "a heavy sparring round that went too long"),
    ("concussion", "a sparring partner who did not respect the light day"),
)


def _flags(fighter) -> dict:
    f = getattr(fighter, "story_flags", None)
    if not isinstance(f, dict):
        fighter.story_flags = {}
        f = fighter.story_flags
    return f


def injury_list(fighter) -> list:
    fl = _flags(fighter)
    lst = fl.get("injuries")
    if not isinstance(lst, list):
        lst = []
        fl["injuries"] = lst
    return lst


def add_injury(fighter, name: str, cause: str = "", console=None) -> dict:
    spec = INJURIES.get(name)
    if not spec:
        return {}
    weeks, sev, cost, saved, blurb = spec
    rec = {
        "name": name, "weeks": int(weeks), "severity": int(sev),
        "cause": cause, "surgery_cost": int(cost), "physio_saves": int(saved),
        "treated": False,
        "week": int(getattr(fighter, "week", 0) or 0),
    }
    injury_list(fighter).append(rec)
    # Keep the legacy single-injury field roughly in sync for old screens.
    fighter.injury = {"area": name, "weeks": int(weeks), "severity": sev}
    if sev >= 2:
        fighter.fight_cooldown = max(int(getattr(fighter, "fight_cooldown", 0) or 0), weeks)
    if console:
        console.warn("INJURY: %s%s" % (name.upper(), (" — %s" % cause) if cause else ""))
        console.print(blurb)
        console.print("Out roughly %s week(s)." % weeks)
        if cost:
            console.print("Surgery would cost $%s and save %s week(s)." % (cost, saved))
    return rec


def active_injuries(fighter) -> list:
    return [i for i in injury_list(fighter) if int(i.get("weeks", 0) or 0) > 0]


def worst_injury(fighter) -> dict:
    act = active_injuries(fighter)
    if not act:
        return {}
    return max(act, key=lambda i: (i.get("severity", 1), i.get("weeks", 0)))


def weeks_out(fighter) -> int:
    act = active_injuries(fighter)
    return max([int(i.get("weeks", 0) or 0) for i in act], default=0)


def can_fight(fighter) -> tuple:
    """(ok, reason). A serious injury is not something you fight through."""
    w = worst_injury(fighter)
    if not w:
        return (True, "")
    if int(w.get("severity", 1)) >= 3:
        return (False, "%s — %s week(s). You are not cleared."
                % (w["name"], w["weeks"]))
    if int(w.get("severity", 1)) == 2 and int(w.get("weeks", 0)) > 2:
        return (False, "%s — %s week(s). Doctor says no."
                % (w["name"], w["weeks"]))
    return (True, "")


def tick(fighter, console=None) -> None:
    """Weekly healing."""
    lst = injury_list(fighter)
    healed = []
    for rec in lst:
        w = int(rec.get("weeks", 0) or 0)
        if w <= 0:
            continue
        rate = 1
        if rec.get("treated"):
            rate = 2
        rec["weeks"] = max(0, w - rate)
        if rec["weeks"] == 0:
            healed.append(rec["name"])
    if healed:
        for n in healed:
            if console:
                console.good("Cleared: %s." % n)
        if not active_injuries(fighter):
            fighter.injury = {}
    # Keep legacy field aligned.
    w = worst_injury(fighter)
    fighter.injury = ({"area": w["name"], "weeks": w["weeks"],
                       "severity": w["severity"]} if w else {})


def treat(fighter, rec: dict, mode: str, console=None) -> str:
    """Surgery (expensive, big cut) or physio (cheaper, smaller cut)."""
    if rec.get("treated"):
        return "Already being treated."
    if mode == "surgery":
        cost = int(rec.get("surgery_cost", 0) or 0)
        try:
            from .education import degree_benefit
            cost = int(round(cost * float(degree_benefit(fighter, "rehab_mult", 1.0))))
        except Exception:
            pass
        if not cost:
            return "Surgery will not help this one. Rest is the treatment."
        fighter.money = int(getattr(fighter, "money", 0) or 0) - cost
        rec["weeks"] = max(1, int(rec["weeks"]) - int(rec.get("physio_saves", 1)) * 2)
        rec["treated"] = True
        if console:
            console.good("Surgery booked. $%s gone. Back in ~%s week(s)."
                         % (cost, rec["weeks"]))
        return "Surgery done."
    cost = max(120, int(rec.get("surgery_cost", 400) or 400) // 4)
    try:
        from .education import degree_benefit
        cost = int(round(cost * float(degree_benefit(fighter, "rehab_mult", 1.0))))
    except Exception:
        pass
    fighter.money = int(getattr(fighter, "money", 0) or 0) - cost
    rec["weeks"] = max(1, int(rec["weeks"]) - int(rec.get("physio_saves", 1)))
    rec["treated"] = True
    if console:
        console.good("Physio block booked. $%s. Back in ~%s week(s)."
                     % (cost, rec["weeks"]))
    return "Physio started."


def post_fight(fighter, body: BodyMap, lost_badly: bool, console=None) -> list:
    """Turn what happened in the cage into what you carry out of it."""
    got = []
    if body is None:
        return got
    head = body.loc["head"]
    leg = max(body.loc["lead_leg"], body.loc["rear_leg"])
    bodyd = body.loc["body"]
    _z, cut_sev = body.worst_cut()

    if cut_sev >= 55:
        got.append(add_injury(fighter, "deep cut", "cut %s" % _z, console))
    if head >= 80 or body.knockdowns >= 2:
        got.append(add_injury(fighter, "concussion", "took heavy head shots", console))
    elif head >= 62 and random.random() < 0.35:
        got.append(add_injury(fighter, "swollen eye", "eaten too many jabs", console))
    if head >= 70 and random.random() < 0.18:
        got.append(add_injury(fighter, "broken nose", "a straight down the middle", console))
    if head >= 88 and random.random() < 0.12:
        got.append(add_injury(fighter, "orbital fracture", "a clean head kick", console))
    if leg >= 70:
        got.append(add_injury(fighter, "dead leg", "leg kicks all night", console))
    elif leg >= 45 and random.random() < 0.3:
        got.append(add_injury(fighter, "bruised shin", "checked kicks", console))
    if bodyd >= 75 and random.random() < 0.4:
        got.append(add_injury(fighter, "cracked rib", "body work", console))
    # Punching a skull is how hands break.
    if random.random() < 0.05:
        got.append(add_injury(fighter, random.choice(("broken hand", "broken knuckle")),
                              "landed one on the top of his head", console))
    if lost_badly and random.random() < 0.06:
        got.append(add_injury(fighter, random.choice(("torn shoulder", "jaw fracture")),
                              "a bad night", console))
    return [g for g in got if g]


def random_life_injury(fighter, console=None, chance: float = 0.006) -> dict:
    """Rare, real, and it happens outside the cage."""
    if random.random() >= chance:
        return {}
    if active_injuries(fighter):
        return {}
    name, cause = random.choice(LIFE_INJURIES)
    return add_injury(fighter, name, cause, console)


def training_injury(fighter, intensity: float = 1.0, console=None) -> dict:
    """Hard sessions break people occasionally."""
    base = 0.004 * max(0.3, intensity)
    if int(getattr(fighter, "energy", 70) or 70) < 25:
        base *= 2.5
    if int(getattr(fighter, "age", 25) or 25) >= 33:
        base *= 1.4
    if random.random() >= base:
        return {}
    if active_injuries(fighter):
        return {}
    name = random.choice(("cracked rib", "torn shoulder", "ankle sprain",
                          "broken knuckle", "concussion", "torn knee"))
    return add_injury(fighter, name, "training", console)


def summary(fighter) -> str:
    act = active_injuries(fighter)
    if not act:
        return "Healthy."
    return "; ".join("%s (%sw%s)" % (i["name"], i["weeks"],
                                     ", treated" if i.get("treated") else "")
                     for i in act)
