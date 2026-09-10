from .base import Ruleset


class WrestlingRuleset(Ruleset):
    name = "wrestling"
    sport = "wrestling"
    periods = 2
    ticks_per_period = 10
    grappling_only = True
    amateur = True
    period_seconds = 180
    allowed_actions = frozenset({
        "double_leg", "single_leg", "sprawl", "clinch_entry", "trip", "throw",
        "break", "guard_pass", "sweep", "scramble", "escape", "stand_up",
        "mount_up", "take_back",
        "snap_down", "ride", "north_south_move",
    })
