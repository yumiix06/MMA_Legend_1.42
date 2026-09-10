"""Athletic age vs calendar age."""
from __future__ import annotations


def athletic_age(fighter) -> float:
    age = float(getattr(fighter, "age", 22) or 22)
    wear = float(getattr(fighter, "mileage", 0) or 0)
    return age + wear * 0.15


def tick_birthday(fighter, console=None) -> None:
    """Advance one birthday at the start of each new 52-week career year.

    This is the only writer for player age.  A second legacy increment used to
    live in Fighter.advance_week(), making a 16-year-old turn 22 by week 178.
    """
    week = int(getattr(fighter, "week", 1) or 1)
    if week < 2 or week % 52 != 1:
        return
    fighter.age = int(getattr(fighter, "age", 16) or 16) + 1
    age = fighter.age
    apply_aging = getattr(fighter, "_apply_aging", None)
    if callable(apply_aging):
        apply_aging(console)
    try:
        from .timeline import add
        add(fighter, "Turned %s." % age)
    except (ImportError, AttributeError, TypeError):
        pass
