"""Playable MMA fight engine (1.2).

Tick sim with gas, learned techniques, and moment choices that resolve
to the move you picked. Grappling cards cannot KO or land punches.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List

from .rules import MMARuleset
from . import positions as P
from ..damage import BodyMap
from . import scoring as SC
from ..ui import wrap_text
from .. import constants as C
from .. import physiology as PHYS
from .. import perks as PERKS
from .. import combat_intelligence as CI


@dataclass
class LogEvent:
    attacker: str = ""
    result: str = ""
    action_id: str = ""
    text: str = ""


@dataclass
class FightStats:
    strikes_landed: int = 0
    strikes_attempted: int = 0
    ground_strikes_landed: int = 0
    ground_strikes_attempted: int = 0
    head_landed: int = 0
    body_landed: int = 0
    leg_landed: int = 0
    takedowns_landed: int = 0
    takedowns_attempted: int = 0
    submission_attempts: int = 0
    control_ticks: int = 0
    control_sec: int = 0
    knockdowns: int = 0
    times_down: int = 0
    # 1.9: positional detail, so the post-fight card can explain a grappling
    # win instead of showing an empty striking line.
    passes: int = 0
    sweeps: int = 0
    escapes: int = 0
    back_takes: int = 0
    mount_ups: int = 0
    grappling_points: int = 0
    # Ruleset score (wrestling points, judo waza-ari units, sambo technical points).
    technical_points: int = 0
    turning_points: int = 0
    round_wins: int = 0

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class FightOutcome:
    winner: str = "draw"
    method: str = "Decision"
    finish_label: str | None = None
    technique: str | None = None
    f_score: int = 0
    o_score: int = 0
    periods: int = 3
    sport: str = "mma"
    notes: list = field(default_factory=list)
    log: list = field(default_factory=list)
    f_stats: FightStats = field(default_factory=FightStats)
    o_stats: FightStats = field(default_factory=FightStats)
    result_word: str = "DRAW"
    amateur: bool = True
    rules: object | None = None
    clock: str = "R1 5:00"
    end_period: int = 1
    scorecards: list = field(default_factory=list)
    f_body: object = None
    o_body: object = None
    decision_type: str = ""
    final_range: str = "boxing"
    range_control: dict = field(default_factory=dict)
    f_adjustments: list = field(default_factory=list)
    o_adjustments: list = field(default_factory=list)
    intelligence: dict = field(default_factory=dict)


class _RoundDelta:
    """Per-round view of a FightStats object.

    Scoring must look at what happened *in this round*, not at fight totals.
    """

    def __init__(self, stats, snapshot: dict):
        for key, val in stats.as_dict().items():
            setattr(self, key, val - int(snapshot.get(key, 0) or 0))


ILLEGAL_AMATEUR = frozenset({"heel_hook", "elbow", "knee_head", "ground_elbow"})

STANDING_STRIKES = frozenset({
    "jab", "cross", "hook", "uppercut", "liver", "low_kick", "head_kick",
    "body_kick", "teep", "body_punch", "side_kick", "spin_back_kick",
    "spin_hook_kick", "axe_kick", "tornado_kick", "dirty_box", "knee_body",
})
RANGE_BANDS = ("outside", "kicking", "boxing", "pocket")
RANGE_IDEAL = {
    "jab": "boxing", "cross": "boxing", "hook": "pocket", "uppercut": "pocket",
    "liver": "pocket", "low_kick": "kicking", "head_kick": "kicking",
    "body_kick": "kicking", "teep": "outside", "body_punch": "boxing",
    "side_kick": "outside", "spin_back_kick": "kicking", "spin_hook_kick": "kicking",
    "axe_kick": "kicking", "tornado_kick": "kicking", "clinch_entry": "pocket",
    "double_leg": "pocket", "single_leg": "pocket",
}


def _range_fit(action: str, band: str) -> float:
    """Accuracy adjustment for attempting an action at the current range."""
    ideal = RANGE_IDEAL.get(action)
    if not ideal or band not in RANGE_BANDS:
        return 0.0
    gap = abs(RANGE_BANDS.index(ideal) - RANGE_BANDS.index(band))
    return {0: 0.055, 1: -0.025, 2: -0.105, 3: -0.18}.get(gap, -0.18)


def _range_weight(action: str, band: str) -> float:
    ideal = RANGE_IDEAL.get(action)
    if not ideal or band not in RANGE_BANDS:
        return 1.0
    gap = abs(RANGE_BANDS.index(ideal) - RANGE_BANDS.index(band))
    return (1.32, 0.92, 0.66, 0.36)[min(3, gap)]


def _clock(sec) -> str:
    sec = max(0, int(sec or 0))
    return "%d:%02d" % (sec // 60, sec % 60)


_HOLD = {
    "mount": 1.55, "back": 1.65, "side": 1.38, "half_guard": 1.16,
    "turtle": 1.28, "closed_guard": 0.92,
}

_RIDE_FLAVOR = {
    "mount": "heavy in mount",
    "back": "hooks in on the back",
    "side": "pinning side control",
    "half_guard": "riding half guard",
    "turtle": "riding turtle",
    "closed_guard": "stuck in closed guard",
}


def _stat(f, name, default=40) -> int:
    # Combat skills are fight-night values, not blindly the stored raw number.
    # Physiology applies divisional ceilings, nutrition/cut condition and
    # injuries in one place. Non-combat state (energy etc.) stays raw.
    if name in C.SKILLS:
        return PHYS.effective_stat(f, name, default)
    try:
        return int(getattr(f, name, default) or default)
    except (TypeError, ValueError):
        return default


def _known(fighter) -> list[str]:
    return [str(x).lower() for x in (getattr(fighter, "techniques", None) or [])]


def _knows(fighter, *needles: str) -> bool:
    bag = " ".join(_known(fighter))
    return any(n.lower() in bag for n in needles if n)


def _phase_for_pos(pos: str) -> str:
    """Collapse a granular position into the coarse phase action_from_label expects."""
    if pos == "clinch":
        return "clinch"
    if pos == "stand":
        return "stand"
    return "ground"


def _auto_from_bag(fighter, pos: str, grappling_only: bool = False, role=None):
    """Pick a random known technique — but only if it is legal from the current
    position AND from this fighter's side of it. (Fixes: a fighter who knows
    'Guillotine' could previously fire a submission action while standing, an
    RNC from any ground position, or ground-and-pound from under mount.)"""
    names = list((getattr(fighter, "technique_levels", None) or {}) or [])
    names += [str(x) for x in (getattr(fighter, "techniques", None) or [])]
    if not names:
        return None
    legal = P.legal_actions(pos, grappling_only, role)
    random.shuffle(names)
    for n in names:
        act, tgt = action_from_label(n, _phase_for_pos(pos))
        if act not in legal:
            continue
        dmg = 2
        if act in ("hook", "cross", "liver", "head_kick"):
            dmg = 3
        return act, tgt, dmg
    return None


def action_from_label(label: str, phase: str) -> tuple[str, str]:
    l = (label or "").lower()
    if "spinning hook" in l or "spin hook" in l:
        return "spin_hook_kick", "head"
    if "tornado" in l:
        return "tornado_kick", "head"
    if "spinning back" in l or "spin back" in l:
        return "spin_back_kick", "body"
    if "back kick" in l:
        return "spin_back_kick", "body"
    if "axe kick" in l:
        return "axe_kick", "head"
    if "side kick" in l or "cut kick" in l:
        return "side_kick", "body"
    if "question mark" in l:
        return "head_kick", "head"
    if "front kick" in l:
        return "teep", "body"
    if "oblique" in l:
        return "low_kick", "leg"
    if "roundhouse to head" in l:
        return "head_kick", "head"
    if "roundhouse to body" in l or "roundhouse kick" in l:
        return "body_kick", "body"
    if "body punch" in l or "trunk punch" in l:
        return "body_punch", "body"
    if any(w in l for w in ("head kick", "high kick", "upstairs")):
        return "head_kick", "head"
    if "body kick" in l or "switch kick" in l:
        return "body_kick", "body"
    if any(w in l for w in ("liver", "body shot", "dig the body", "to the body")):
        return "liver", "body"
    if any(w in l for w in ("calf", "low kick", "chop", "leg kick", "the leg")):
        return "low_kick", "leg"
    if "uppercut" in l:
        return "uppercut", "head"
    if "hook" in l or "sit down" in l:
        return "hook", "head"
    if any(w in l for w in ("teep", "push kick")):
        return "teep", "body"
    if "armbar" in l:
        return "armbar", ""
    if "kimura" in l or "americana" in l:
        return "kimura", ""
    if "triangle" in l:
        return "triangle", ""
    if "guillotine" in l:
        return "guillotine", ""
    if "heel hook" in l:
        return "heel_hook", ""
    if "kneebar" in l:
        return "kneebar", ""
    if "north-south choke" in l or "north south choke" in l:
        return "north_south_choke", ""
    if "leg entry" in l:
        return "leg_entry", ""
    if "front headlock" in l or "snap" in l:
        return "snap_down", ""
    if "sweep" in l or "hip escape" in l:
        return "guard_pass", ""
    if "fireman" in l or "suplex" in l or "throw" in l or "ankle pick" in l:
        return "double_leg", ""
    if "check hook" in l or "overhand" in l:
        return "hook", "head"
    if "distance" in l or "feint" in l or "long guard" in l:
        return "jab", "head"
    if any(w in l for w in ("jab", "cross", "one-two", "down the middle")):
        return ("cross" if "cross" in l else "jab"), "head"
    if any(w in l for w in ("shoot", "double", "single", "takedown", "change levels", "level change", "mat return", "trip", "knee tap")):
        return "double_leg", ""
    if any(w in l for w in ("sprawl", "stuff", "defend the shot")):
        return "sprawl", ""
    if any(w in l for w in ("submission", "choke", "rnc", "armbar", "guillotine", "hunt the sub")):
        return "rear_naked", ""
    if any(w in l for w in ("mount", "pass", "advance", "heavy hips", "hold him")):
        return "guard_pass", ""
    if any(w in l for w in ("stand up", "get up")):
        return "stand_up", ""
    if "break" in l:
        return "break", ""
    if "clinch" in l or "frame" in l:
        return "clinch_entry", ""
    if phase == "ground":
        return "gnp", "head"
    return "jab", "head"


def _line(name, action, result, dmg, target: str = "") -> str:
    nice = action.replace("_", " ")
    if result == "miss":
        return "%s misses the %s." % (name, nice)
    if action == "rear_naked" and dmg >= 10:
        return "%s locks the choke. It's over." % name
    if dmg >= 8:
        return "%s LANDS a heavy %s." % (name, nice)
    verbs = {
        "jab": "jabs down the pipe", "cross": "fires a stiff cross",
        "hook": "whips a hook around the guard",
        "uppercut": "sneaks an uppercut up the middle",
        "liver": "digs a liver shot",
        "low_kick": ("chops the rear leg" if target == "rear_leg" else
                     "chops the lead calf"), "teep": "tees him off the pocket",
        "head_kick": "whips a high roundhouse", "body_punch": "drives a straight punch to the trunk",
        "side_kick": "stabs a side kick through the body",
        "spin_back_kick": "turns through a spinning back kick",
        "spin_hook_kick": "whips a spinning hook kick at the head",
        "axe_kick": "drops an axe kick over the guard",
        "tornado_kick": "launches a tornado kick",
        "double_leg": "changes levels — DOUBLE LEG TAKEDOWN",
        "single_leg": "picks the single — TAKEDOWN",
        "sprawl": "sprawls hard", "dirty_box": "dirty-boxes in the clinch",
        "knee_body": "knees the body on the fence",
        "gnp": "drops short ground strikes",
        "rear_naked": "sneaks the rear-naked under the chin",
        "armbar": "isolates the arm for an armbar",
        "triangle": "throws up a triangle",
        "kimura": "locks a kimura",
        "guillotine": "snatches a front headlock guillotine",
        "guard_pass": "slices through guard",
        "sweep": "hits the sweep — REVERSAL, he comes up on top",
        "scramble": "hits a scramble — hips explode, position is live",
        "escape": "works free and improves position",
        "mount_up": "steps over into MOUNT",
        "take_back": "climbs onto the BACK",
        "anaconda": "cinches an anaconda from the front headlock",
        "stand_up": "stands and resets", "break": "frames off and breaks",
        "clinch_entry": "closes the door into the clinch",
        "trip": "picks an inside trip — TAKEDOWN",
        "throw": "turns the corner on a throw",
    }
    if result == "land" and dmg >= 5:
        return "%s LANDS — %s. He feels that." % (name, nice)
    return "%s %s." % (name, verbs.get(action, nice))


def _hurt_part(who, target: str, dmg: int, action: str) -> None:
    """Accumulate head / body / leg damage that persists past the bell."""
    bag = dict(getattr(who, "damage", None) or {})
    key = target if target in ("head", "body", "leg") else (
        "leg" if action == "low_kick" else ("body" if action in ("liver", "teep", "knee_body", "body_kick", "body_punch", "side_kick", "spin_back_kick") else "head")
    )
    if key == "leg":
        bag["legs"] = min(100, int(bag.get("legs", 0) or 0) + max(1, dmg))
    elif key == "body":
        bag["body"] = min(100, int(bag.get("body", 0) or 0) + max(1, dmg))
    else:
        bag["cuts"] = min(100, int(bag.get("cuts", 0) or 0) + (1 if dmg >= 3 else 0))
        bag["eyes"] = min(100, int(bag.get("eyes", 0) or 0) + (1 if action in ("hook", "gnp") and dmg >= 2 else 0))
        bag["nose"] = min(100, int(bag.get("nose", 0) or 0) + (1 if action in ("cross", "jab") and dmg >= 3 else 0))
        bag["head"] = min(100, int(bag.get("head", 0) or 0) + max(1, dmg))
    bag["total"] = min(100, sum(int(bag.get(k, 0) or 0) for k in ("cuts", "nose", "eyes", "body", "legs", "head")))
    who.damage = bag


def _hurt(who) -> dict:
    bag = getattr(who, "damage", None) or {}
    return {k: int(bag.get(k, 0) or 0) for k in ("legs", "body", "head", "eyes", "cuts")}


def _part_mod(who, action: str) -> float:
    """The man throwing the shot is already hurt. Accuracy drops."""
    h = _hurt(who)
    mod = 1.0
    if h["legs"] >= 6 and action in (
            "low_kick", "head_kick", "teep", "throw", "trip", "double_leg", "single_leg"):
        mod *= max(0.40, 1.0 - h["legs"] / 70.0)
    if h["body"] >= 8 and action in (
            "hook", "uppercut", "head_kick", "double_leg", "throw", "knee_body"):
        # Liver shots steal the wind. Big swings and shots die first.
        mod *= max(0.48, 1.0 - h["body"] / 90.0)
    if h["head"] >= 10 and action in ("cross", "hook", "head_kick"):
        mod *= max(0.55, 1.0 - h["head"] / 110.0)
    if h["eyes"] >= 5 and action in ("jab", "cross", "hook", "uppercut", "head_kick"):
        mod *= max(0.55, 1.0 - h["eyes"] / 90.0)
    return mod


def _prey_mod(who, action: str) -> float:
    """The other man is already hurt in the place this shot attacks."""
    h = _hurt(who)
    bonus = 1.0
    if h["legs"] >= 8 and action in ("double_leg", "single_leg", "trip"):
        bonus *= 1.18
    if h["body"] >= 8 and action in ("liver", "knee_body", "hook"):
        bonus *= 1.16
    if h["head"] >= 10 and action in ("cross", "hook", "head_kick", "gnp"):
        bonus *= 1.12
    return bonus


def _damage_hunt_weight(action: str, body: BodyMap, fight_iq: int) -> float:
    """How strongly an AI notices and attacks live locational damage."""
    if body is None:
        return 1.0
    iq_read = 0.35 + min(0.65, max(0, int(fight_iq)) / 100.0)
    leg_dmg = max(body.loc["lead_leg"], body.loc["rear_leg"])
    body_dmg = body.loc["body"]
    head_dmg = body.loc["head"]
    _cut_zone, cut_dmg = body.worst_cut()
    hunt = 1.0
    if action == "low_kick" and leg_dmg >= 35:
        hunt = 1.45 if leg_dmg < 65 else 2.0
    elif action in ("double_leg", "single_leg", "trip") and leg_dmg >= 55:
        hunt = 1.25
    elif action in ("liver", "knee_body", "teep") and body_dmg >= 35:
        hunt = 1.4 if body_dmg < 65 else 1.9
    elif action in ("cross", "hook", "uppercut", "head_kick", "gnp") and head_dmg >= 45:
        hunt = 1.3 if head_dmg < 72 else 1.65
    if cut_dmg >= 50 and action in ("elbow", "cross", "hook", "gnp"):
        hunt = max(hunt, 1.45 if cut_dmg < 70 else 1.85)
    return 1.0 + (hunt - 1.0) * iq_read


def _damage_target_hint(action: str, body: BodyMap, fight_iq: int) -> str:
    """Choose the vulnerable *place* once an action has been selected.

    1.21 taught AI to prefer actions that attack damage, but low kicks still
    always landed on the lead leg and cut-hunting punches could open a random
    new cut.  This second layer makes high-IQ fighters actually aim at the
    compromised limb/cut while low-IQ fighters mostly keep their default aim.
    """
    if body is None:
        return ""
    iq = max(0, min(100, int(fight_iq or 0)))
    if action == "low_kick":
        zone, sev = body.worst_leg()
        if sev >= 35 and iq >= 55:
            return zone
        return "lead_leg"
    if action in ("liver", "knee_body", "teep", "body_kick", "body_punch", "side_kick", "spin_back_kick"):
        return "body"
    if action in ("elbow", "cross", "hook", "uppercut", "gnp"):
        zone, sev = body.worst_cut()
        if zone and sev >= 45 and iq >= 62:
            return "cut:" + zone
    if action in ("jab", "cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "gnp", "dirty_box", "elbow"):
        return "head"
    return ""


_SIGNATURE = (
    ("rear_naked", ("back",), "top"),
    ("armbar", ("mount", "side"), "top"),
    ("triangle", ("closed_guard",), "bottom"),
    ("guillotine", ("clinch", "stand"), None),
    ("head_kick", ("stand",), None),
    ("liver", ("stand", "clinch"), None),
)


def _signature_acts(who, pos, role, legal) -> list:
    known = " ".join(str(t).lower() for t in (getattr(who, "techniques", None) or []))
    hits = []
    for act, seats, need_role in _SIGNATURE:
        if act not in legal:
            continue
        if pos not in seats:
            continue
        if need_role and role != need_role:
            continue
        token = act.replace("_", " ")
        if token in known or act.split("_")[0] in known:
            hits.append(act)
    return hits


def _count_strike(stats, action, target, result, ground=False):
    strike = action in (
        "jab", "cross", "hook", "uppercut", "liver", "body_kick",
        "low_kick", "teep", "head_kick", "body_punch", "side_kick", "spin_back_kick",
        "spin_hook_kick", "axe_kick", "tornado_kick", "dirty_box", "knee_body", "gnp",
    )
    if not strike:
        return
    if ground or action == "gnp":
        stats.ground_strikes_attempted += 1
        if result == "land":
            stats.ground_strikes_landed += 1
    stats.strikes_attempted += 1
    if result != "land":
        return
    stats.strikes_landed += 1
    if target in ("leg", "lead_leg", "rear_leg") or action == "low_kick":
        stats.leg_landed += 1
    elif target == "body" or action in ("liver", "body_kick", "teep", "knee_body", "body_punch", "side_kick", "spin_back_kick"):
        stats.body_landed += 1
    else:
        stats.head_landed += 1


# name -> (action id, default target, base dmg). The action id is the single
# source of truth for legality: positions.LEGAL says which positions each
# action id may be thrown from. A technique's *name* no longer implies a
# phase of its own — two names can share an action id (e.g. "Sweep" and
# "Level Change Strike" both compile to a takedown-family action) but every
# submission now has ITS OWN action id, matching positions.py, so an Armbar
# can never fire as a Guillotine or a Rear Naked Choke from the wrong spot.
_TECH_CATALOG = [
    ("Jab", "jab", "head", 2),
    ("Cross", "cross", "head", 3),
    ("Hook", "hook", "head", 3),
    ("Uppercut", "uppercut", "head", 3),
    ("Low Kick", "low_kick", "leg", 2),
    ("Body Kick", "body_kick", "body", 3),
    ("Teep", "teep", "body", 2),
    ("Head Kick", "head_kick", "head", 4),
    ("Side Kick", "side_kick", "body", 2),
    ("Cut Kick", "side_kick", "body", 2),
    ("Spinning Back Kick", "spin_back_kick", "body", 5),
    ("Back Kick", "spin_back_kick", "body", 4),
    ("Spinning Hook Kick", "spin_hook_kick", "head", 5),
    ("Axe Kick", "axe_kick", "head", 4),
    ("Tornado Kick", "tornado_kick", "head", 5),
    ("Roundhouse to Body", "body_kick", "body", 3),
    ("Roundhouse to Head", "head_kick", "head", 4),
    ("Body Punch", "body_punch", "body", 1),
    ("Double Leg", "double_leg", "", 2),
    ("Single Leg", "single_leg", "", 2),
    ("Sprawl", "sprawl", "", 0),
    ("Clinch Entry", "clinch_entry", "", 1),
    ("Dirty Boxing", "dirty_box", "head", 2),
    ("Trip", "trip", "", 2),
    ("Throw", "throw", "", 2),
    ("Break", "break", "", 0),
    ("Ground and Pound", "gnp", "head", 2),
    ("Knee Slice Pass", "guard_pass", "", 1),
    ("Sweep", "sweep", "", 1),
    ("Escape", "escape", "", 0),
    ("Mount Up", "mount_up", "", 1),
    ("Take The Back", "take_back", "", 1),
    ("Anaconda", "anaconda", "", 4),
    ("Stand Up", "stand_up", "", 0),
    ("Rear Naked Choke", "rear_naked", "", 4),
    ("Rear Naked", "rear_naked", "", 4),
    ("Armbar", "armbar", "", 4),
    ("Triangle", "triangle", "", 4),
    ("Kimura", "kimura", "", 4),
    ("Guillotine", "guillotine", "", 4),
    ("Liver Shot", "liver", "body", 3),
    ("Body Jab", "jab", "body", 2),
    ("Lead Hook", "hook", "head", 3),
    ("Check Hook", "hook", "head", 3),
    ("Switch Kick", "low_kick", "leg", 3),
    ("Feint Entry", "jab", "head", 1),
    ("Level Change Strike", "double_leg", "", 2),
    ("Scramble", "scramble", "", 1),
    ("Closed Guard", "guard_pass", "", 1),
    ("Cage Wrestling", "clinch_entry", "", 1),
    ("Knee Body", "knee_body", "body", 3),
    ("Heel Hook", "heel_hook", "", 4),
    ("Inside Heel Hook", "heel_hook", "", 4),
    ("Outside Heel Hook", "heel_hook", "", 4),
    ("Kneebar", "kneebar", "", 4),
    ("Rolling Kneebar", "kneebar", "", 4),
    ("North-South Choke", "north_south_choke", "", 4),
    ("Front Headlock Snap", "snap_down", "", 1),
    ("Sprawl to Front Headlock", "snap_down", "", 1),
    ("Leg Entry", "leg_entry", "", 1),
    ("North-South", "north_south_move", "", 1),
    ("Ride", "ride", "", 0),
]

_TECH_BY_NAME = {name.lower(): (action, target, dmg) for name, action, target, dmg in _TECH_CATALOG}

# Broad abilities are skills, never buttons a fighter presses mid-fight.
from ..techniques import CONCEPT_SKILLS, REACTION_TECHNIQUES, reaction_bonus
_PASSIVE_NAMES = set(CONCEPT_SKILLS) | set(REACTION_TECHNIQUES)

# Always-safe fallbacks per action, tried in order, used only if nothing else
# is offered (e.g. a fresh NPC with an empty technique bag).
_SAFETY_NET = (
    ("Knee Slice Pass", "guard_pass", "", 1),
    ("Escape", "escape", "", 0),
    ("Sweep", "sweep", "", 1),
    ("Stand Up", "stand_up", "", 0),
    ("Break", "break", "", 0),
    ("Clinch Entry", "clinch_entry", "", 1),
    ("Sprawl", "sprawl", "", 0),
    ("Jab", "jab", "head", 2),
)

# Basics every fighter can attempt regardless of what they have "learned" —
# you do not need a certificate to try to stand up or escape a bad spot.
_ALWAYS_AVAILABLE = frozenset({
    "Jab", "Cross", "Sprawl", "Stand Up", "Break", "Guard Pass",
    "Escape", "Sweep", "Mount Up", "Take The Back", "Scramble",
})


def _action_known(fighter, action: str) -> bool:
    """Whether the fighter has learned a named technique for this action."""
    names = [str(x).lower() for x in (getattr(fighter, "techniques", None) or [])]
    names += [str(x).lower() for x in (getattr(fighter, "technique_levels", None) or {}).keys()]
    for name, act, _target, _dmg in _TECH_CATALOG:
        if act != action:
            continue
        needle = name.lower()
        if name in _ALWAYS_AVAILABLE or any(needle in k or k in needle for k in names):
            return True
    return False


def _tech_options(fighter, pos, amateur, grappling_only, role=None, rules=None):
    """Options offered to the player this moment — filtered through the same
    positions.legal_actions() the AI and resolve_action() both use, so a
    submission or strike never appears in a menu it could not legally land
    from, and never from the wrong side of the position (no ground-and-pound
    from underneath mount, no choke when it is your back being taken)."""
    known = _known(fighter)
    legal = P.legal_actions(pos, grappling_only, role)
    if rules is not None:
        legal = {a for a in legal if rules.allows_action(a)}
    out = []
    for name, action, target, dmg in _TECH_CATALOG:
        if action not in legal:
            continue
        if grappling_only and action in P.GRAPPLING_BANNED:
            continue
        if grappling_only and any(w in name.lower() for w in ("kick", "punch", "jab", "hook", "cross", "elbow", "hammer")):
            if action not in ("double_leg", "single_leg", "trip", "throw", "scramble", "clinch_entry", "sprawl"):
                continue
        if amateur and action in ILLEGAL_AMATEUR:
            continue
        needle = name.lower()
        if not any(needle in k or k in needle or name.split()[0].lower() in k for k in known):
            if name not in _ALWAYS_AVAILABLE:
                continue
        out.append((name, action, target, dmg))
    catalog_names = {row[0].lower() for row in _TECH_CATALOG}
    passive_names = {p.lower() for p in _PASSIVE_NAMES}
    for k in known:
        if any(k in n or n in k for n in catalog_names):
            continue
        if any(k in p or p in k for p in passive_names):
            continue
        guess_action, guess_target = action_from_label(k, _phase_for_pos(pos))
        if guess_action not in legal:
            continue
        out.append((k.title(), guess_action, guess_target, 2))
    if not out:
        for name, action, target, dmg in _SAFETY_NET:
            if action in legal:
                out.append((name, action, target, dmg))
        if not out and legal:
            action = sorted(legal)[0]
            target = "head" if action in ("gnp", "dirty_box") else ("leg" if action == "low_kick" else "")
            out.append((action.replace("_", " ").title(), action, target, 1))
    seen, slim = set(), []
    for row in out:
        if row[0] in seen:
            continue
        seen.add(row[0])
        slim.append(row)
        if len(slim) >= 4:
            break
    return slim


def _ask_tech(console, fighter, period, pos, amateur, grappling_only, role=None, rules=None):
    opts = _tech_options(fighter, pos, amateur, grappling_only, role, rules)
    letters = "ABCDEF"
    try:
        if hasattr(console, "moment"):
            console.moment(period, P.label(pos, role), [r[0] for r in opts])
            raw = (console.ask("Move > ") or "A").strip().upper()
            idx = "ABCDEF".find(raw[:1])
            if idx < 0 or idx >= len(opts):
                idx = 0
            name, act, tgt, dmg = opts[idx]
            return name, act, tgt, dmg
        console.print("MOMENT R%s · %s" % (period, P.label(pos, role)))
        legal = P.legal_actions(pos, grappling_only, role)
        if rules is not None:
            legal = {a for a in legal if rules.allows_action(a)}
        sigs = set(_signature_acts(fighter, pos, role, legal))
        for i, row in enumerate(opts):
            star = " *" if row[1] in sigs else ""
            console.print("  %s) %s%s" % (letters[i], row[0], star))
        raw = (console.ask("Move > ") or "A").strip().upper()
    except Exception:
        raw = "A"
    idx = letters.find(raw[:1]) if raw else 0
    if idx < 0 or idx >= len(opts):
        idx = 0
    return opts[idx]


def _gas_mod(gas: int) -> float:
    if gas >= 55:
        return 1.0
    if gas >= 35:
        return 0.82
    if gas >= 18:
        return 0.64
    return 0.45


def simulate_fight(fighter, opponent, rules=None, gameplan="Balanced", console=None, interactive=False):
    rules = rules or MMARuleset(amateur=True)
    amateur = bool(getattr(rules, "amateur", True))
    grappling_only = bool(getattr(rules, "grappling_only", False))
    periods = int(getattr(rules, "periods", 3) or 3)
    ticks_n = max(10, min(16, int(getattr(rules, "ticks_per_period", 12) or 12)))
    period_len = int(getattr(rules, "period_seconds", 180 if amateur else 300) or 300)
    sport = getattr(rules, "sport", "mma") or "mma"
    detail = str(getattr(fighter, "fight_details", "Round") or "Round")
    live = bool(interactive and console is not None)
    instant = bool(detail in ("Instant", "Quick"))
    show = bool(live and detail in ("Round", "Full"))
    compact = bool(live and detail == "Sim")
    moments_per = 0 if (not live or instant) else (5 if detail == "Full" else 4 if compact else 3)

    fname = getattr(fighter, "name", "You")
    oname = getattr(opponent, "name", "Opp")
    # Short labels for the live feed. Full names are 14+ characters and ate a
    # phone line every single exchange, which is most of why the fight read as
    # a wall of text.
    short_f = (str(fname).split()[-1] if fname else "You")[:8]
    short_o = (str(oname).split()[-1] if oname else "Opp")[:8]
    _recent_lines = []
    fs, os_ = FightStats(), FightStats()
    log: List[LogEvent] = []
    notes: list[str] = []
    # Repetition belongs to each fighter. A shared counter made one man's jab
    # usage reduce the other man's accuracy and distorted style matchups.
    used: dict[bool, dict[str, int]] = {True: {}, False: {}}
    mom = 0
    f_gas = max(20, min(100, _stat(fighter, "energy", 80)))
    o_gas = max(20, min(100, _stat(opponent, "energy", 80)))
    f_cardio = _stat(fighter, "cardio")
    o_cardio = _stat(opponent, "cardio")
    # Per-fight body maps: head / body / legs / cuts, each feeding a
    # different system rather than one damage scalar.
    f_body, o_body = BodyMap(), BodyMap()
    f_dmg = o_dmg = 0
    f_pts = o_pts = 0
    # Every match starts on the feet — including no-gi, which used to be
    # pinned to closed guard on every single tick and so could never progress.
    pos = "stand"
    # Reach does not add damage. It helps decide who gets to operate at their
    # preferred distance and how comfortable a technique is from that band.
    range_band = "boxing"
    range_control = {True: 0, False: 0}
    counter_ready = {True: False, False: False}
    # Who holds the top of the current ground position. None while neutral
    # (stand / clinch). Without this the engine could not tell "you mounted him"
    # from "he mounted you" and offered both fighters the same options.
    top_is_player = None
    control = 0
    last_p = ""
    last_act = {True: "", False: ""}
    finish = technique = None
    winner, method = "draw", "Decision"
    scorecards = []
    # Per-fighter tally of how often each action got stuffed, so the AI can
    # notice a move is not working and stop feeding it.
    stuffed = {True: {}, False: {}}
    landed_count = {True: {}, False: {}}
    last_acts = {True: [], False: []}
    intel = {True: CI.make_state(fighter, opponent), False: CI.make_state(opponent, fighter)}
    judged_sport = sport in ("mma", "boxing", "kickboxing")
    judges = SC.make_judges() if judged_sport else []
    tkd_round_wins = {True: 0, False: 0}
    tkd_match_complete = False

    def _auto_plan(who) -> dict:
        """Independent tactical identity for NPCs and non-MMA sport sims."""
        style = str(getattr(who, "archetype", "") or getattr(who, "style", "") or "").lower()
        striking = _stat(who, "striking") + _stat(who, "kicks") * 0.65
        grap = _stat(who, "grappling") + _stat(who, "ground_control") * 0.55
        subs = _stat(who, "submissions") + _stat(who, "ground_control") * 0.35
        if sport == "wrestling":
            return {"name":"Wrestle-heavy","target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"movement"}
        if sport == "judo":
            return {"name":"Clinch & Control","target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"guard"}
        if sport == "grappling":
            return {"name":"Submission Hunter" if subs >= grap else "Wrestle-heavy", "target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"guard"}
        if sport == "taekwondo":
            return {"name":"Taekwondo Range","target":"head","pace":"mid","td":"Safe","range":"kicking","defense":"movement"}
        if sport == "combat_sambo":
            if any(x in style for x in ("sambo","wrest","judo")) or grap > striking + 8:
                return {"name":"Clinch & Control","target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"guard"}
            return {"name":"Pressure","target":"head","pace":"high","td":"Opportunistic","range":"boxing","defense":"guard"}
        # MMA opening plans are matchup-aware in v1.39.
        try:
            other = opponent if who is fighter else fighter
            return CI.choose_mma_plan(who, other)
        except Exception:
            return {"name":"Balanced","target":"body","pace":"mid","td":"Opportunistic","range":"boxing","defense":"guard"}


    # Player plan is explicit in MMA. Side-sport bouts use an art-appropriate
    # automatic plan rather than leaking a stale MMA plan from a prior fight.
    if sport == "mma" and bool(getattr(fighter, "is_player", False)):
        fp = dict(getattr(fighter, "_fight_plan", None) or {})
        fp.setdefault("name", str(gameplan or "Balanced"))
        fp.setdefault("target", "body"); fp.setdefault("pace", "mid")
        fp.setdefault("td", "Opportunistic"); fp.setdefault("range", "boxing")
        fp.setdefault("defense", "guard")
        fighter._fight_plan = fp
    else:
        # NPC-vs-NPC fights must be symmetric: both sides receive the same
        # matchup-aware planner.  The old slot-1 default Balanced plan became
        # a material bias once v1.39 made the opponent planner smarter.
        fighter._fight_plan = _auto_plan(fighter)
    opponent._fight_plan = _auto_plan(opponent)

    def _preferred_range(who) -> str:
        plan = getattr(who, "_fight_plan", None) or {}
        explicit = str(plan.get("range") or "").lower()
        if explicit in RANGE_BANDS:
            return explicit
        style = str(getattr(who, "archetype", "") or getattr(who, "style", "") or "").lower()
        if any(x in style for x in ("kick", "muay", "karate", "taekwondo")):
            return "kicking"
        if any(x in style for x in ("wrest", "sambo", "judo", "pressure", "brawler")):
            return "pocket"
        return "boxing"

    def _move_range_toward(target: str) -> None:
        nonlocal range_band
        if target not in RANGE_BANDS:
            return
        here, there = RANGE_BANDS.index(range_band), RANGE_BANDS.index(target)
        if here < there:
            range_band = RANGE_BANDS[here + 1]
        elif here > there:
            range_band = RANGE_BANDS[here - 1]

    def _contest_range() -> None:
        """One symmetric range-control contest per standing exchange."""
        if pos != "stand":
            return
        f_score = (_stat(fighter, "distance_management") * 1.4 +
                   _stat(fighter, "fight_iq") * 0.35 + _stat(fighter, "speed") * 0.25 +
                   (int(getattr(fighter, "reach", 177) or 177) - 177) * 0.8)
        f_score += reaction_bonus(fighter, "distance_management") * 100
        o_score = (_stat(opponent, "distance_management") * 1.4 +
                   _stat(opponent, "fight_iq") * 0.35 + _stat(opponent, "speed") * 0.25 +
                   (int(getattr(opponent, "reach", 177) or 177) - 177) * 0.8)
        o_score += reaction_bonus(opponent, "distance_management") * 100
        p = max(0.24, min(0.76, 0.5 + (f_score - o_score) / 300.0))
        winner = random.random() < p
        range_control[winner] += 1
        _move_range_toward(_preferred_range(fighter if winner else opponent))

    def role_of(is_p):
        """'top' / 'bottom' for this fighter in the current position, or None
        when the position is neutral."""
        if pos in P.NEUTRAL or top_is_player is None:
            return None
        return "top" if (is_p == top_is_player) else "bottom"

    def _ci_damage(body_map):
        try:
            _zone, cut = body_map.worst_cut()
            return {
                "head": int(body_map.loc.get("head", 0) or 0),
                "body": int(body_map.loc.get("body", 0) or 0),
                "legs": int(max(body_map.loc.get("lead_leg", 0) or 0, body_map.loc.get("rear_leg", 0) or 0)),
                "cuts": int(cut or 0),
            }
        except Exception:
            return {"head": 0, "body": 0, "legs": 0, "cuts": 0}

    def _score_margin(is_p):
        if judged_sport and judges:
            a, b = judges[0].totals
        else:
            a, b = int(fs.technical_points), int(os_.technical_points)
        return float((a - b) if is_p else (b - a))

    def drain(is_p, cost):
        nonlocal f_gas, o_gas
        who = fighter if is_p else opponent
        save = (f_cardio if is_p else o_cardio) / 400.0
        pace = str((getattr(who, "_fight_plan", None) or {}).get("pace", "mid") or "mid").lower()
        pace_mult = 1.13 if pace == "high" else (0.88 if pace == "low" else 1.0)
        mass_mult = PHYS.gas_cost_multiplier(who) * PERKS.gas_cost_multiplier(who, period)
        prep = intel.get(is_p, {}).get("prep", {}) or {}
        pace_rehearsal = min(0.06, int(prep.get("pace_plan", 0) or 0) * 0.009)
        burned = max(1, int(round(cost * (1.15 - save) * pace_mult * mass_mult * (1.0 - pace_rehearsal))))
        if is_p:
            f_gas = max(4, f_gas - burned)
        else:
            o_gas = max(4, o_gas - burned)

    def try_ko(is_p, action, dmg):
        nonlocal finish, technique, winner, method
        if grappling_only or dmg < 4:
            return False
        ko = _stat(fighter if is_p else opponent, "ko_power")
        dur = _stat(opponent if is_p else fighter, "durability")
        chance = 0.06 + max(0, dmg - 3) * 0.04 + (ko - dur) / 280.0
        # A head that has already taken a beating goes out easier.
        chance += (o_body if is_p else f_body).ko_bonus()
        if sport == "taekwondo":
            # Kyorugi allows stoppages, but most matches are won on rounds/points.
            chance *= 0.05
        victim = opponent if is_p else fighter
        chance *= PERKS.ko_received_multiplier(victim)
        ko_floor, ko_cap = (0.003, 0.08) if sport == "taekwondo" else (0.03, 0.38)
        if random.random() > max(ko_floor, min(ko_cap, chance)):
            return False
        finish = "KO" if is_p else "KO Loss"
        technique, winner, method = action, ("player" if is_p else "opponent"), "KO"
        if show or compact:
            try:
                console.print("  IT'S OVER — KO.")
            except Exception:
                pass
        return True

    def try_sub(is_p, action):
        nonlocal finish, technique, winner, method
        att = fighter if is_p else opponent
        de = opponent if is_p else fighter
        skill = _stat(att, "submissions")
        # Holding the dominant side of the position is what actually finishes
        # submissions — a rear naked choke from back control is a different
        # proposition from a scrambled guillotine.
        top = (role_of(is_p) == "top")
        chance = 0.06 + skill / 400.0 - _stat(de, "fight_iq") / 600.0 + (0.10 if top else -0.04)
        if action == "rear_naked" and pos == "back":
            chance += 0.06
        # The defender's own grappling is a real defence, not just fight IQ.
        chance -= _stat(de, "submissions") / 1100.0
        chance -= _stat(de, "grappling") / 1300.0
        chance -= (_stat(de, "submission_def") - 40) / 650.0
        # A gassed fighter defends chokes badly.
        d_gas = o_gas if is_p else f_gas
        if d_gas <= 25:
            chance += 0.05
        if not _knows(att, "choke", "rear", "armbar", "triangle", "guillotine", "submission"):
            chance *= 0.65
        if random.random() > max(0.03, min(0.32, chance)):
            return False
        if sport == "judo":
            finish = "Ippon" if is_p else "Ippon Loss"
            technique, winner, method = action, ("player" if is_p else "opponent"), "Ippon (Submission)"
        else:
            finish = "Submission" if is_p else "Submission Loss"
            technique, winner, method = action, ("player" if is_p else "opponent"), "Submission"
        if show or compact:
            try:
                console.print("  TAP. Submission — %s." % action.replace("_", " "))
            except Exception:
                pass
        return True

    def _takedown_accuracy(att, de, action, is_p, chained=False):
        """Entry + finish vs a real defensive profile, not one flat grappling roll."""
        gas = f_gas if is_p else o_gas
        mymap = f_body if is_p else o_body
        # Different takedowns demand different blends of speed/strength.
        if action == "throw":
            atk = (_stat(att,"grappling")*.48 + _stat(att,"strength")*.28 + _stat(att,"fight_iq")*.14 + _stat(att,"speed")*.10)
            dfn = (_stat(de,"takedown_def")*.52 + _stat(de,"strength")*.23 + _stat(de,"fight_iq")*.15 + _stat(de,"grappling")*.10)
            base = .44
        elif action == "trip":
            atk = (_stat(att,"grappling")*.50 + _stat(att,"speed")*.20 + _stat(att,"fight_iq")*.18 + _stat(att,"strength")*.12)
            dfn = (_stat(de,"takedown_def")*.55 + _stat(de,"speed")*.18 + _stat(de,"fight_iq")*.17 + _stat(de,"grappling")*.10)
            base = .46
        else:
            atk = (_stat(att,"grappling")*.48 + _stat(att,"speed")*.22 + _stat(att,"strength")*.18 + _stat(att,"fight_iq")*.12)
            dfn = (_stat(de,"takedown_def")*.57 + _stat(de,"speed")*.16 + _stat(de,"strength")*.14 + _stat(de,"fight_iq")*.13)
            base = .45
        acc = base + (atk - dfn) / 175.0
        # Good shots are created by strikes, clinch contact and chain attempts.
        prev = last_act[is_p]
        if prev in ("jab","cross","hook","low_kick","teep","dirty_box","knee_body"):
            acc += .065
        if pos == "clinch" and action in ("trip","throw","single_leg"):
            acc += .06
        if pos == "stand" and range_band == "outside" and action in ("double_leg","single_leg"):
            acc -= .07
        if chained:
            acc += .07
        plan = getattr(att,"_fight_plan",None) or {}
        td = str(plan.get("td") or "Opportunistic")
        if td == "Aggressive": acc += .035
        elif td == "Safe": acc -= .035
        if str(plan.get("name") or "") in ("Wrestle-heavy","Clinch & Control"):
            acc += .025
        if _action_known(att, action):
            acc += .035
        acc += PHYS.size_matchup_modifier(att, de) * .85
        acc += CI.takedown_entry_bonus(att, de, action, intel[is_p].get("prep", {}))
        acc -= CI.takedown_defense_bonus(de, att, action, intel[not is_p].get("prep", {}))
        acc *= _gas_mod(gas) * (0.55 + 0.45*mymap.leg_penalty()) * _part_mod(att, action) * _prey_mod(de, action)
        return max(.08, min(.82, acc))

    def _award_sport_points(ast, pts: int):
        pts=max(0,int(pts or 0))
        ast.technical_points += pts
        # Keep legacy grappling_points useful in saved stat cards.
        if sport != "mma":
            ast.grappling_points += pts

    def _technical_finish(is_p) -> bool:
        nonlocal finish, technique, winner, method
        mine = fs if is_p else os_; other = os_ if is_p else fs
        diff = mine.technical_points - other.technical_points
        if sport == "wrestling" and diff >= 10:
            finish = "Technical Superiority" if is_p else "Technical Superiority Loss"
            technique = "points"; winner = "player" if is_p else "opponent"; method = "Technical Superiority"
            return True
        if sport == "combat_sambo" and (diff >= 8 or mine.knockdowns >= 2):
            finish = "Total Victory" if is_p else "Total Victory Loss"
            technique = "technical points" if diff >= 8 else "two knockdowns"
            winner = "player" if is_p else "opponent"
            method = "Total Victory (8-point lead)" if diff >= 8 else "Total Victory (2 knockdowns)"
            return True
        if sport == "judo" and mine.technical_points >= 2:
            finish = "Ippon" if is_p else "Ippon Loss"
            technique = "two waza-ari"; winner = "player" if is_p else "opponent"; method = "Ippon (Waza-ari-awasete-ippon)"
            return True
        return False

    def resolve_action(is_p, action, target, intended, chained=False):
        nonlocal pos, control, f_dmg, o_dmg, last_p, mom, top_is_player, pending_sig, f_gas, o_gas, range_band, finish, technique, winner, method
        att = fighter if is_p else opponent
        de = opponent if is_p else fighter
        ast = fs if is_p else os_
        name = fname if is_p else oname
        gas = f_gas if is_p else o_gas
        pre_knockdowns = int(ast.knockdowns)
        requested_action, requested_target = action, target
        pre_pos, pre_range, pre_f_gas, pre_o_gas = pos, range_band, f_gas, o_gas
        if amateur and action in ILLEGAL_AMATEUR:
            action, target = "jab", "head"
        if grappling_only and action in (
            "jab", "cross", "hook", "uppercut", "liver", "low_kick", "teep",
            "head_kick", "dirty_box", "knee_body", "gnp",
        ):
            action, target = "guard_pass", ""
        # Final legality gate: whatever chose this action (moment picker, AI
        # branch, or a technique pulled from the bag), it must be throwable
        # from the current position AND from this fighter's side of it. No RNC
        # from stand, no triangle from side control, no head kick from mount,
        # and no ground-and-pound from underneath somebody.
        my_role = role_of(is_p)
        legal_here = {a for a in P.legal_actions(pos, grappling_only, my_role)
                      if rules.allows_action(a)}
        if action not in legal_here:
            for fallback in ("escape", "guard_pass", "stand_up", "sweep"):
                if fallback in legal_here:
                    action, target = fallback, ""
                    break
            else:
                if legal_here:
                    action = sorted(legal_here)[0]
                    target = "head" if action in ("gnp", "dirty_box") else (
                        "leg" if action == "low_kick" else "")
                else:
                    action, target = "sprawl", ""

        # General actions use relative athleticism rather than an absolute speed
        # bonus that pushed every elite striker into the 86% accuracy clamp.
        # Specialized takedown/submission formulas below still override this.
        speed_edge = (_stat(att, "speed") - _stat(de, "speed")) / 650.0
        iq_term = (_stat(att, "fight_iq") - 40) / 950.0
        acc = 0.52 * _gas_mod(gas) + speed_edge + iq_term
        acc += PHYS.camp_accuracy_bonus(att) + PHYS.scouting_accuracy_bonus(att)
        # A compromised leg cannot throw kicks or drive through a shot.
        _mymap = f_body if is_p else o_body
        if action in ("low_kick", "head_kick", "teep", "body_kick", "calf_kick", "side_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
            acc *= _mymap.leg_penalty()
        elif action in ("double_leg", "single_leg", "throw", "trip"):
            acc *= (0.55 + 0.45 * _mymap.leg_penalty()) * _part_mod(att, action) * _prey_mod(de, action)
        try:
            from ..systems15 import belt_accuracy
            acc += belt_accuracy(att, action)
        except Exception:
            pass
        if pos == "stand" and action in STANDING_STRIKES:
            # Active striking defence and distance are opposed skills. Reach
            # is useful at long range, a liability in the pocket, and never a
            # damage multiplier.
            acc += _range_fit(action, range_band)
            acc -= (_stat(de, "striking_def") - 40) / 440.0
            acc -= reaction_bonus(de, "striking_def")
            acc -= CI.striking_defense_bonus(de, att, action, intel[not is_p].get("prep", {}))
            dm_edge = _stat(att, "distance_management") - _stat(de, "distance_management")
            acc += max(-0.055, min(0.055, dm_edge / 700.0))
            reach_edge = int(getattr(att, "reach", 177) or 177) - int(getattr(de, "reach", 177) or 177)
            reach_sign = 1.0 if range_band in ("outside", "kicking", "boxing") else -0.65
            acc += max(-0.045, min(0.045, reach_edge * reach_sign / 260.0))
            defense = str((getattr(de, "_fight_plan", None) or {}).get("defense", "guard")).lower()
            if defense == "movement":
                acc -= max(0.0, (_stat(de, "distance_management") - 35) / 900.0)
            elif defense == "guard":
                acc -= max(0.0, (_stat(de, "striking_def") - 35) / 1050.0)
            if counter_ready[is_p]:
                acc += 0.065
                counter_ready[is_p] = False
        # Combinations: following a jab with a power shot. This was gated on
        # `is_p` and `last_p` was only ever written for the player, so the
        # opponent could never throw a combination at all — the single
        # biggest reason a boxing clone-vs-clone fight came out 63/37.
        if last_act[is_p] in ("jab", "feint", "cross") and action in ("cross", "hook", "liver"):
            acc += 0.10
            intended = max(intended, intended + 1)
        # Kick setups: hands/front kicks create the opening; naked spins are risky.
        if action in ("body_kick", "head_kick", "side_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
            if last_act[is_p] in ("jab", "cross", "teep", "side_kick", "body_punch"):
                acc += 0.065
            if last_act[is_p] in ("body_kick", "low_kick") and action in ("head_kick", "axe_kick"):
                acc += 0.04
        if action == "side_kick":
            acc += (_stat(att, "distance_management") - _stat(de, "distance_management")) / 900.0
        elif action == "spin_back_kick":
            acc -= 0.055
            intended += 1
        elif action == "spin_hook_kick":
            acc -= 0.095
            intended += 1
        elif action == "axe_kick":
            acc -= 0.07
        elif action == "tornado_kick":
            acc -= 0.12
            intended += 2
        if used[is_p].get(action, 0) >= 3:
            acc -= 0.06
            if action == "low_kick":
                notes.append("checking the calf")
        # Momentum is signed toward the player, but it must cut BOTH ways.
        # Previously both branches were gated on `is_p`, so the player gained
        # from their own momentum while the opponent gained nothing from
        # theirs — a permanent one-sided accuracy edge.
        my_mom = mom if is_p else -mom
        if my_mom > 4:
            acc += 0.04
        elif my_mom < -4:
            acc -= 0.03
        if action in ("single_leg", "ankle_pick", "trip", "throw"):
            ast.takedowns_attempted += 1
            acc = _takedown_accuracy(att, de, action, is_p, chained=chained)
            if action == "ankle_pick":
                acc += 0.025
        if action in P.SUBMISSIONS:
            ast.submission_attempts += 1
            acc = 0.20 + _stat(att, "submissions") / 260.0
            if not _action_known(att, action):
                acc -= 0.05
            if action == "triangle":
                acc += 0.03
            if action == "kimura":
                acc += _stat(att, "strength") / 500.0
            if action == "guillotine":
                acc += 0.02
            acc -= _stat(de, "grappling") / 850.0
            acc -= (_stat(de, "submission_def") - 40) / 560.0
            acc -= reaction_bonus(de, "submission_def")
            acc -= CI.submission_defense_bonus(de, att, intel[not is_p].get("prep", {}))
        if action == "scramble":
            acc = (0.38 + _stat(att, "speed") / 280.0 + _stat(att, "grappling") / 360.0
                   - _stat(de, "ground_control") / 400.0 + PHYS.size_matchup_modifier(att, de) * 0.35) * _gas_mod(gas)
        if action == "stand_up":
            # Standing up was never given a contested roll, so it fell through
            # to the default ~58% per tick and the bottom fighter simply stood
            # whenever they liked. A wrestler held 22 seconds per takedown.
            acc = (0.26 + _stat(att, "grappling") / 320.0 + _stat(att, "strength") / 520.0
                   - _stat(de, "ground_control") / 240.0 - PHYS.size_matchup_modifier(de, att) * 0.35) * _gas_mod(gas)
            if pos in ("mount", "back", "side"):
                acc -= 0.14
            acc = max(0.05, acc)
        if action in ("escape", "sweep"):
            # Getting out from underneath: grappling and strength vs the top
            # fighter's control, and it is much harder when you are gassed.
            acc = (0.30 + _stat(att, "grappling") / 300.0 + _stat(att, "strength") / 500.0
                   - _stat(de, "ground_control") / 320.0 - PHYS.size_matchup_modifier(de, att) * 0.30) * _gas_mod(gas)
            if pos == "back":
                acc -= 0.06
            elif pos == "mount":
                acc -= 0.06
        if action in ("mount_up", "take_back"):
            acc = (0.34 + _stat(att, "ground_control") / 280.0
                   - _stat(de, "grappling") / 340.0) * _gas_mod(gas)
        if action in ("jab", "cross", "hook", "uppercut", "head_kick", "liver",
                      "low_kick", "body_kick", "teep", "body_punch", "side_kick",
                      "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick",
                      "knee_body", "dirty_box", "gnp"):
            # Hands and kicks finally use their own technical attributes.
            acc += PHYS.action_skill(att, action) / 420.0
            if _knows(att, action.replace("_", " "), "kick" if "kick" in action else action):
                acc += 0.055
            acc += PHYS.technique_level_bonus(att, action, _TECH_BY_NAME)
        if action == "double_leg":
            ast.takedowns_attempted += 1
            acc = _takedown_accuracy(att, de, action, is_p, chained=chained)
        if action == "rear_naked":
            ast.submission_attempts += 1
            acc = 0.22 + _stat(att, "submissions") / 280.0
            if _action_known(att, action):
                acc += 0.08
            else:
                acc -= 0.06
            acc -= (_stat(de, "submission_def") - 40) / 600.0
            acc -= CI.submission_defense_bonus(de, att, intel[not is_p].get("prep", {}))

        if action not in ("jab", "cross", "hook", "uppercut", "head_kick", "liver",
                           "low_kick", "body_kick", "teep", "body_punch", "side_kick",
                           "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick",
                           "knee_body", "dirty_box", "gnp"):
            acc += PHYS.technique_level_bonus(att, action, _TECH_BY_NAME)
        acc += PERKS.accuracy_bonus(att, action, period)
        acc_final = max(0.10, min(0.84, acc))
        hit_roll = random.random()
        result = "land" if hit_roll < acc_final else "miss"
        if result == "miss" and pos == "stand" and action in STANDING_STRIKES:
            dplan = getattr(de, "_fight_plan", None) or {}
            if action in ("spin_back_kick", "spin_hook_kick", "tornado_kick"):
                counter_ready[not is_p] = True
                _move_range_toward("boxing")
            counter_chance = 0.10 + _stat(de, "striking_def") / 500.0
            if str(dplan.get("defense") or "").lower() == "counter":
                counter_chance += 0.16
            if random.random() < min(0.48, counter_chance):
                counter_ready[not is_p] = True
        used[is_p][action] = used[is_p].get(action, 0) + 1
        seq = last_acts[is_p]
        seq.append(action)
        del seq[:-6]
        if result == "land":
            mom += 1 if is_p else -1
        else:
            mom += -1 if is_p else 1
        dmg = 0
        if result == "land":
            landed_count[is_p][action] = landed_count[is_p].get(action, 0) + 1
            # Preserve the historical integer damage baseline, then let
            # division/mass nudge it probabilistically.  Multiplying before
            # int() created harsh thresholds where a tiny heavyweight bonus
            # could literally double low-damage strikes.
            raw_dmg = intended * (0.7 + _stat(att, "ko_power") / 250.0) * _gas_mod(gas)
            dmg = max(0, int(raw_dmg))
            impact = PHYS.impact_multiplier(att)
            if impact > 1.0 and random.random() < min(0.22, (impact - 1.0) * 1.4):
                dmg += 1
            elif impact < 1.0 and dmg > 0 and random.random() < min(0.15, (1.0 - impact) * 1.2):
                dmg -= 1
            if action == "gnp":
                # Punches from mount land far heavier than punches from inside
                # a closed guard.
                dmg = max(1, int(dmg * P.GNP_POWER.get(pos, 1.0)))
            if action in ("double_leg", "single_leg", "trip", "throw"):
                ast.takedowns_landed += 1
                pos, _swap = P.apply_transition(pos, action)
                # A clean shot can land past guard (ADCC 4, not 2).
                if grappling_only and pos not in SC.PAST_GUARD:
                    if random.random() < 0.22 + _stat(att, "grappling") / 400.0:
                        pos = "side"
                top_is_player = is_p
                control += 2 if is_p else -2
                dmg = 1
                if sport == "grappling":
                    key = "clean_takedown" if pos in SC.PAST_GUARD else "takedown"
                    _award_sport_points(ast, SC.ADCC_POINTS.get(key, 2))
                elif sport == "wrestling":
                    # Freestyle: ordinary takedowns score 2; amplitude throws score more.
                    pts = 4 if action == "throw" else 2
                    if action == "throw" and _stat(att,"strength") + _stat(att,"grappling") > _stat(de,"strength") + _stat(de,"takedown_def") + 35:
                        pts = 5
                    _award_sport_points(ast, pts)
                elif sport == "judo":
                    # Model non-ippon scoring as one waza-ari unit; two end the match.
                    ippon_ch = .14 + (_stat(att,"grappling")-_stat(de,"takedown_def"))/360.0
                    if action == "throw": ippon_ch += .11
                    if _action_known(att, action): ippon_ch += .05
                    if random.random() < max(.08,min(.48,ippon_ch)):
                        finish = "Ippon" if is_p else "Ippon Loss"; technique=action
                        winner="player" if is_p else "opponent"; method="Ippon (Throw)"
                        return True
                    _award_sport_points(ast, 1)
                elif sport == "combat_sambo":
                    pts = 4 if action == "throw" else 2
                    _award_sport_points(ast, pts)
                elif not grappling_only:
                    # MMA keeps positional points only as analytics, not the official score.
                    key = "clean_takedown" if pos in SC.PAST_GUARD else "takedown"
                    ast.grappling_points += SC.ADCC_POINTS.get(key, 2)
                if _technical_finish(is_p):
                    return True
            elif action in ("guard_pass", "mount_up", "take_back", "snap_down", "leg_entry", "north_south_move"):
                ast.control_ticks += 1
                control += 1 if is_p else -1
                pos, _swap = P.apply_transition(pos, action)
                top_is_player = is_p
                # Positional points are ruleset-specific, not universal ADCC scoring.
                if action == "guard_pass":
                    ast.passes += 1
                    if sport == "grappling": _award_sport_points(ast, SC.ADCC_POINTS["guard_pass"])
                    elif sport == "mma": ast.grappling_points += SC.ADCC_POINTS["guard_pass"]
                elif action == "mount_up":
                    ast.mount_ups += 1
                    if sport == "grappling": _award_sport_points(ast, SC.ADCC_POINTS["mount"])
                    elif sport == "mma": ast.grappling_points += SC.ADCC_POINTS["mount"]
                elif action == "take_back":
                    ast.back_takes += 1
                    if sport == "grappling": _award_sport_points(ast, SC.ADCC_POINTS["back_control"])
                    elif sport == "wrestling": _award_sport_points(ast, 2)
                    elif sport == "mma": ast.grappling_points += SC.ADCC_POINTS["back_control"]
                    pending_sig = True
                if _technical_finish(is_p): return True
            elif action == "ride":
                ast.control_ticks += 1
                control += 1 if is_p else -1
                dmg = 0
            elif action == "scramble":
                old_pos = pos
                new_pos, outcome = CI.scramble_outcome(
                    att, de, old_pos, attacker_gas=gas,
                    defender_gas=(o_gas if is_p else f_gas))
                pos = new_pos
                if outcome == "stand":
                    top_is_player, control = None, 0
                    ev_note = "SCRAMBLE to the feet"
                elif outcome == "attacker_top":
                    top_is_player = is_p
                    control += 1 if is_p else -1
                    ev_note = "SCRAMBLE — %s comes up on top" % name
                else:
                    top_is_player = not is_p
                    control += -1 if is_p else 1
                    ev_note = "SCRAMBLE — countered into %s" % pos
                ast.escapes += 1
                dmg = 1
                notes.append(ev_note)
            elif action == "sweep":
                # A reversal: the bottom fighter comes up on top.
                pos, swapped = P.apply_transition(pos, action)
                if grappling_only and pos not in SC.PAST_GUARD:
                    if random.random() < 0.18 + _stat(att, "grappling") / 450.0:
                        pos = "side"
                if swapped:
                    top_is_player = is_p
                control += 1 if is_p else -1
                ast.sweeps += 1
                if sport == "grappling":
                    key = "clean_sweep" if pos in SC.PAST_GUARD else "sweep"
                    _award_sport_points(ast, SC.ADCC_POINTS.get(key, 2))
                elif sport == "wrestling":
                    _award_sport_points(ast, 2)
                elif sport == "mma":
                    key = "clean_sweep" if pos in SC.PAST_GUARD else "sweep"
                    ast.grappling_points += SC.ADCC_POINTS.get(key, 2)
                if _technical_finish(is_p): return True
                dmg = 1
            elif action == "escape":
                ast.escapes += 1
                if sport == "mma": ast.grappling_points += 1
                pos, _swap = P.apply_transition(pos, action)
                if pos in P.NEUTRAL:
                    top_is_player, control = None, 0
                else:
                    # Escaped to a less-bad position, but still underneath.
                    top_is_player = not is_p
                    control = int(control * 0.5)
                dmg = 0
            elif action in ("stand_up", "break", "sprawl"):
                if sport == "grappling" and action == "stand_up" and P.is_control(pos) and role_of(is_p) == "top":
                    pen = int(SC.ADCC_PENALTIES.get("flee_position", -1))
                    ast.grappling_points += pen; ast.technical_points += pen
                    notes.append("flee position −1")
                pos, control, top_is_player = "stand", 0, None
                range_band = "boxing"
            elif action == "clinch_entry":
                pos, top_is_player, control = "clinch", None, 0
            if P.is_control(pos) and top_is_player is not None and is_p == top_is_player:
                ast.control_ticks += 1
            _count_strike(ast, action, target, "land", ground=(pos not in ("stand", "clinch") or grappling_only))
        else:
            stuffed[is_p][action] = stuffed[is_p].get(action, 0) + 1
            _count_strike(ast, action, target, "miss", ground=(pos not in ("stand", "clinch")))
            if P.is_control(pos) and top_is_player is not None and is_p == top_is_player:
                ast.control_ticks += 1
            # Takedown defence creates consequences. A clean sprawl can
            # create front-headlock control; a skilled chain wrestler can
            # connect the failed shot to a secondary attack.
            if action in ("double_leg", "single_leg") and pos in ("stand", "clinch"):
                def_edge = (_stat(de, "takedown_def") + _stat(de, "grappling") * .25
                            - _stat(att, "grappling") - _stat(att, "fight_iq") * .15)
                sprawl_ch = max(.04, min(.38, .10 + def_edge / 260.0
                                        + CI.takedown_defense_bonus(de, att, action, intel[not is_p].get("prep", {}))))
                if random.random() < sprawl_ch:
                    pos, top_is_player, control = "front_headlock", (not is_p), (-1 if is_p else 1)
                    notes.append("sprawl to front headlock")
                    if show or compact:
                        try:
                            console.print("  SPRAWL — front headlock control.")
                        except Exception:
                            pass
                elif not chained:
                    # Turn a stuffed shot into an actual second takedown
                    # attempt from clinch contact. Previous builds often
                    # stopped at a generic clinch entry, which looked like a
                    # chain in commentary but did not create a second finish.
                    nxt = CI.chain_takedown_followup(
                        att, de, action, gas=gas,
                        plan=dict(getattr(att, "_fight_plan", None) or {}))
                    if nxt:
                        try:
                            CI.observe(intel[is_p], self_action=True, action=action, result=result, damage=0, target=target or "")
                            CI.observe(intel[not is_p], self_action=False, action=action, result=result, damage=0, target=target or "")
                        except Exception:
                            pass
                        pos, top_is_player, control = "clinch", None, 0
                        legal_chain = P.legal_actions("clinch", grappling_only, None)
                        if nxt not in legal_chain or not rules.allows_action(nxt):
                            nxt = "trip" if "trip" in legal_chain and rules.allows_action("trip") else None
                        if nxt:
                            notes.append("chain %s off %s" % (nxt, action))
                            if show or compact:
                                try:
                                    console.print("  CHAIN — %s into %s." % (action.replace("_", " "), nxt.replace("_", " ")))
                                except Exception:
                                    pass
                            return resolve_action(is_p, nxt, "", max(1, intended), chained=True)
        kick_checked = False
        if result == "land" and action == "low_kick":
            # A real check reduces the damage that gets through and transfers
            # a small shin tax to the kicker. Predictable repeated low kicks
            # become easier to read.
            check_ch = max(0.08, min(0.58, 0.12 + _stat(de,"striking_def")/430.0 + _stat(de,"fight_iq")/950.0 + min(0.14, used[is_p].get(action,0)*0.022)))
            if random.random() < check_ch:
                kick_checked = True
                dmg = max(0, int(round(dmg * 0.28)))
                try:
                    (o_body if is_p else f_body).check_kick(f_body if is_p else o_body)
                except Exception:
                    pass
        if result == "land" and dmg:
            victim = opponent if is_p else fighter
            _hurt_part(victim, target or _target_for(action), dmg, action)
            # --- body map: each location feeds a different system ---------
            vmap = o_body if is_p else f_body
            amap = f_body if is_p else o_body
            loc = vmap.hit(action, dmg, target or "")
            if loc == "body":
                # Body work is a gas tax, which is how it ends fights late.
                bleed = 3 + vmap.gas_drain() // 6
                if is_p:
                    o_gas = max(0, o_gas - bleed)
                else:
                    f_gas = max(0, f_gas - bleed)
            if loc in ("lead_leg", "rear_leg") and kick_checked:
                if (show or compact) and hasattr(console, "feed"):
                    try:
                        console.feed("%s checks it — most of the kick dies on the shin."
                                     % (short_o if is_p else short_f), mine=not is_p)
                    except Exception:
                        pass
            if action in ("teep", "side_kick") and result == "land":
                # Long weapons manage distance instead of only dealing damage.
                _move_range_toward("outside")
            # A caught body kick creates a brief counter window in MMA/kickboxing.
            if action == "body_kick" and sport in ("mma", "kickboxing", "combat_sambo"):
                catch_ch=max(0.03,min(0.24,(_stat(de,"striking_def")+_stat(de,"fight_iq")-90)/500.0))
                if random.random() < catch_ch:
                    counter_ready[not is_p]=True
                    range_band="pocket"
                    notes.append("kick caught")
            # Cuts are a separate layer. Smart AI can work an existing cut;
            # ordinary sharp head strikes can still open a fresh one.
            targeted_cut = str(target or "").startswith("cut:")
            if loc == "head" and targeted_cut:
                zone = str(target).split(":", 1)[1]
                if zone in vmap.cuts and random.random() < min(0.55, 0.38 * PERKS.cut_chance_multiplier(att)):
                    before = int(vmap.cuts.get(zone, 0) or 0)
                    after = vmap.worsen_cut(zone, action, dmg)
                    if (show or compact) and after > before:
                        try:
                            console.feed("%s keeps touching the cut over the %s."
                                         % (short_f if is_p else short_o, zone),
                                         mine=is_p, tag="CUT")
                        except Exception:
                            pass
            elif loc == "head" and dmg >= 3 and action in (
                    "elbow", "head_kick", "cross", "hook", "uppercut", "gnp"):
                if random.random() < min(0.30, (0.16 if action == "elbow" else 0.07) * PERKS.cut_chance_multiplier(att)):
                    zone = vmap.open_cut(action)
                    if show or compact:
                        try:
                            console.feed("%s is opened up — cut over the %s."
                                         % (short_o if is_p else short_f, zone),
                                         mine=is_p, tag="CUT")
                        except Exception:
                            pass
        if is_p:
            o_dmg += dmg
        else:
            f_dmg += dmg
        try:
            CI.observe(intel[is_p], self_action=True, action=action, result=result, damage=dmg, target=target or "")
            CI.observe(intel[not is_p], self_action=False, action=action, result=result, damage=dmg, target=target or "")
        except Exception:
            pass
        drain(is_p, 2 if action in (
            "head_kick", "spin_back_kick", "axe_kick", "double_leg", "rear_naked", "armbar", "triangle", "kimura", "guillotine",
        ) else (3 if action in ("spin_hook_kick", "tornado_kick") else 1))
        ev = LogEvent(name, result, action, _line(name, action, result, dmg, target))
        log.append(ev)
        try:
            from .. import telemetry
            telemetry.combat(
                round=int(period), elapsed=int(elapsed), clock=_clock(max(0, period_len - elapsed)),
                actor="player" if is_p else "opponent", actor_name=name,
                requested_action=requested_action, requested_target=requested_target,
                action=action, target=target, legal_fallback=(requested_action != action),
                position_before=pre_pos, position_after=pos, role=my_role,
                range_before=pre_range, range_after=range_band,
                result=result, intended=int(intended or 0), damage=int(dmg or 0),
                hit_chance=round(float(acc_final), 4), hit_roll=round(float(hit_roll), 4),
                gas_before=int(pre_f_gas if is_p else pre_o_gas),
                gas_after=int(f_gas if is_p else o_gas),
                opponent_gas=int(o_gas if is_p else f_gas),
                momentum=int(mom), control=int(control),
                defender_body={
                    "head": round(float((o_body if is_p else f_body).loc.get("head", 0)), 1),
                    "body": round(float((o_body if is_p else f_body).loc.get("body", 0)), 1),
                    "lead_leg": round(float((o_body if is_p else f_body).loc.get("lead_leg", 0)), 1),
                    "rear_leg": round(float((o_body if is_p else f_body).loc.get("rear_leg", 0)), 1),
                    "cuts": dict((o_body if is_p else f_body).cuts),
                })
        except Exception:
            pass
        last_act[is_p] = action
        if is_p:
            last_p = action
        notable = result == "land" or action in (
            "rear_naked", "double_leg", "single_leg", "head_kick", "armbar",
            "triangle", "kimura", "guillotine", "scramble", "sweep", "throw",
        )
        if (show or compact) and notable:
            try:
                # Swap the long name for a short label and route through the
                # feed so each line is prefixed and coloured by who acted.
                txt = str(ev.text or "")
                txt = txt.replace(fname, short_f).replace(oname, short_o)
                # Suppress an identical line repeating back to back — the old
                # feed printed "sneaks an uppercut up the middle" three times
                # in a row.
                if txt in _recent_lines[-2:]:
                    txt = ""
                if txt:
                    _recent_lines.append(txt)
                    del _recent_lines[:-4]
                    tag = ""
                    if action in ("double_leg", "single_leg", "trip", "throw") and result == "land":
                        tag = "TD"
                    elif action in P.SUBMISSIONS:
                        tag = "SUB"
                    if hasattr(console, "feed"):
                        console.feed(txt, mine=is_p, tag=tag)
                    else:
                        console.print(txt)
                    if compact:
                        console.pause(0.12)
            except Exception:
                pass
        if result == "land" and action in P.SUBMISSIONS:
            return try_sub(is_p, action)
        if result == "land" and action in ("jab", "cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "liver") and dmg >= 2:
            ko = _stat(att, "ko_power")
            dur = _stat(de, "durability")
            kd_ch = P.KO_BASE.get(action, 0.04) + max(0, dmg - 3) * 0.04 + (ko - dur) / 400.0
            if random.random() < max(0.02, min(0.28, kd_ch)):
                ast.knockdowns += 1
                (os_ if is_p else fs).times_down += 1
                ev.text = (ev.text or "") + "  DOWN."
                if show or compact:
                    try:
                        if hasattr(console, "feed"):
                            console.feed("%s has him hurt — DOWN." % (
                                short_f if is_p else short_o), mine=is_p, tag="KD")
                        else:
                            console.print("  Knockdown.")
                    except Exception:
                        pass
                notes.append("KD %s" % name)
                pending_sig = True
                dmg = max(dmg, dmg + 2)
        if result == "land" and sport == "taekwondo":
            # WT scoring values: punch to trunk 1, kick to trunk 2, turning
            # trunk 4, head 3, turning head 5.
            tkd_pts = {
                "body_punch": 1, "teep": 2, "body_kick": 2, "side_kick": 2,
                "spin_back_kick": 4, "head_kick": 3, "axe_kick": 3,
                "spin_hook_kick": 5, "tornado_kick": 5,
            }.get(action, 0)
            if tkd_pts:
                _award_sport_points(ast, tkd_pts)
                if action in ("spin_back_kick", "spin_hook_kick", "tornado_kick"):
                    ast.turning_points += tkd_pts
        if result == "land" and sport == "combat_sambo" and action in STANDING_STRIKES:
            # FIAS scores effective attacks, not every touch. Reward clear effect.
            if dmg >= 4:
                _award_sport_points(ast, 2)
            elif dmg >= 2:
                _award_sport_points(ast, 1)
            if ast.knockdowns > pre_knockdowns:
                # Knockdown itself is a major scored action and two end the bout.
                ast.technical_points += 2
                ast.grappling_points += 2
            if _technical_finish(is_p):
                return True
        if result == "land":
            vmap = o_body if is_p else f_body
            # Short label — the full name overflows a phone line.
            vname = short_o if is_p else short_f
            # --- body shot knockout -----------------------------------------
            # A liver shot does not knock you senseless, it folds you. This is
            # its own finish, gated on accumulated body damage rather than a
            # head-KO roll.
            if action in ("liver", "knee_body", "body_kick") and dmg >= 2:
                body_dmg = vmap.loc["body"]
                ch = max(0.0, (body_dmg - 45) / 260.0) + (0.05 if action == "liver" else 0.02)
                if sport == "taekwondo":
                    ch *= 0.08
                if body_dmg >= 55 and random.random() < min(0.30, ch):
                    finish = "KO" if is_p else "KO Loss"
                    technique = action
                    winner, method = ("player" if is_p else "opponent"), "KO (body)"
                    if show or compact:
                        try:
                            console.feed("%s folds — BODY SHOT. It is over."
                                         % vname, mine=is_p, tag="KO")
                        except Exception:
                            pass
                    return True
            # --- leg TKO ------------------------------------------------------
            if vmap.leg_tko():
                finish = "TKO" if is_p else "TKO Loss"
                technique = "leg kicks"
                winner, method = ("player" if is_p else "opponent"), "TKO (leg)"
                if show or compact:
                    try:
                        console.feed("The leg gives out. %s cannot stand on it."
                                     % vname, mine=is_p, tag="TKO")
                    except Exception:
                        pass
                return True
            # --- cut stoppage -------------------------------------------------
            if vmap.cut_stoppage():
                zone, _sev = vmap.worst_cut()
                finish = "TKO" if is_p else "TKO Loss"
                technique = "cut"
                winner, method = ("player" if is_p else "opponent"), "TKO (doctor)"
                if show or compact:
                    try:
                        console.feed("Doctor waves it off — the %s is too deep."
                                     % zone, mine=is_p, tag="DOC")
                    except Exception:
                        pass
                return True
            return try_ko(is_p, action, dmg)
        return False

    _BASE_DMG = {
        "jab": 1, "cross": 2, "hook": 2, "uppercut": 3, "low_kick": 2,
        "liver": 3, "body_kick": 3, "teep": 1, "head_kick": 4,
        "body_punch": 1, "side_kick": 2, "spin_back_kick": 4, "spin_hook_kick": 4,
        "axe_kick": 3, "tornado_kick": 4, "double_leg": 2, "single_leg": 2,
        "trip": 2, "throw": 2, "dirty_box": 2, "knee_body": 3, "gnp": 2,
        "guard_pass": 1, "sweep": 1, "scramble": 1, "escape": 0, "stand_up": 0, "break": 0,
        "sprawl": 0, "clinch_entry": 1, "mount_up": 1, "take_back": 1,
        "snap_down": 1, "leg_entry": 1, "north_south_move": 1, "ride": 0,
        "heel_hook": 4, "kneebar": 4, "north_south_choke": 4,
    }

    def _target_for(action):
        if action in ("low_kick",):
            return "leg"
        if action in ("liver", "body_kick", "teep", "knee_body", "body_punch", "side_kick", "spin_back_kick"):
            return "body"
        if action in ("jab", "cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "gnp", "dirty_box"):
            return "head"
        return ""

    def _ai_pick(is_p, plan_name):
        """Choose an action for one fighter.

        Everything comes out of positions.legal_actions() for that fighter's
        role, so the AI can never pick an illegal move. On top of that it
        weights by archetype (a wrestler shoots, a boxer stays standing, a BJJ
        player hunts submissions from guard) and *adapts*: a move that has been
        stuffed twice gets heavily downweighted.
        """
        who = fighter if is_p else opponent
        my_role = role_of(is_p)
        legal = {a for a in P.legal_actions(pos, grappling_only, my_role)
                 if rules.allows_action(a)}
        if not legal:
            return ("sprawl", "", 0)
        sigs = _signature_acts(who, pos, my_role, legal)
        if sigs:
            sigs = sorted(sigs, key=lambda a: CI.action_multiplier(
                intel[is_p], a, gas=(f_gas if is_p else o_gas),
                opponent_gas=(o_gas if is_p else f_gas),
                my_damage=_ci_damage(f_body if is_p else o_body),
                opponent_damage=_ci_damage(o_body if is_p else f_body),
                round_no=period, total_rounds=periods, score_margin=_score_margin(is_p)),
                reverse=True)
            sig_mult = CI.action_multiplier(
                intel[is_p], sigs[0], gas=(f_gas if is_p else o_gas),
                opponent_gas=(o_gas if is_p else f_gas),
                my_damage=_ci_damage(f_body if is_p else o_body),
                opponent_damage=_ci_damage(o_body if is_p else f_body),
                round_no=period, total_rounds=periods, score_margin=_score_margin(is_p))
        else:
            sig_mult = 0.0
        if sigs and sig_mult >= 0.58 and random.random() < (0.22 + _stat(who, "fight_iq") / 400.0) * min(1.15, sig_mult):
            pick = sigs[0]
            prey_map = o_body if is_p else f_body
            target = _damage_target_hint(pick, prey_map, _stat(who, "fight_iq"))
            if not target and pick in ("head_kick", "liver"):
                target = _target_for(pick)
            try:
                from .. import telemetry
                telemetry.decision("ai_pick", choice=pick, target=target, reason="signature",
                                   actor="player" if is_p else "opponent", actor_name=getattr(who, "name", ""),
                                   position=pos, role=my_role, gas=int(f_gas if is_p else o_gas),
                                   legal=sorted(legal))
            except Exception:
                pass
            return (pick, target,
                    4 if pick in ("rear_naked", "head_kick", "liver") else 3)
        arch = str(getattr(who, "archetype", "") or getattr(who, "style", "") or "").lower()
        wrestler = any(w in arch for w in ("wrestl", "sambo", "judo"))
        grappler = any(w in arch for w in ("bjj", "jiu", "submission", "grappl"))
        striker = any(w in arch for w in ("box", "muay", "kick", "karate", "taekwondo"))
        boxer = "box" in arch
        brawler = any(w in arch for w in ("pressure", "brawler", "berserk", "slugger"))
        plan = (getattr(fighter, "_fight_plan", None) or {}) if is_p else (
            getattr(opponent, "_fight_plan", None) or {})
        plan_name = str(plan.get("name") or (plan_name if is_p else "Balanced") or "Balanced")

        weights = {}
        # Stable order matters: otherwise Python's randomized set hash changes
        # seeded simulations (and balance results) between processes.
        for act in sorted(legal):
            w = 1.0
            # --- position intent -------------------------------------------
            if act in P.SUBMISSIONS:
                w = 2.6 if grappler else (1.4 if wrestler else 0.9)
            elif act == "gnp":
                w = 1.8 if (wrestler or brawler) else 1.3
            elif act == "guard_pass":
                w = 1.6 if (wrestler or grappler) else 1.1
            elif act in ("mount_up", "take_back"):
                w = 1.7 if (wrestler or grappler) else 1.2
            elif act == "escape":
                # Getting out from under is urgent, more so if being hurt.
                w = (3.0 if striker else 2.2) if pos in ("mount", "back", "side") else (1.9 if striker else 1.4)
            elif act == "scramble":
                w = 2.1 if (wrestler or striker) else 1.6
            elif act == "sweep":
                w = 1.8 if grappler else 1.2
            elif act == "stand_up":
                # A striker desperately wants back to the feet; a grappler does not.
                w = 0.4 if grappling_only else (3.0 if striker else 0.7)
            elif act in ("double_leg", "single_leg", "trip", "throw"):
                w = 2.2 if wrestler else (1.3 if grappler else 0.35 if boxer else 0.6)
            elif act == "clinch_entry":
                w = 1.6 if (wrestler or "muay" in arch) else 0.8
            elif act in ("jab", "cross", "hook", "uppercut"):
                w = 2.4 if boxer else (1.8 if striker else 1.0)
                if brawler and act in ("hook", "uppercut"):
                    w = 2.2
            elif act in ("low_kick", "head_kick", "body_kick", "teep", "side_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
                w = 2.15 if "taekwondo" in arch else (1.9 if ("muay" in arch or "kick" in arch or "karate" in arch) else (0.45 if boxer else 0.8))
            elif act == "liver":
                w = 1.5 if "muay" in arch else (1.35 if boxer else 0.9)
            elif act == "break":
                w = 1.8 if boxer else (1.4 if striker else 0.5)
            elif act == "sprawl":
                w = 1.5 if striker and not wrestler else 0.7

            if pos == "stand":
                w *= _range_weight(act, range_band)

            # --- proficiency ------------------------------------------------
            # Legal does not mean proficient.  Fighters may improvise, but a
            # move they have actually learned should be selected and executed
            # much more often than an advanced move they have never trained.
            if act in P.SUBMISSIONS and not _action_known(who, act):
                w *= 0.45
            elif act in ("spin_back_kick", "spin_hook_kick", "tornado_kick") and not _action_known(who, act):
                # Advanced turning attacks are learned tools, not generic kicks.
                # Keeping a tiny fallback allows improvisation without letting
                # every kickboxer spam high-damage Taekwondo techniques.
                w *= 0.14
            elif act in ("side_kick", "axe_kick") and not _action_known(who, act):
                w *= 0.28
            elif act in ("head_kick", "body_kick", "throw", "trip", "dirty_box", "knee_body") and not _action_known(who, act):
                w *= 0.55

            # --- gameplan: each fighter obeys THEIR OWN plan ---------------
            if plan:
                if plan_name == "Wrestle-heavy":
                    if act in ("double_leg","single_leg","trip","throw","guard_pass","mount_up","take_back","ride"): w *= 2.45
                    if act in ("hook","uppercut","head_kick"): w *= .72
                elif plan_name == "Pressure":
                    if act in ("cross","hook","uppercut","low_kick","clinch_entry","dirty_box","gnp"): w *= 1.90
                    if act in ("break","stand_up"): w *= .72
                elif plan_name == "Counter":
                    if act in ("jab","teep","sprawl","break"): w *= 1.70
                    if counter_ready[is_p] and act in ("cross","hook","uppercut","liver"): w *= 2.25
                    if act in ("double_leg","throw"): w *= .72
                elif plan_name == "Kickboxing Outside":
                    if act in ("jab","teep","low_kick","body_kick","head_kick"): w *= 2.10
                    if act in ("double_leg","single_leg","clinch_entry"): w *= .50
                elif plan_name == "Submission Hunter":
                    if act in P.SUBMISSIONS: w *= 2.55
                    if act in ("double_leg","single_leg","trip","guard_pass","take_back","sweep"): w *= 1.85
                    if act == "gnp": w *= .70
                elif plan_name == "Clinch & Control":
                    if act in ("clinch_entry","trip","throw","dirty_box","knee_body","ride","guard_pass","take_back"): w *= 2.20
                    if act in ("head_kick","break"): w *= .65
                elif plan_name in ("Taekwondo Range", "Taekwondo Kicking"):
                    if act in ("teep","side_kick","body_kick","head_kick","axe_kick"): w *= 2.35
                    if act in ("spin_back_kick","spin_hook_kick","tornado_kick"): w *= 1.65
                    if act == "body_punch": w *= 1.15
                # Fine controls layer on top of the template.
                if plan.get("target") == "body" and act in ("liver", "body_kick", "side_kick", "spin_back_kick", "body_punch", "knee_body", "teep"): w *= 1.85
                if plan.get("target") == "legs" and act == "low_kick": w *= 2.0
                if plan.get("target") == "head" and act in ("cross", "hook", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "uppercut"): w *= 1.55
                if plan.get("td") == "Aggressive" and act in ("double_leg", "single_leg", "trip", "throw"): w *= 2.0
                if plan.get("td") == "Safe" and act in ("double_leg", "single_leg", "trip", "throw"): w *= .42
                if plan.get("pace") == "high":
                    if act not in ("break","stand_up"): w *= 1.20
                elif plan.get("pace") == "low" and act in ("jab", "teep", "break", "sprawl"): w *= 1.45
                wanted = str(plan.get("range") or "").lower()
                if wanted in RANGE_BANDS and RANGE_IDEAL.get(act) == wanted: w *= 1.65
                defense = str(plan.get("defense") or "").lower()
                if defense == "counter" and counter_ready[is_p] and act in ("cross", "hook", "uppercut", "liver"): w *= 1.75
            # Tactical adaptation reacts to what the opponent actually did, not
            # magically to the player's menu label.
            theirs = last_acts.get(not is_p) or []
            shots = sum(1 for a in theirs[-4:] if a in ("double_leg", "single_leg", "trip", "throw"))
            jabs = sum(1 for a in theirs[-4:] if a in ("jab", "teep"))
            if shots >= 2 and act in ("sprawl", "guillotine", "stand_up"): w *= 1.75
            if jabs >= 2 and act in ("double_leg", "clinch_entry"): w *= 1.30
            if period == 1 and act in ("hook", "head_kick", "double_leg", "throw"):
                w *= 0.72
            if period == 1 and act in ("jab", "teep", "low_kick"):
                w *= 1.28
            if period >= periods and judges and judges[0].rounds:
                ta, tb = judges[0].totals
                mine, theirs = (ta, tb) if is_p else (tb, ta)
                if mine < theirs and act in ("hook", "head_kick", "rear_naked", "gnp", "armbar", "cross"):
                    w *= 1.55

            # --- adaptation: stop feeding a move that keeps getting stuffed ---
            miss = stuffed[is_p].get(act, 0)
            hit = landed_count[is_p].get(act, 0)
            iq = _stat(who, "fight_iq")
            if miss >= 2 and miss > hit:
                w *= 0.22 if iq >= 70 else 0.35
            if miss >= 4 and miss > hit:
                w *= 0.3 if iq >= 70 else 0.4
            hx = _hurt(who)
            if hx["legs"] >= 8 and act in ("low_kick", "head_kick", "teep", "double_leg"):
                w *= 0.45
            if hx["body"] >= 8 and act in ("hook", "head_kick", "double_leg"):
                w *= 0.6
            prey = opponent if is_p else fighter
            py = _hurt(prey)
            if py["legs"] >= 8 and act == "low_kick":
                # Between-fight leg damage/injury is visible in stance and
                # movement before the live BodyMap has accumulated anything.
                w *= 1.35 if iq < 65 else 1.65
            if py["legs"] >= 8 and act in ("double_leg", "single_leg", "trip"):
                w *= 1.4
            if py["body"] >= 8 and act in ("liver", "knee_body"):
                w *= 1.45
            if py["head"] >= 10 and act in ("cross", "hook", "gnp", "head_kick"):
                w *= 1.25
            if py["cuts"] >= 5 and act in ("jab", "cross", "hook", "elbow", "gnp"):
                w *= 1.15 if iq < 65 else 1.35
            # Read the damage created in THIS fight. Before 1.21 the AI only
            # saw the old between-fight summary, so it never noticed a leg,
            # body or cut it had just compromised.
            prey_map = o_body if is_p else f_body
            w *= _damage_hunt_weight(act, prey_map, _stat(who, "fight_iq"))
            w *= PERKS.action_weight_multiplier(who, act, period)
            # v1.39 tactical intelligence: live reads, score urgency, damage
            # preservation and opponent-specific preparation all bias only
            # LEGAL actions chosen by this engine.
            my_map = f_body if is_p else o_body
            op_map = o_body if is_p else f_body
            my_live = _ci_damage(my_map)
            op_live = _ci_damage(op_map)
            margin = _score_margin(is_p)
            w *= CI.action_multiplier(
                intel[is_p], act, gas=(f_gas if is_p else o_gas),
                opponent_gas=(o_gas if is_p else f_gas),
                my_damage=my_live, opponent_damage=op_live,
                round_no=period, total_rounds=periods, score_margin=margin)
            # Conversely, keep going back to what is working.
            if hit >= 2 and hit > miss:
                w *= 1.35
            # Do not spam one button.
            if used[is_p].get(act, 0) >= 4:
                w *= 0.7

            # A tired fighter reaches for cheap options.
            my_gas = f_gas if is_p else o_gas
            if my_gas <= 25 and act in ("head_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "double_leg", "single_leg", "throw"):
                w *= 0.5

            weights[act] = max(0.05, w)

        iq = _stat(who, "fight_iq")
        bag_p = 0.12 if iq >= 75 else (0.22 if iq >= 55 else 0.35)
        if random.random() < bag_p:
            bag = _auto_from_bag(who, pos, grappling_only, my_role)
            if bag and not rules.allows_action(bag[0]):
                bag = None
            if bag and stuffed[is_p].get(bag[0], 0) < 2:
                bag_mult = CI.action_multiplier(
                    intel[is_p], bag[0], gas=(f_gas if is_p else o_gas),
                    opponent_gas=(o_gas if is_p else f_gas),
                    my_damage=_ci_damage(f_body if is_p else o_body),
                    opponent_damage=_ci_damage(o_body if is_p else f_body),
                    round_no=period, total_rounds=periods, score_margin=_score_margin(is_p))
                if bag_mult < 0.62:
                    bag = None
            if bag and stuffed[is_p].get(bag[0], 0) < 2:
                try:
                    from .. import telemetry
                    telemetry.decision("ai_pick", choice=bag[0], target=bag[1], reason="technique_bag",
                                       actor="player" if is_p else "opponent", actor_name=getattr(who, "name", ""),
                                       position=pos, role=my_role, gas=int(f_gas if is_p else o_gas),
                                       legal=sorted(legal))
                except Exception:
                    pass
                return bag

        acts = list(weights)
        action = random.choices(acts, weights=[weights[a] for a in acts], k=1)[0]
        prey_map = o_body if is_p else f_body
        target = _damage_target_hint(action, prey_map, _stat(who, "fight_iq"))
        if not target:
            target = _target_for(action)
        try:
            from .. import telemetry
            ranked = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:6]
            telemetry.decision("ai_pick", choice=action, target=target, reason="weighted",
                               actor="player" if is_p else "opponent", actor_name=getattr(who, "name", ""),
                               position=pos, role=my_role, gas=int(f_gas if is_p else o_gas),
                               iq=int(_stat(who, "fight_iq")),
                               top_weights=[[a, round(float(w), 3)] for a, w in ranked])
        except Exception:
            pass
        return (action, target, _BASE_DMG.get(action, 2))

    def _bank_ride(is_top_player, hold):
        """Seconds on the mat become control; judo can end on a 20s hold-down."""
        nonlocal finish, technique, winner, method
        if hold <= 0:
            return
        ast = fs if is_top_player else os_
        ast.control_sec += hold
        ast.control_ticks += max(1, hold // 10)
        if sport == "judo" and pos in ("side","mount") and hold >= 20 and not finish:
            finish = "Ippon" if is_top_player else "Ippon Loss"
            technique = "osaekomi"; winner = "player" if is_top_player else "opponent"
            method = "Ippon (Hold-down)"

    def _ride_work(beats):
        """While the top man holds a position he works — GnP, pass, sub —
        and the bottom man answers with escapes, sweeps, or guard attacks.
        Each beat burns real seconds already banked on the ride clock."""
        if beats <= 0 or pos in P.NEUTRAL or top_is_player is None:
            return False
        for _ in range(beats):
            if finish or pos in P.NEUTRAL or top_is_player is None:
                return bool(finish)
            top_p = bool(top_is_player)
            t_act, t_tgt, t_dmg = _ai_pick(top_p, gameplan)
            if resolve_action(top_p, t_act, t_tgt, t_dmg):
                return True
            if pos in P.NEUTRAL or top_is_player is None:
                return False
            b_act, b_tgt, b_dmg = _ai_pick(not top_p, gameplan)
            if resolve_action(not top_p, b_act, b_tgt, b_dmg):
                return True
        return False

    end_elapsed = 0
    pending_sig = False
    for period in range(1, periods + 1):
        if finish:
            break
        moment_ticks = set()
        if moments_per:
            bag = list(range(2, max(3, ticks_n - 1)))
            random.shuffle(bag)
            moment_ticks = set(bag[:moments_per])
        elapsed = 0
        start_fsec, start_osec = fs.control_sec, os_.control_sec
        if show or compact:
            try:
                if hasattr(console, "fight_head"):
                    # Compact HUD: one header line plus a damage/gas bar each.
                    # The old banner burned four lines and repeated gas twice.
                    console.fight_head(
                        period, _clock(period_len), P.label(pos, role_of(True)) + (
                            " · " + range_band.upper() if pos == "stand" else ""),
                        short_f, short_o, f_dmg, o_dmg, f_gas, o_gas,
                        f_body, o_body)
                else:
                    console.header(
                        "ROUND %s  %s · %s" % (period, _clock(period_len),
                                               P.label(pos, role_of(True)) + (
                                                   " · " + range_band.upper() if pos == "stand" else "")),
                        "%s gas %s | %s gas %s" % (fname, f_gas, oname, o_gas),
                    )
            except Exception:
                pass
        start_fd, start_od = f_dmg, o_dmg
        start_fkd, start_okd = fs.knockdowns, os_.knockdowns
        start_fc, start_oc = fs.control_ticks, os_.control_ticks
        start_ftp, start_otp = fs.technical_points, os_.technical_points
        start_f_snap = fs.as_dict()
        start_o_snap = os_.as_dict()
        rd_f = rd_o = 0 if not judged_sport else 10
        for t in range(ticks_n):
            if finish:
                break
            _contest_range()
            if (t in moment_ticks or pending_sig) and (show or compact):
                pending_sig = False
                if show:
                    name, action, target, intended = _ask_tech(
                        console, fighter, period, pos, amateur, grappling_only, role_of(True), rules
                    )
                    if amateur:
                        intended = max(1, intended - 1)
                else:
                    action, target, intended = _ai_pick(True, gameplan)
                    try:
                        console.print("MOMENT  %s — you go for %s" % (
                            P.label(pos, role_of(True)), action.replace("_", " ")))
                    except Exception:
                        pass
                if resolve_action(True, action, target, intended):
                    end_elapsed = elapsed
                    break
                o_action, o_target, o_dmg_i = _ai_pick(False, gameplan)
                if resolve_action(False, o_action, o_target, o_dmg_i):
                    end_elapsed = elapsed
                    break
                continue
            pplan = getattr(fighter, "_fight_plan", None) or {}
            oplan = getattr(opponent, "_fight_plan", None) or {}
            pname = str(pplan.get("name", "Balanced") or "Balanced").lower()
            oname_plan = str(oplan.get("name", "Balanced") or "Balanced").lower()
            p_init = 0.50
            if pname in ("pressure", "wrestle-heavy", "clinch & control"): p_init += 0.08
            if pname == "counter": p_init -= 0.08
            if oname_plan in ("pressure", "wrestle-heavy", "clinch & control"): p_init -= 0.05
            if oname_plan == "counter": p_init += 0.03
            first_p = random.random() < max(0.35, min(0.65, p_init))
            for is_p in ([True, False] if first_p else [False, True]):
                action, target, dmg = _ai_pick(is_p, gameplan)
                if resolve_action(is_p, action, target, dmg):
                    break
            if finish:
                end_elapsed = elapsed
                break
            if f_cardio > 70 and t % 4 == 0:
                f_gas = min(100, f_gas + 1)
            if o_cardio > 70 and t % 4 == 0:
                o_gas = min(100, o_gas + 1)
            # Clock + ride. Ground control eats real seconds so a wrestler
            # can hold someone for a minute-plus inside a 3:00/5:00 round.
            # While the clock runs the top man works and the bottom man
            # answers — that is the hold, not empty time.
            slice_s = max(8, int(period_len / max(1, ticks_n)))
            if pos not in P.NEUTRAL and top_is_player is not None:
                top = fighter if top_is_player else opponent
                bot = opponent if top_is_player else fighter
                edge = (
                    _stat(top, "ground_control") + _stat(top, "strength") / 5.0
                    - _stat(bot, "grappling") - _stat(bot, "submissions") / 5.0
                )
                hold = int(slice_s * _HOLD.get(pos, 1.0) * (0.82 + max(-0.28, min(0.55, edge / 160.0))))
                cap = 36 if pos in ("mount", "back", "side") else 28
                hold = max(7, min(cap, hold))
                hold = min(hold, max(4, period_len - elapsed))
                _bank_ride(top_is_player, hold)
                elapsed += hold
                beats = 1 if hold >= 10 else 0
                if hold >= 22 and pos in ("mount", "back", "side"):
                    beats = 2
                if (show or compact) and hold >= 8:
                    try:
                        # Short label and two lines — this used the full
                        # opponent name and ran past the phone width.
                        who = short_f if top_is_player else short_o
                        flavor = _RIDE_FLAVOR.get(pos, "holding position")
                        console.print("  %s  %s %s" % (
                            _clock(max(0, period_len - elapsed)), who, flavor))
                        console.print("     ride +%s  ctrl %s-%s" % (
                            _clock(hold),
                            _clock(fs.control_sec), _clock(os_.control_sec)))
                    except Exception:
                        pass
                if _ride_work(beats):
                    end_elapsed = elapsed
                    break
                # Referee stand-up: stalling in closed guard with no work.
                if (not grappling_only and pos == "closed_guard"
                        and hold >= 16 and random.random() < 0.12):
                    pos, control, top_is_player = "stand", 0, None
                    if show or compact:
                        try:
                            console.print("  REF STANDS THEM UP.")
                        except Exception:
                            pass
            else:
                elapsed += slice_s
            if elapsed >= period_len:
                end_elapsed = period_len
                if show or compact:
                    try:
                        console.print("  HORN. End of round.")
                    except Exception:
                        pass
                break
            end_elapsed = elapsed
        f_gas = max(4, f_gas - f_body.gas_drain() // 6)
        o_gas = max(4, o_gas - o_body.gas_drain() // 6)
        f_body.between_rounds()
        o_body.between_rounds()
        if not finish:
            rd_od = o_dmg - start_od
            rd_fd = f_dmg - start_fd
            # A referee stoppage depends on the state of the man being HIT,
            # not on the order the engine happens to check things in.
            #
            # Two bugs lived here. The player's condition was tested first in
            # an if/elif chain, so whenever both men qualified in the same
            # round the player always won — worth roughly 2.3x the finishes in
            # a clone-vs-clone fight. And each branch read the wrong fighter's
            # gas: the player's stoppage of the opponent was gated on
            # `f_gas`, the player's own tank, rather than the opponent's.
            # Keyed off accumulated HEAD trauma now that a body map exists.
            # The old proxy (total damage + low gas) started firing on half of
            # all fights once body shots began draining gas properly.
            if sport == "taekwondo":
                p_stops = (o_body.loc["head"] >= 82 and rd_od >= 14)
                o_stops = (f_body.loc["head"] >= 82 and rd_fd >= 14)
            else:
                p_stops = (o_body.loc["head"] >= 68 and rd_od >= 10) or (
                    o_dmg >= 44 and o_gas <= 14 and rd_od >= 12)
                o_stops = (f_body.loc["head"] >= 68 and rd_fd >= 10) or (
                    f_dmg >= 44 and f_gas <= 14 and rd_fd >= 12)
            if p_stops and o_stops:
                # Both hurt badly enough. The one who took more this round
                # goes; a coin flip only if that is level too.
                if rd_fd != rd_od:
                    p_stops, o_stops = rd_od > rd_fd, rd_fd > rd_od
                elif f_dmg != o_dmg:
                    p_stops, o_stops = o_dmg > f_dmg, f_dmg > o_dmg
                else:
                    coin = random.random() < 0.5
                    p_stops, o_stops = coin, not coin
            if p_stops:
                finish, technique, winner, method = "TKO", "accumulation", "player", "TKO"
            elif o_stops:
                finish, technique, winner, method = "TKO Loss", "accumulation", "opponent", "TKO"
            else:
                # Per-period deltas only. Judge sports use 10-point must;
                # wrestling/judo/sambo/grappling show their own technical score.
                rd_f_stats = _RoundDelta(fs, start_f_snap)
                rd_o_stats = _RoundDelta(os_, start_o_snap)
                rd_ctrl_f = max(fs.control_ticks - start_fc, (fs.control_sec - start_fsec) // 8)
                rd_ctrl_o = max(os_.control_ticks - start_oc, (os_.control_sec - start_osec) // 8)
                if judged_sport:
                    for card in judges:
                        sa, sb = SC.score_round(
                            rd_f_stats, rd_o_stats, rd_od, rd_fd,
                            rd_ctrl_f, rd_ctrl_o, lean=card.lean)
                        card.add(sa, sb)
                    rd_f, rd_o = judges[0].rounds[-1]
                    f_pts += rd_f
                    o_pts += rd_o
                else:
                    rd_f = int(fs.technical_points - start_ftp)
                    rd_o = int(os_.technical_points - start_otp)
                    f_pts, o_pts = int(fs.technical_points), int(os_.technical_points)
                    if sport == "taekwondo":
                        # Best-of-three round system. Tied rounds prefer points
                        # from turning/spinning techniques, then head scoring.
                        f_turn = fs.turning_points - int(start_f_snap.get("turning_points", 0) or 0)
                        o_turn = os_.turning_points - int(start_o_snap.get("turning_points", 0) or 0)
                        if rd_f != rd_o:
                            rd_player = rd_f > rd_o
                        elif f_turn != o_turn:
                            rd_player = f_turn > o_turn
                        else:
                            fh = fs.head_landed - int(start_f_snap.get("head_landed",0) or 0)
                            oh = os_.head_landed - int(start_o_snap.get("head_landed",0) or 0)
                            rd_player = (fh > oh) if fh != oh else (random.random() < .5)
                        tkd_round_wins[rd_player] += 1
                        (fs if rd_player else os_).round_wins += 1
            if show or compact:
                try:
                    role = P.label(pos, role_of(True))
                    # Two short lines instead of one 60+ char line that wrapped
                    # badly on a phone.
                    if judged_sport:
                        console.info("Round %s   %s-%s   %s" % (period, rd_f, rd_o, role))
                    else:
                        console.info("Period %s   score %s-%s   %s" % (period, fs.technical_points, os_.technical_points, role))
                    console.print("   dmg %s-%s  ctrl %s-%s" % (
                        o_dmg - start_od, f_dmg - start_fd,
                        _clock(fs.control_sec - start_fsec),
                        _clock(os_.control_sec - start_osec)))
                    if compact:
                        console.pause(0.25)
                except Exception:
                    pass
            if not finish and period < periods:
                f_rec = int(round((8 + f_cardio // 20) / PHYS.gas_cost_multiplier(fighter))) + PERKS.round_recovery_bonus(fighter, period)
                o_rec = int(round((8 + o_cardio // 20) / PHYS.gas_cost_multiplier(opponent))) + PERKS.round_recovery_bonus(opponent, period)
                f_gas = min(100, f_gas + max(5, f_rec))
                o_gas = min(100, o_gas + max(5, o_rec))
                try:
                    f_live = _ci_damage(f_body)
                    o_live = _ci_damage(o_body)
                    oplan, _oreason = CI.between_round_adjustment(
                        opponent, fighter, intel[False], dict(getattr(opponent,"_fight_plan",None) or {}),
                        round_lost=(rd_o < rd_f), gas=o_gas, opponent_gas=f_gas,
                        score_margin=(o_pts-f_pts), my_damage=o_live, opponent_damage=f_live)
                    opponent._fight_plan = oplan
                    # In automatic modes the player's Fight IQ/adaptability
                    # makes bounded between-round adjustments too. Interactive
                    # play keeps the choice with the player/corner below.
                    if not show:
                        pplan, _preason = CI.between_round_adjustment(
                            fighter, opponent, intel[True], dict(getattr(fighter,"_fight_plan",None) or {}),
                            round_lost=(rd_f < rd_o), gas=f_gas, opponent_gas=o_gas,
                            score_margin=(f_pts-o_pts), my_damage=f_live, opponent_damage=o_live)
                        fighter._fight_plan = pplan
                except Exception:
                    pass
            if not finish and period < periods and (show or compact):
                won_rd = rd_f > rd_o
                try:
                    f_live = _ci_damage(f_body)
                    o_live = _ci_damage(o_body)
                    _tip_state = dict(intel[True])
                    _tip_state["adjustments"] = list(intel[True].get("adjustments", []))
                    _suggest, tip = CI.between_round_adjustment(
                        fighter, opponent, _tip_state, dict(getattr(fighter,"_fight_plan",None) or {}),
                        round_lost=(rd_f < rd_o), gas=f_gas, opponent_gas=o_gas,
                        score_margin=(f_pts-o_pts), my_damage=f_live, opponent_damage=o_live)
                except Exception:
                    if rd_ctrl_f > rd_ctrl_o + 1:
                        tip = "He is losing the floor. Keep the hips heavy."
                    elif rd_od >= rd_fd + 4:
                        tip = "Your shots are landing. Do not get greedy."
                    elif f_gas < 40:
                        tip = "Breathe. Walk him down, do not sprint."
                    elif won_rd:
                        tip = "You stole that one. Stay disciplined."
                    else:
                        tip = "You are behind. Force a moment next round."
                try:
                    console.print("CORNER  gas %s/%s" % (f_gas, o_gas))
                    for _ln in wrap_text(str(tip), max(20, console.width - 2)):
                        console.print("  " + _ln)
                    if show:
                        console.print("  A) Press  B) Recover  C) Wrestle  D) Follow coach")
                        adj = (console.ask("Corner > ") or "D").strip().upper()
                        plan = dict(getattr(fighter, "_fight_plan", None) or {})
                        if adj == "A":
                            plan["pace"] = "high"
                            f_gas = max(20, f_gas - 4)
                            console.print("  Corner: hunt it.")
                        elif adj == "C":
                            plan["td"] = "Aggressive"
                            console.print("  Corner: connect to the wrestling.")
                        elif adj == "B":
                            plan["pace"] = "low"
                            f_gas = min(100, f_gas + 6)
                            console.print("  Corner: reset the lungs.")
                        else:
                            plan = dict(_suggest)
                            console.print("  Corner: adjustment accepted.")
                        fighter._fight_plan = plan
                    elif compact:
                        console.pause(0.3)
                    # Opponent adjustments were already resolved above by the
                    # v1.39 tactical intelligence layer.
                except Exception:
                    pass
            if sport == "taekwondo" and max(tkd_round_wins.values()) >= 2:
                tkd_match_complete = True
                break

    try:
        fighter.last_fight_adjustments = list(intel[True].get("adjustments", []))[-8:]
        opponent.last_fight_adjustments = list(intel[False].get("adjustments", []))[-8:]
    except Exception:
        pass

    if not finish:
        if sport == "grappling":
            who, how = SC.grappling_result(fs.technical_points, os_.technical_points,
                fs.control_ticks, os_.control_ticks, fs.submission_attempts, os_.submission_attempts)
            winner = {"a":"player","b":"opponent"}[who]; method=how
            f_pts,o_pts=fs.technical_points,os_.technical_points
        elif sport == "wrestling":
            a,b=fs.technical_points,os_.technical_points
            if a != b: winner="player" if a>b else "opponent"
            elif fs.takedowns_landed != os_.takedowns_landed: winner="player" if fs.takedowns_landed>os_.takedowns_landed else "opponent"
            elif fs.control_sec != os_.control_sec: winner="player" if fs.control_sec>os_.control_sec else "opponent"
            else: winner="player" if random.random()<.5 else "opponent"
            method="Points" if a!=b else "Criteria"; f_pts,o_pts=a,b
        elif sport == "judo":
            a,b=fs.technical_points,os_.technical_points
            if a != b:
                winner="player" if a>b else "opponent"; method="Waza-ari"
            else:
                # Golden score: technique/IQ/control edge decides the next score.
                edge=(_stat(fighter,"grappling")+_stat(fighter,"fight_iq")*.35+fs.control_sec*.08
                      -_stat(opponent,"grappling")-_stat(opponent,"fight_iq")*.35-os_.control_sec*.08)
                p=max(.25,min(.75,.5+edge/260.0)); winner="player" if random.random()<p else "opponent"; method="Golden Score"
            f_pts,o_pts=a,b
        elif sport == "taekwondo":
            a,b=int(fs.technical_points),int(os_.technical_points)
            rw_a,rw_b=int(tkd_round_wins[True]),int(tkd_round_wins[False])
            if rw_a == rw_b:
                winner = "player" if a>b else "opponent" if b>a else ("player" if random.random()<.5 else "opponent")
            else:
                winner = "player" if rw_a>rw_b else "opponent"
            method = "Round Points %s-%s" % (rw_a,rw_b)
            f_pts,o_pts=a,b
        elif sport == "combat_sambo":
            a,b=fs.technical_points,os_.technical_points
            if a != b:
                winner="player" if a>b else "opponent"; method="Technical Points"
            else:
                # FIAS tie-break spirit: higher-value/effective actions first, then last activity proxy.
                pa=(fs.knockdowns*8+fs.takedowns_landed*3+fs.submission_attempts*2+fs.control_ticks)
                pb=(os_.knockdowns*8+os_.takedowns_landed*3+os_.submission_attempts*2+os_.control_ticks)
                if pa != pb: winner="player" if pa>pb else "opponent"
                else: winner="player" if random.random()<.5 else "opponent"
                method="Technical Criteria"
            f_pts,o_pts=a,b
        else:
            # MMA / boxing / kickboxing use judge cards.
            who, label = SC.decision(judges)
            winner = {"a": "player", "b": "opponent"}.get(who, "draw")
            method, finish = label, None
            f_pts, o_pts = judges[0].totals
            for card in judges: notes.append(card.line())
            scorecards = [(c.name, c.totals[0], c.totals[1]) for c in judges]
            if compact:
                try:
                    console.print("CARDS  " + "  ".join(c.line() for c in judges))
                    console.print("%s — %s" % (label, {"a": fname, "b": oname}.get(who, "DRAW")))
                except Exception: pass
        if compact and sport in ("grappling","wrestling","judo","combat_sambo","taekwondo"):
            try: console.print("SCORE  %s-%s · %s" % (f_pts,o_pts,method))
            except Exception: pass

    try:
        fighter.damage = dict(getattr(fighter, "damage", None) or {})
        opponent.damage = dict(getattr(opponent, "damage", None) or {})
        _parts = ("cuts", "nose", "eyes", "body", "legs", "head")
        fighter.damage["total"] = min(100, sum(int(fighter.damage.get(k, 0) or 0) for k in _parts))
        opponent.damage["total"] = min(100, sum(int(opponent.damage.get(k, 0) or 0) for k in _parts))
        fighter.energy = max(8, int(f_gas))
        opponent.energy = max(8, int(o_gas))
    except Exception:
        pass
    if finish:
        notes.append(str(finish))
    return FightOutcome(
        winner=winner, method=method, finish_label=finish, technique=technique,
        f_score=f_pts, o_score=o_pts, periods=periods, sport=sport, notes=notes,
        log=log, f_stats=fs, o_stats=os_,
        result_word={"player": "WIN", "opponent": "LOSS"}.get(winner, "DRAW"),
        amateur=amateur, rules=rules, scorecards=scorecards,
        f_body=f_body, o_body=o_body,
        decision_type=(method if not finish else ""),
        final_range=range_band,
        range_control={"player": range_control[True], "opponent": range_control[False]},
        f_adjustments=list(intel[True].get("adjustments", []) or []),
        o_adjustments=list(intel[False].get("adjustments", []) or []),
        intelligence={
            "player_read": round(float(intel[True].get("profile", {}).get("read", 0)), 3),
            "opponent_read": round(float(intel[False].get("profile", {}).get("read", 0)), 3),
            "player_prep": dict(intel[True].get("prep", {}) or {}),
            "opponent_prep": dict(intel[False].get("prep", {}) or {}),
            # Bout-scoped decision telemetry is intentionally transient. It
            # makes balance/playtest audits able to verify that a gameplan or
            # adaptation changed behavior rather than only changing labels.
            "player_actions": dict(intel[True].get("self", {}) or {}),
            "opponent_actions": dict(intel[False].get("self", {}) or {}),
            "player_results": dict(intel[True].get("self_result", {}) or {}),
            "opponent_results": dict(intel[False].get("self_result", {}) or {}),
        },
        clock="R%s %s" % (
            period if finish else periods,
            _clock(max(0, period_len - end_elapsed) if finish else 0),
        ),
        end_period=period if finish else periods,
    )
