"""Ruleset package surface expected by combat.py and tests."""
from .base import Ruleset
from .mma import MMARuleset
from .grappling import GrapplingRuleset
from .boxing import BoxingRuleset
from .kickboxing import KickboxingRuleset
from .taekwondo import TaekwondoRuleset
from .wrestling import WrestlingRuleset
from .judo import JudoRuleset
from .combat_sambo import CombatSamboRuleset

__all__ = [
    "Ruleset",
    "MMARuleset",
    "GrapplingRuleset",
    "BoxingRuleset",
    "KickboxingRuleset", "TaekwondoRuleset",
    "WrestlingRuleset",
    "JudoRuleset", "CombatSamboRuleset",
]
