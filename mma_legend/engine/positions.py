"""Grappling / MMA positions, roles, and legal actions (1.9).

A ground position is not symmetric. Being in mount and being *under* mount are
different situations with different options, and before 1.9 the engine did not
distinguish them: whoever acted from "mount" was offered ground-and-pound, and
whoever acted from "back" was offered the choke, regardless of which fighter
had actually won the position.

So every ground position now has two roles:

    top    - the fighter who holds the position (mount, side, back control,
             passing the guard, riding a turtle)
    bottom - the fighter underneath (guard player, mount escape, back defence)

Stand and clinch are neutral: both fighters have the same options.
"""
from __future__ import annotations

POSITIONS = (
    "stand",
    "clinch",
    "closed_guard",
    "open_guard",
    "half_guard",
    "side",
    "north_south",
    "mount",
    "back",
    "turtle",
    "front_headlock",
    "leg_entanglement",
)

NEUTRAL = frozenset({"stand", "clinch"})
GROUND = tuple(p for p in POSITIONS if p not in NEUTRAL)

LABEL = {
    "stand": "STANDING",
    "clinch": "CLINCH",
    "closed_guard": "CLOSED GUARD",
    "open_guard": "OPEN GUARD",
    "half_guard": "HALF GUARD",
    "side": "SIDE CONTROL",
    "north_south": "NORTH-SOUTH",
    "mount": "MOUNT",
    "back": "BACK CONTROL",
    "turtle": "TURTLE",
    "front_headlock": "FRONT HEADLOCK",
    "leg_entanglement": "LEG ENTANGLEMENT",
}


def label(pos: str, role: str | None = None) -> str:
    """Display name including which side of the position you are on."""
    base = LABEL.get(pos, str(pos).upper())
    if pos in NEUTRAL or not role:
        return base
    if pos == "back":
        return base + (" (you have the back)" if role == "top" else " (back taken)")
    if pos == "turtle":
        return base + (" (riding)" if role == "top" else " (turtled)")
    if pos == "closed_guard":
        return base + (" (in his guard)" if role == "top" else " (playing guard)")
    return base + (" (top)" if role == "top" else " (bottom)")


# Neutral positions: identical options for both fighters.
NEUTRAL_ACTIONS = {
    "stand": {
        "jab", "cross", "hook", "uppercut", "low_kick", "head_kick", "liver",
        "body_kick", "teep", "body_punch", "side_kick", "spin_back_kick",
        "spin_hook_kick", "axe_kick", "tornado_kick", "double_leg", "single_leg", "clinch_entry", "sprawl",
        "snap_down",
    },
    "clinch": {
        "hook", "uppercut", "liver", "dirty_box", "knee_body",
        "trip", "throw", "double_leg", "single_leg", "guillotine", "break",
        "snap_down",
    },
}

# Ground positions, split by role.
ROLE_ACTIONS = {
    "closed_guard": {
        # Inside his closed guard, trying to open and pass.
        "top": {"guard_pass", "gnp", "kimura", "stand_up", "scramble", "ride"},
        # On your back playing guard - this is where guard subs live.
        "bottom": {"armbar", "triangle", "kimura", "guillotine", "sweep", "stand_up", "scramble", "leg_entry"},
    },
    "open_guard": {
        "top": {"guard_pass", "gnp", "stand_up", "ride"},
        "bottom": {"triangle", "armbar", "sweep", "stand_up", "scramble", "leg_entry"},
    },
    "half_guard": {
        "top": {"guard_pass", "gnp", "kimura", "scramble", "ride"},
        "bottom": {"sweep", "kimura", "stand_up", "scramble", "leg_entry"},
    },
    "side": {
        "top": {"gnp", "kimura", "armbar", "mount_up", "north_south_move", "ride"},
        "bottom": {"escape", "stand_up"},
    },
    "north_south": {
        "top": {"north_south_choke", "kimura", "mount_up", "ride"},
        "bottom": {"escape", "scramble"},
    },
    "mount": {
        "top": {"gnp", "armbar", "ride"},
        "bottom": {"escape", "sweep"},
    },
    "back": {
        "top": {"rear_naked", "gnp", "ride"},
        "bottom": {"escape"},
    },
    "turtle": {
        "top": {"gnp", "take_back", "anaconda", "snap_down", "ride"},
        "bottom": {"stand_up", "escape", "scramble"},
    },
    "front_headlock": {
        "top": {"guillotine", "anaconda", "take_back", "gnp", "ride"},
        "bottom": {"stand_up", "escape", "scramble"},
    },
    "leg_entanglement": {
        "top": {"heel_hook", "kneebar", "ride", "escape"},
        "bottom": {"heel_hook", "kneebar", "escape", "scramble"},
    },
}

# action -> every position it can ever be thrown from (either role).
# Derived, so it can never drift from the tables above.
LEGAL: dict = {}
for _pos, _acts in NEUTRAL_ACTIONS.items():
    for _a in _acts:
        LEGAL.setdefault(_a, set()).add(_pos)
for _pos, _roles in ROLE_ACTIONS.items():
    for _acts in _roles.values():
        for _a in _acts:
            LEGAL.setdefault(_a, set()).add(_pos)

# Strikes that simply do not exist under pure grappling rules.
GRAPPLING_BANNED = frozenset({
    "jab", "cross", "hook", "uppercut", "low_kick", "head_kick", "body_kick", "teep",
    "dirty_box", "gnp", "liver", "knee_body", "body_punch", "side_kick",
    "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick",
})

# Positions where the top fighter accrues control time.
# Closed guard still counts as top control in MMA (GnP, referee stand-up clock).
# ADCC scoring treats it as neutral-ish, but ticks still accrue so hammerfists
# in guard are not invisible on the card.
CONTROL_POSITIONS = frozenset({
    "mount", "back", "side", "north_south", "half_guard", "turtle",
    "front_headlock", "leg_entanglement", "closed_guard", "open_guard",
})

# Neutral transitions: action -> resulting position.
NEXT_POS = {
    "double_leg": "closed_guard",
    "single_leg": "half_guard",
    "trip": "half_guard",
    "throw": "side",
    "clinch_entry": "clinch",
    "break": "stand",
    "sprawl": "stand",
    "stand_up": "stand",
    "mount_up": "mount",
    "take_back": "back",
    "snap_down": "front_headlock",
    "leg_entry": "leg_entanglement",
    "north_south_move": "north_south",
}

# Where a bottom fighter's escape lands. Not straight to standing - escaping
# mount puts you back in guard, and you still have work to do.
ESCAPE_TO = {
    "mount": "half_guard",
    "side": "closed_guard",
    "back": "turtle",
    "turtle": "stand",
    "half_guard": "closed_guard",
    "closed_guard": "stand",
    "open_guard": "stand",
    "front_headlock": "stand",
    "north_south": "side",
    "leg_entanglement": "open_guard",
}

# Guard passing chain.
PASS_TO = {
    "closed_guard": "open_guard",
    "open_guard": "half_guard",
    "half_guard": "side",
}

KO_BASE = {
    "jab": 0.012,
    "cross": 0.045,
    "hook": 0.075,
    "uppercut": 0.08,
    "overhand": 0.10,
    "head_kick": 0.13,
    "spin_hook_kick": 0.16,
    "axe_kick": 0.11,
    "tornado_kick": 0.17,
    "liver": 0.018,
    "dirty_box": 0.03,
    "gnp": 0.025,
    "knee_body": 0.02,
}

# Ground-and-pound is far more dangerous from mount than from inside guard.
GNP_POWER = {
    "mount": 1.6,
    "back": 1.3,
    "side": 1.2,
    "turtle": 1.0,
    "half_guard": 0.8,
    "closed_guard": 0.5,
}

SUBMISSIONS = frozenset({
    "rear_naked", "armbar", "triangle", "kimura", "guillotine", "anaconda",
    "heel_hook", "kneebar", "north_south_choke",
})


def legal_actions(pos: str, grappling_only: bool = False, role=None) -> set:
    """Actions legal from `pos`. If `role` is given ("top"/"bottom") the set is
    restricted to that side of the position; otherwise the union is returned."""
    if pos in NEUTRAL_ACTIONS:
        out = set(NEUTRAL_ACTIONS[pos])
    elif pos in ROLE_ACTIONS:
        roles = ROLE_ACTIONS[pos]
        if role in roles:
            out = set(roles[role])
        else:
            out = set().union(*roles.values())
    else:
        out = set()
    if grappling_only:
        out -= GRAPPLING_BANNED
    return out


def is_legal(pos: str, action: str, grappling_only: bool = False, role=None) -> bool:
    return action in legal_actions(pos, grappling_only, role)


def apply_transition(pos: str, action: str, role=None):
    """Return (new_position, role_swapped).

    `role_swapped` is True when the acting fighter and their opponent trade
    top/bottom - which is exactly what a sweep is.
    """
    if action == "sweep":
        return ("half_guard", True)
    if action == "scramble":
        # Coin-flip athletic scramble: either you come up in half or both hit the feet.
        import random as _r
        if _r.random() < 0.45:
            return ("stand", False)
        return ("half_guard", True)
    if action == "escape":
        return (ESCAPE_TO.get(pos, "stand"), False)
    if action == "guard_pass":
        return (PASS_TO.get(pos, "side"), False)
    if action in NEXT_POS:
        return (NEXT_POS[action], False)
    return (pos, False)


def dominant(pos: str) -> bool:
    return pos in ("mount", "back", "side", "north_south", "front_headlock")


def is_control(pos: str) -> bool:
    return pos in CONTROL_POSITIONS


def other_role(role):
    if role == "top":
        return "bottom"
    if role == "bottom":
        return "top"
    return role
