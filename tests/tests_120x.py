"""1.20 checks: locational damage, real finishes, and injuries."""
from __future__ import annotations

import collections
import random

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.damage import BodyMap
from mma_legend import damage as D, booking, matchroom
from mma_legend.engine import simulate_fight
from mma_legend.engine.rules import MMARuleset


def test_locations_feed_different_systems():
    bm = BodyMap()
    for _ in range(30):
        bm.hit("low_kick", 3)
    assert bm.leg_penalty() < 1.0, "leg damage must restrict kicks"
    bm2 = BodyMap()
    for _ in range(30):
        bm2.hit("liver", 3)
    assert bm2.gas_drain() > 0, "body damage must cost gas"
    assert bm2.leg_penalty() == 1.0, "body damage must not hurt the legs"
    bm3 = BodyMap()
    for _ in range(30):
        bm3.hit("cross", 3)
    assert bm3.ko_bonus() > 0, "head trauma must raise KO chance"
    return "head/body/leg each drive their own system"


def test_checked_kick_hurts_the_kicker():
    kicker, defender = BodyMap(), BodyMap()
    before = kicker.loc["lead_leg"]
    defender.check_kick(kicker)
    assert kicker.loc["lead_leg"] > before
    return "checking a kick damages the kicker"


def test_leg_and_body_and_cut_stoppages_exist():
    bm = BodyMap()
    bm.loc["lead_leg"] = 95
    assert bm.leg_tko() is True
    bm2 = BodyMap()
    bm2.loc["body"] = 95
    assert bm2.body_tko() is True
    bm3 = BodyMap()
    bm3.cuts["left brow"] = 90
    assert bm3.cut_stoppage() is True
    return "leg TKO, body stoppage and doctor stoppage all defined"


def test_finish_rate_is_realistic():
    random.seed(9)
    m = collections.Counter()
    styles = ["Boxing", "Muay Thai", "Wrestling", "BJJ", "Kickboxing"]
    for _ in range(400):
        sa, sb = random.sample(styles, 2)
        a = Fighter.new_npc("A", country_by_name("USA"), style=sa)
        booking.apply_kit(a, sa)
        b = Fighter.new_npc("B", country_by_name("USA"), style=sb)
        booking.apply_kit(b, sb)
        m[simulate_fight(a, b, MMARuleset(amateur=False)).method] += 1
    total = sum(m.values())
    dec = sum(v for k, v in m.items() if "Decision" in k or "Draw" in k)
    pct = 100 * dec / total
    assert 40 <= pct <= 78, "decision rate unrealistic: %.0f%%" % pct
    return "decisions %.0f%% / finishes %.0f%%" % (pct, 100 - pct)


def test_body_map_reaches_outcome():
    random.seed(2)
    a = Fighter.new_npc("A", country_by_name("USA"), style="Muay Thai")
    booking.apply_kit(a, "Muay Thai")
    b = Fighter.new_npc("B", country_by_name("USA"), style="Boxing")
    booking.apply_kit(b, "Boxing")
    o = simulate_fight(a, b, MMARuleset(amateur=False))
    assert o.f_body is not None and o.o_body is not None
    return "body maps are exposed on FightOutcome"


# ---------------- injuries ----------------

def test_injury_blocks_booking():
    f = Fighter.new_player("I", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    D.add_injury(f, "torn knee", "sparring")
    ok, why = D.can_fight(f)
    assert ok is False and "torn knee" in why
    gok, gwhy = matchroom.gate(f)
    assert gok is False, "the one booking gate must respect injuries"
    return "a serious injury blocks every booking path"


def test_surgery_and_physio():
    f = Fighter.new_player("S", "B", country_by_name("USA"), "Boxing")
    f.money = 9000
    D.add_injury(f, "broken hand")
    rec = D.active_injuries(f)[0]
    base = rec["weeks"]
    D.treat(f, rec, "surgery")
    assert rec["weeks"] < base, "surgery must shorten recovery"
    assert f.money < 9000, "surgery must cost money"
    f2 = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f2.money = 9000
    D.add_injury(f2, "broken hand")
    r2 = D.active_injuries(f2)[0]
    D.treat(f2, r2, "physio")
    assert r2["weeks"] < base
    assert (9000 - f2.money) < (9000 - f.money), "physio must be cheaper"
    return "surgery is fast and dear, physio is slow and cheap"


def test_injuries_heal_and_clear():
    f = Fighter.new_player("H", "B", country_by_name("USA"), "Boxing")
    D.add_injury(f, "broken nose")
    for _ in range(6):
        D.tick(f)
    assert not D.active_injuries(f)
    assert D.can_fight(f)[0] is True
    return "injuries heal on the weekly tick"


def test_rare_injuries_are_rare():
    f = Fighter.new_player("R", "B", country_by_name("USA"), "Boxing")
    random.seed(1)
    hits = 0
    for wk in range(500):
        f.week = wk
        if D.random_life_injury(f):
            hits += 1
        for rec in D.injury_list(f):
            rec["weeks"] = 0
        f.story_flags["injuries"] = []
    assert 0 < hits < 40, "life injuries fire %d times in 500 weeks" % hits
    return "%d life injuries in 500 weeks" % hits


def test_broken_hand_exists():
    for n in ("broken hand", "broken knuckle", "orbital fracture", "torn knee"):
        assert n in D.INJURIES, n
    assert D.INJURIES["torn knee"][0] >= 20, "an ACL should be a long layoff"
    return "serious fractures and ligament tears are modelled"


def main():
    for t in (
        test_locations_feed_different_systems,
        test_checked_kick_hurts_the_kicker,
        test_leg_and_body_and_cut_stoppages_exist,
        test_finish_rate_is_realistic,
        test_body_map_reaches_outcome,
        test_injury_blocks_booking,
        test_surgery_and_physio,
        test_injuries_heal_and_clear,
        test_rare_injuries_are_rare,
        test_broken_hand_exists,
    ):
        print("PASS", t())
    print("ALL 1.20 DAMAGE / INJURY CHECKS OK")


if __name__ == "__main__":
    main()
