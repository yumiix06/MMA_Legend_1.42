"""1.14 belts, ladder, purses, life menu."""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import booking, orgs, identity
from mma_legend.world import FighterPool


def test_named_org_purse_beats_room():
    f = Fighter.new_player("P", "B", country_by_name("Serbia"), "Wrestling")
    f.pro_debut = True
    orgs.sign_org(f, "Balkan Combat")
    wins = [booking.purse_for(f, "local")[0] for _ in range(8)]
    lo, hi = orgs.ORGS["Balkan Combat"]["purse"]
    assert min(wins) >= lo and max(wins) <= hi, (wins, lo, hi)
    return "Balkan purse inside %s-%s" % (lo, hi)


def test_next_org_never_ufc():
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.pro_record = [14, 1, 0]
    f.fame = 30
    f.organization = "Bellator"
    f.org_contract = {"org": "Bellator", "fights_left": 3, "weeks_left": 20}
    assert identity.next_org(f) != "UFC"
    f.organization = "LFA"
    f.org_contract = {"org": "LFA", "fights_left": 3, "weeks_left": 20}
    nxt = identity.next_org(f)
    assert nxt and nxt != "UFC" and nxt != "LFA"
    return "next from LFA is %s" % nxt


def test_belt_persists_and_moves():
    pool = FighterPool()
    pool.generate_world(30, 20)
    a = next(f for f in pool.fighters if f.pro_debut)
    org = identity.canonical_org(a) or orgs.home_org(a.country)
    a.organization = org
    pool.award_belt(org, a.weight_class, a)
    key = identity.belt_key(org, a.weight_class)
    assert key in pool.belts
    assert pool.belt_holder(org, a.weight_class) is a
    b = next(f for f in pool.fighters if f is not a and f.pro_debut)
    pool.award_belt(org, a.weight_class, b)
    assert pool.belt_holder(org, a.weight_class) is b
    return "belt %s -> %s" % (a.name, b.name)


def test_life_has_no_compete_toggle():
    import inspect
    from mma_legend import career
    src = inspect.getsource(career.lifestyle_menu)
    assert "Compete in" not in src
    assert "action_map" not in src
    return "life menu slim"


def main():
    for t in (
        test_named_org_purse_beats_room,
        test_next_org_never_ufc,
        test_belt_persists_and_moves,
        test_life_has_no_compete_toggle,
    ):
        print("PASS", t.__name__, t())
    print("ALL 1.14 OK")


if __name__ == "__main__":
    main()
