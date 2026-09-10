"""1.13 identity + body."""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import booking, orgs, identity, cut, persistence, contracts


def _kamil_like():
    f = Fighter.new_player("Kamil Mensah", "E", country_by_name("Serbia"), "Wrestling")
    f.pro_debut = True
    f.pro_record = [4, 0, 0]
    f.natural_weight = 93.0
    f.walking_weight = 79.9
    f.bodyfat = 5.0
    f.physique_type = "Heavy-built"
    f.weight_class = "Middleweight"
    f.fight_weight_class = "Middleweight"
    f.organization = "UFC"
    f.room = "ufc"
    f.promotion_tier = 10
    f.story_flags = {"ufc_signed": True}
    f.org_contract = {"org": "UFC", "fights_left": 5, "fights_total": 6, "weeks_left": 40, "exclusive": True}
    f.fight_history = [
        {"event": "Balkan Combat", "result": "Win"},
        {"event": "UFC", "result": "Win"},
    ]
    f.age = 21
    f.school_status = "none"
    return f


def test_set_room_does_not_rename_org():
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    orgs.sign_org(f, "Balkan Combat")
    assert f.organization == "Balkan Combat"
    booking.set_room(f, "national")
    assert f.organization == "Balkan Combat", f.organization
    assert f.room == "national"
    return "set_room keeps named org"


def test_repair_walks_back_early_ufc():
    raw = _kamil_like().to_dict()
    raw["fight_history"] = [{"event": "UFC", "result": "Win", "opponent": "X"}]
    out = identity.repair_save(raw)
    assert out["organization"] == "Balkan Combat", out["organization"]
    assert out["story_flags"].get("early_ufc_walked_back") is True
    assert out["bodyfat"] >= 12.0, out["bodyfat"]
    assert out["walking_weight"] > 79.9, out["walking_weight"]
    return "Kamil-like save repaired to Balkan + body fill"


def test_tick_body_fills_out_of_camp():
    f = _kamil_like()
    f.organization = "Balkan Combat"
    f.camp_active = False
    f.camp_for_bout = 0
    f.meal_plan = "Comfort Food"
    start_w, start_bf = f.walking_weight, f.bodyfat
    cut.tick_body(f)
    assert f.walking_weight > start_w, (start_w, f.walking_weight)
    assert f.bodyfat >= 12.0, f.bodyfat
    return "out of camp walk %.1f -> %.1f  bf %.1f" % (start_w, f.walking_weight, f.bodyfat)


def test_plan_json_is_used():
    n = cut.plan_weight_change("Fight Camp Clean")
    assert n < 0, n
    n2 = cut.plan_weight_change("Cheat Meal")
    assert n2 > 0, n2
    return "plan deltas %s / %s" % (n, n2)


def test_display_org_ignores_tier_labels():
    f = _kamil_like()
    identity.sync(f)
    # still stamped UFC in this live object; sync keeps named contract org
    assert identity.display_org(f) in ("UFC", "Balkan Combat")
    f.org_contract = {"org": "Balkan Combat", "fights_left": 3, "weeks_left": 20}
    f.organization = "Regional FC"
    assert identity.canonical_org(f) == "Balkan Combat"
    identity.sync(f)
    assert f.organization == "Balkan Combat"
    return "canonical org wins over room label"


def test_no_ufc_from_local_room_label():
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.pro_record = [3, 0, 0]
    booking.set_room(f, "local")
    assert "UFC" not in orgs.eligible_orgs(f)
    return "local band cannot see UFC"


def main():
    tests = [
        test_set_room_does_not_rename_org,
        test_repair_walks_back_early_ufc,
        test_tick_body_fills_out_of_camp,
        test_plan_json_is_used,
        test_display_org_ignores_tier_labels,
        test_no_ufc_from_local_room_label,
    ]
    for t in tests:
        print("PASS", t.__name__, t())
    print("ALL 1.13 OK")


if __name__ == "__main__":
    main()
