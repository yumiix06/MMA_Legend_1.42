"""1.24 release-gate checks for physiology, nutrition, perks and telemetry."""
from __future__ import annotations

import random

from mma_legend.data import country_by_name, SPONSORS_DB
from mma_legend.models import Fighter
from mma_legend import cut, physiology, perks, record, identity


def _f(wc="Lightweight", physique="Athletic"):
    f = Fighter.new_player("QA", "B", country_by_name("Greece"), "Boxing")
    f.physique_type = physique
    f.weight_class = wc; f.fight_weight_class = wc; f.natural_weight_class = wc
    cap = float(cut.CLASS_LIMIT[wc])
    f.weight = cap; f.natural_weight = cap * 1.04; f.walking_weight = cap * 1.04
    f.bodyfat = 12.0; f.nutrition = 75; f.weight_cut_health = 90
    return f


def test_structured_nutrition_is_single_source():
    f = _f(); f.camp_active = False; f.camp_for_bout = 0
    f.walking_weight = f.natural_weight = 75.0; f.bodyfat = 12.0
    f.meal_plan = "Comfort Food"
    cut.tick_body(f)
    # JSON says +0.35kg/w. Old substring engine stacked another +0.15/+fill.
    assert 75.30 <= f.walking_weight <= 75.40, f.walking_weight
    assert 12.05 <= f.bodyfat <= 12.20, f.bodyfat
    g = _f(); g.walking_weight = g.natural_weight = 75.0; g.meal_plan = "Mystery Comfort Cut"
    cut.tick_body(g)
    assert abs(g.walking_weight - 75.0) < 0.02, g.walking_weight
    return "meal-plan JSON drives mass; labels no longer secretly change physiology"


def test_cut_health_is_not_double_recovered():
    f = _f(); f.meal_plan = "Balanced Athlete"; f.weight_cut_health = 50; f.camp_active = False
    cut.tick_body(f)
    assert f.weight_cut_health == 50
    physiology.nutrition_week(f)
    assert f.weight_cut_health == 52, f.weight_cut_health
    return "weekly cut-health recovery is owned by nutrition_week only"


def test_division_caps_and_tradeoffs():
    fly = _f("Flyweight"); heavy = _f("Heavyweight")
    fly.speed = fly.cardio = heavy.speed = heavy.cardio = 99
    assert physiology.stat_cap(fly, "speed") == 100
    assert physiology.stat_cap(heavy, "speed") == 88
    assert physiology.stat_cap(heavy, "cardio") == 88
    physiology.gain_stat(heavy, "cardio", 50)
    assert heavy.cardio == 88
    assert physiology.impact_multiplier(heavy) > physiology.impact_multiplier(fly)
    assert physiology.gas_cost_multiplier(heavy) > physiology.gas_cost_multiplier(fly)
    return "heavyweights express more impact but lower speed/cardio ceilings and higher gas cost"


def test_weighin_preserves_walking_weight_and_hard_cut_costs_more():
    easy = _f("Lightweight"); hard = _f("Lightweight")
    easy.walking_weight = 71.2; easy.natural_weight = 72.0
    hard.walking_weight = 76.5; hard.natural_weight = 77.0
    ew, hw = easy.walking_weight, hard.walking_weight
    random.seed(12401); a = cut.weigh_in(easy)
    random.seed(12401); b = cut.weigh_in(hard)
    assert easy.walking_weight == ew and hard.walking_weight == hw
    assert b["cut_pct"] > a["cut_pct"] and b["cut_drain"] > a["cut_drain"], (a, b)
    assert b["cage_kg"] <= hw and a["cage_kg"] <= ew
    return "scale/cage weight are temporary; larger cuts buy size at a real conditioning cost"


def test_hard_cut_misses_more_in_monte_carlo():
    def rate(walk):
        misses = 0
        for seed in range(260):
            f = _f("Lightweight"); f.walking_weight = walk; f.natural_weight = walk
            f.nutrition = 75; f.weight_cut_health = 85
            random.seed(seed)
            misses += not cut.weigh_in(f)["made"]
        return misses / 260.0
    easy, hard = rate(72.0), rate(79.0)
    assert hard > easy + 0.12, (easy, hard)
    return "hard-cut miss rate %.0f%% vs routine %.0f%%" % (hard * 100, easy * 100)


def test_doping_risk_is_not_a_generic_cut_bonus():
    a = _f(); b = _f(); a.walking_weight = b.walking_weight = 75.5
    a.doping_risk = 0; b.doping_risk = 90
    assert cut.cut_risk(a) == cut.cut_risk(b), (cut.cut_risk(a), cut.cut_risk(b))
    random.seed(77); wa = cut.weigh_in(a)
    random.seed(77); wb = cut.weigh_in(b)
    assert wa == wb, (wa, wb)
    return "generic PED risk no longer magically improves a weight cut"


def test_perks_are_consumed_by_gameplay():
    f = _f(); f.perks = ["film_room", "body_work", "grinder", "glass"]
    assert perks.accuracy_bonus(f, "liver", 2) > 0.02
    assert perks.action_weight_multiplier(f, "body_kick", 2) > 1.0
    assert perks.gas_cost_multiplier(f, 2) < 1.0
    assert perks.ko_received_multiplier(f) > 1.0
    chin = _f(); chin.perks = ["iron_chin"]
    assert perks.ko_received_multiplier(chin) < 1.0
    return "earned perks now feed accuracy, tendencies, gas and chin logic"


def test_performance_rating_is_meaningful():
    good = {"strikes_landed": 28, "strikes_attempted": 40, "ground_strikes_landed": 3,
            "ground_strikes_attempted": 5, "takedowns_landed": 2, "control_sec": 80,
            "knockdowns": 1, "submission_attempts": 1, "passes": 1, "back_takes": 0, "mount_ups": 0}
    bad = {"strikes_landed": 13, "strikes_attempted": 35, "ground_strikes_landed": 0,
           "ground_strikes_attempted": 2, "takedowns_landed": 0, "control_sec": 12,
           "knockdowns": 0, "submission_attempts": 0, "passes": 0, "back_takes": 0, "mount_ups": 0}
    wr = record.performance_rating(good, bad, "Win", "TKO", 2)
    lr = record.performance_rating(bad, good, "Loss", "TKO", 2)
    assert 1 <= lr < wr <= 10 and wr != 0.0, (wr, lr)
    return "fight ledger now carries a defined 1-10 performance grade"


def test_big_sponsors_require_pro_resume_and_audience():
    f = _f(); f.pro_debut = True; f.pro_record = [0, 2, 0]; f.fame = 100; f.followers = 100
    nike = next(s for s in SPONSORS_DB if s["name"] == "Nike")
    assert not cut.sponsor_allowed(f, nike)
    f.pro_record = [5, 1, 0]; f.followers = 25
    assert cut.sponsor_allowed(f, nike)
    f.fame = 204; identity.sync(f)
    assert f.fame == 100
    return "global brands use pro résumé + audience; fame is consistently bounded 0-100"


def main():
    tests = (
        test_structured_nutrition_is_single_source,
        test_cut_health_is_not_double_recovered,
        test_division_caps_and_tradeoffs,
        test_weighin_preserves_walking_weight_and_hard_cut_costs_more,
        test_hard_cut_misses_more_in_monte_carlo,
        test_doping_risk_is_not_a_generic_cut_bonus,
        test_perks_are_consumed_by_gameplay,
        test_performance_rating_is_meaningful,
        test_big_sponsors_require_pro_resume_and_audience,
    )
    for t in tests:
        print("PASS", t())
    print("ALL 1.24 RELEASE-GATE CHECKS OK")


if __name__ == "__main__":
    main()
