from .base import Ruleset


class CombatSamboRuleset(Ruleset):
    """Amateur combat sambo: striking, throws and submissions; no cage elbows."""
    name = "combat_sambo"
    sport = "combat_sambo"
    periods = 1
    ticks_per_period = 14
    grappling_only = False
    amateur = True
    period_seconds = 300
    allowed_actions = frozenset({
        "jab", "cross", "hook", "uppercut", "liver", "low_kick", "head_kick",
        "body_kick", "teep", "side_kick", "spin_back_kick", "spin_hook_kick",
        "axe_kick", "tornado_kick", "clinch_entry", "dirty_box", "knee_body", "break",
        "double_leg", "single_leg", "sprawl", "trip", "throw", "guard_pass",
        "sweep", "scramble", "escape", "stand_up", "mount_up", "take_back",
        "rear_naked", "armbar", "triangle", "kimura", "guillotine", "kneebar",
    })

    def label_period(self, n: int) -> str:
        return "COMBAT SAMBO BOUT"
