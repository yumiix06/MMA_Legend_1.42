from .base import Ruleset


class JudoRuleset(Ruleset):
    """Amateur judo: throws, pins and legal upper-body submissions."""
    name = "judo"
    sport = "judo"
    periods = 1
    ticks_per_period = 12
    grappling_only = True
    amateur = True
    period_seconds = 240
    allowed_actions = frozenset({
        "clinch_entry", "trip", "throw", "break", "guard_pass", "sweep",
        "scramble", "escape", "stand_up", "mount_up", "take_back",
        "armbar", "rear_naked", "kimura", "ride",
    })

    def label_period(self, n: int) -> str:
        return "JUDO MATCH"
