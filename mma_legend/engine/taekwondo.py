from .base import Ruleset


class TaekwondoRuleset(Ruleset):
    """WT-style kyorugi: three two-minute rounds, trunk punches and kicks.

    Scoring is handled in fight.py because turning techniques carry extra
    technical value and the match is decided by rounds won.
    """
    name = "taekwondo"
    sport = "taekwondo"
    periods = 3
    ticks_per_period = 8
    grappling_only = False
    amateur = True
    period_seconds = 120
    allowed_actions = frozenset({
        "body_punch", "teep", "body_kick", "head_kick", "side_kick",
        "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick",
    })
