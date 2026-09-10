from .base import Ruleset


class BoxingRuleset(Ruleset):
    """Amateur boxing: hands only, standing, three-minute rounds."""
    name = "boxing"
    sport = "boxing"
    periods = 3
    ticks_per_period = 8
    grappling_only = False
    amateur = True
    period_seconds = 180
    allowed_actions = frozenset({"jab", "cross", "hook", "uppercut", "liver"})
