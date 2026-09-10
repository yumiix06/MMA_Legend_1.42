"""1.19.2 checks: one booking spine, and physically real weight cuts."""
from __future__ import annotations

import inspect
import random

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import matchroom, cut, career


def _pro():
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.week = 60
    return f


# ---------------- booking spine ----------------

def test_single_gate():
    f = _pro()
    f.suspension_weeks = 4
    ok, why = matchroom.gate(f)
    assert ok is False and why, why
    f.suspension_weeks = 0
    f.fight_cooldown = 3
    assert matchroom.gate(f)[0] is False
    f.fight_cooldown = 0
    assert matchroom.gate(f)[0] is True
    return "one gate answers suspension and recovery"


def test_menus_thread_the_pool():
    """manager_menu used to call booking with pool=None, so offers were built
    with no world to draw opponents from."""
    assert "pool" in inspect.signature(career.manager_menu).parameters
    assert "pool" in inspect.signature(career.lifestyle_menu).parameters
    return "manager and lifestyle menus accept a pool"


def test_booked_status():
    f = _pro()
    assert matchroom.booked_status(f) == {}
    f.booked_fight = {"org": "LFA", "date_week": 66, "opponent_name": "X"}
    st = matchroom.booked_status(f)
    assert st["weeks_out"] == 6 and st["due"] is False
    f.week = 66
    assert matchroom.booked_status(f)["due"] is True
    return "booked status is computed in one place"


# ---------------- weight ----------------

def test_impossible_cut_rejected():
    """The reported bug: a 118kg fighter could declare Light Heavyweight."""
    f = Fighter.new_player("B", "B", country_by_name("USA"), "Boxing")
    f.weight = 118
    f.walking_weight = 118.0
    probe = cut.cut_feasibility(f, "Light Heavyweight")
    assert probe["makeable"] is False, probe
    assert probe["frac"] > 0.18
    assert cut.cut_feasibility(f, "Flyweight")["makeable"] is False
    return "118kg -> 93kg correctly impossible (%.0f%% cut)" % (probe["frac"] * 100)


def _feas_ok(walk, wc):
    from mma_legend import constants as C  # noqa: F401
    cap = cut.CLASS_LIMIT[wc]
    return (walk - cap) / walk <= cut.CUT_IMPOSSIBLE


def test_lowest_class_is_sane():
    f = Fighter.new_player("B", "B", country_by_name("USA"), "Boxing")
    f.walking_weight = 118.0
    assert cut.lowest_class_for(118.0) == "Heavyweight"
    # 84kg can technically reach Lightweight (70.3) — an 18% cut, the
    # absolute physiological edge. It must NOT reach Featherweight (65.8).
    assert cut.lowest_class_for(84.0) == "Lightweight"
    assert _feas_ok(84.0, "Featherweight") is False
    return "lowest makeable class is physically sensible"


def test_cut_bands():
    f = Fighter.new_player("R", "B", country_by_name("USA"), "Wrestling")
    f.weight = 84
    f.walking_weight = 84.0
    assert cut.cut_feasibility(f, "Middleweight")["band"] == "natural"
    assert cut.cut_feasibility(f, "Welterweight")["band"] in ("routine", "hard")
    assert cut.cut_feasibility(f, "Lightweight")["band"] in ("brutal", "impossible")
    return "cut difficulty scales with the gap"


def test_discipline_decides_a_brutal_cut():
    """A brutal cut should be survivable only with a properly run camp."""
    f = Fighter.new_player("R", "B", country_by_name("USA"), "Wrestling")
    f.weight = 84
    f.walking_weight = 84.0
    f.fight_weight_class = f.weight_class = "Lightweight"
    made_low = made_high = 0
    state = random.getstate()
    random.seed(1920)
    try:
        for _ in range(200):
            f.nutrition = 25
            f.energy = 80; f.weight_cut_health = 100; f.cut_fatigue = 0
            made_low += cut.weigh_in(f)["made"]
            f.nutrition = 90
            f.energy = 80; f.weight_cut_health = 100; f.cut_fatigue = 0
            made_high += cut.weigh_in(f)["made"]
    finally:
        random.setstate(state)
    assert made_high > made_low + 80, (made_low, made_high)
    return "sloppy camp %d%% vs disciplined %d%% on a brutal cut" % (
        made_low / 2, made_high / 2)


def test_hard_cut_drains_energy():
    f = Fighter.new_player("R", "B", country_by_name("USA"), "Wrestling")
    f.weight = 84
    f.walking_weight = 84.0
    f.fight_weight_class = f.weight_class = "Lightweight"
    f.energy = 90
    f.nutrition = 90
    cut.weigh_in(f)
    assert f.energy < 90, f.energy
    assert int(getattr(f, "cut_drain", 0)) > 0
    return "a hard cut costs energy on fight night"


def test_natural_weight_no_drain():
    f = Fighter.new_player("R", "B", country_by_name("USA"), "Wrestling")
    f.weight = 84
    f.walking_weight = 84.0
    f.fight_weight_class = f.weight_class = "Middleweight"
    f.energy = 90
    cut.weigh_in(f)
    assert f.energy == 90
    assert int(getattr(f, "cut_drain", 0)) == 0
    return "walking at the limit costs nothing"


def main():
    for t in (
        test_single_gate,
        test_menus_thread_the_pool,
        test_booked_status,
        test_impossible_cut_rejected,
        test_lowest_class_is_sane,
        test_cut_bands,
        test_discipline_decides_a_brutal_cut,
        test_hard_cut_drains_energy,
        test_natural_weight_no_drain,
    ):
        print("PASS", t())
    print("ALL 1.19.2 CHECKS OK")


if __name__ == "__main__":
    main()
