from .base import Ruleset


class KickboxingRuleset(Ruleset):
    name = "kickboxing"
    sport = "kickboxing"
    periods = 3
    ticks_per_period = 8
    grappling_only = False
    amateur = True
    period_seconds = 120
    allowed_actions = frozenset({
        "jab", "cross", "hook", "uppercut", "liver", "low_kick", "head_kick",
        "body_kick", "teep", "side_kick", "spin_back_kick", "spin_hook_kick",
        "axe_kick", "tornado_kick", "clinch_entry", "dirty_box", "knee_body", "break",
    })
