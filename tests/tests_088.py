"""0.8.8 acceptance."""
from __future__ import annotations

from mma_legend import booking
from mma_legend import constants as C
from mma_legend.data import country_by_name
from mma_legend.engine import positions as P
from mma_legend.engine.fight import _tech_options
from mma_legend.engine import simulate_fight
from mma_legend.engine.rules import MMARuleset
from mma_legend.fights import get_weight_class_options, _pick_weight_option
from mma_legend.models import Fighter


def _boxer():
    c = country_by_name("USA")
    return Fighter.new_player("P", "B", c, "Boxing")


def test_standing_no_guillotine():
    """Guillotine is a clinch / closed-guard submission. It must never be
    legal, or offered, while standing."""
    f = _boxer()
    assert "guillotine" not in P.legal_actions("stand", False)
    opts = _tech_options(f, "stand", amateur=False, grappling_only=False)
    names = [o[0] for o in opts]
    assert "Guillotine" not in names, names
    print("PASS standing menu no guillotine", names[:6])


def test_weight_letter():
    f = _boxer()
    f.walking_weight = 84
    f.weight = 84
    opts = get_weight_class_options(f)
    labels = [o[2] for o in opts]
    assert any("77" in x or "WW" in x for x in labels), labels
    picked = _pick_weight_option("a", opts)
    assert picked is not None
    print("PASS weight A and 77 option", labels)


def test_turn_pro_room():
    f = _boxer()
    f.pro_debut = True
    booking.set_room(f, "local")
    assert f.room == "local"
    assert not booking.can_use_ranked_picker(f)
    print("PASS local room no UFC picker")


def test_local_purse():
    f = _boxer()
    booking.set_room(f, "local")
    wins = [booking.purse_for(f, "local")[0] for _ in range(20)]
    assert min(wins) >= 250 and max(wins) <= 460, wins
    show = booking.purse_for(f, "local")[1]
    assert show >= 40
    print("PASS local purse", min(wins), max(wins), "show", show)


def test_known_tech():
    f = _boxer()
    assert "Jab" in f.techniques
    assert "guillotine" in P.legal_actions("clinch", False)
    assert "guillotine" in P.legal_actions("closed_guard", False)
    assert "guillotine" not in P.legal_actions("mount", False)
    opts = _tech_options(f, "closed_guard", amateur=False, grappling_only=False)
    names = [o[0] for o in opts]
    assert "Guillotine" not in names, names
    print("PASS boxer does not know guillotine; position legality holds")


def test_finish_clock():
    f = _boxer()
    o = Fighter.new_npc("O", country_by_name("USA"))
    booking.apply_kit(o, "Boxing")
    out = None
    for _ in range(12):
        out = simulate_fight(f, o, MMARuleset(True), "Aggressive")
        if out.winner != "draw":
            break
    assert out is not None
    if out.finish_label:
        assert out.clock.startswith("R") or out.end_period >= 1
    print("PASS fight ran clock=%s method=%s" % (out.clock, out.method))


def test_save_skips_booked():
    f = _boxer()
    opp = _boxer()
    opp.name = "Other"
    f.booked_fight = {"opponent": opp, "date_week": 12, "purse_win": 300}
    d = f.to_dict()
    assert d["booked_fight"]["opponent_snap"]["name"] == "Other"
    g = type(f).from_dict(d)
    assert g.booked_fight["opponent"].name == "Other"
    print("PASS booked_fight packed without live Fighter")


def main():
    test_standing_no_guillotine()
    test_weight_letter()
    test_turn_pro_room()
    test_local_purse()
    test_known_tech()
    test_finish_clock()
    test_save_skips_booked()
    print("ALL 0.8.8 CHECKS OK")


if __name__ == "__main__":
    main()
