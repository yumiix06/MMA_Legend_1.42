from .base import Ruleset


class GrapplingRuleset(Ruleset):
    """One continuous period. ADCC-style points + submissions.
    Amateur no-gi night: ~6 minutes represented as one period, many ticks.
    """
    name = "grappling"
    sport = "grappling"
    periods = 1
    ticks_per_period = 14
    grappling_only = True
    amateur = True
    period_seconds = 360
    blocked_actions = frozenset({
        "jab", "cross", "hook", "uppercut", "liver", "low_kick", "head_kick",
        "body_kick", "teep", "dirty_box", "knee_body", "gnp",
    })

    def label_period(self, n: int) -> str:
        return "NO-GI MATCH (ADCC-inspired)"
