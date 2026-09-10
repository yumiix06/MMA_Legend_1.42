"""Engine surface used by combat.py and diagnostics."""
from __future__ import annotations

from .rules import (
    MMARuleset, GrapplingRuleset, BoxingRuleset,
    KickboxingRuleset, TaekwondoRuleset, WrestlingRuleset,
    JudoRuleset, CombatSamboRuleset,
)
from .fight import (
    simulate_fight, FightOutcome, FightStats, LogEvent,
)

__all__ = [
    "MMARuleset", "GrapplingRuleset", "BoxingRuleset",
    "KickboxingRuleset", "TaekwondoRuleset", "WrestlingRuleset",
    "JudoRuleset", "CombatSamboRuleset",
    "simulate_fight", "FightOutcome", "FightStats", "LogEvent",
]
