"""1.6 rating, economy, aging, actions."""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import rating, economy, aging, systems15
from mma_legend.engine import positions as P
from mma_legend.engine.fight import _TECH_CATALOG


def _f():
    return Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")


def test_rating_window():
    a = _f()
    b = Fighter.new_npc("O", country_by_name("USA"), "Boxing")
    assert rating.power(a) > 0
    assert rating.window(a) >= 6
    return "rating %.1f window %.1f" % (rating.power(a), rating.window(a))


def test_actions_import():
    """The combat catalog (engine.fight._TECH_CATALOG) is the single source
    of playable techniques; position legality (engine.positions.LEGAL) is
    the single source of where each one may be thrown from."""
    assert any(action == "guillotine" for _, action, _, _ in _TECH_CATALOG)
    assert "guillotine" in P.LEGAL
    assert P.LEGAL["guillotine"] == {"clinch", "closed_guard", "front_headlock"}
    f = _f()
    assert "Guillotine" not in [t for t in (f.techniques or [])]
    return "combat catalog %s techniques, %s legal action ids" % (len(_TECH_CATALOG), len(P.LEGAL))


def test_loan_and_ledger():
    f = _f()
    f.age = 20
    f.money = 10
    systems15.take_loan(f, 400)
    assert f.debt >= 400
    economy.apply_weekly(f)
    assert "expenses" in (f.last_ledger or {})
    return "debt %s ledger ok" % f.debt


def test_aging_tick():
    f = _f()
    f.age = 34
    f.week = 53
    f.speed = 50
    aging.tick_birthday(f)
    assert f.age == 35
    return "age %s speed %s" % (f.age, f.speed)


def test_suspend_and_cash():
    f = _f()
    f.suspension_weeks = 4
    from mma_legend.systems15 import can_compete
    assert "Suspended" in can_compete(f)
    f.suspension_weeks = 0
    f.money = 10
    from mma_legend.cut import weekly_costs
    weekly_costs(f)
    return "suspend + cash %s" % f.money


def main():
    for t in (test_rating_window, test_actions_import, test_loan_and_ledger, test_aging_tick, test_suspend_and_cash):
        print("PASS", t())
    print("ALL 1.6 CHECKS OK")


if __name__ == "__main__":
    main()
