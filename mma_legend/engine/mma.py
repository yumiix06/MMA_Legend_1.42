from .base import Ruleset


class MMARuleset(Ruleset):
    name = "mma"
    sport = "mma"

    def __init__(self, amateur: bool = True, title: bool = False):
        self.amateur = amateur
        self.periods = 5 if (title and not amateur) else 3
        self.ticks_per_period = 16 if amateur else 18
        self.grappling_only = False
        self.period_seconds = 180 if amateur else 300
