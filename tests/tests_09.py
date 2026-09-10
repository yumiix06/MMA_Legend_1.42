"""0.9.0 ladder / cards / perks."""
from __future__ import annotations

from mma_legend import booking, perks
from mma_legend.data import country_by_name
from mma_legend.models import Fighter


def test_no_skip_ufc():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.pro_debut = True
    f.pro_record = [3, 0, 0]
    booking.set_room(f, "local")
    assert booking.maybe_promote(f) == "regional"
    assert booking.current_room(f) != "ufc"
    f.pro_record = [5, 0, 0]
    assert booking.maybe_promote(f) == "national"
    assert f.organization != "UFC"
    print("PASS no skip to UFC from local wins")


def test_card_and_tag():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.pro_debut = True
    booking.set_room(f, "local")
    off = booking.build_offer(f)
    assert "card" in off and len(off["card"]) >= 2
    assert off["tag"] in ("even", "trap", "tune-up", "short notice", "catchweight", "rematch")
    assert "MAIN" in off["card"][-1]
    print("PASS card", off["tag"], "lines", len(off["card"]))


def test_auto_perk():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.story_flags = {"decision_wins": 3}
    perks.evaluate(f)
    assert "grinder" in f.perks
    f.story_flags["r1_finishes"] = 2
    perks.evaluate(f)
    assert len(f.perks) <= 3
    print("PASS auto perks", f.perks)


def test_dwcs_to_ufc():
    """A DWCS win hook must not stamp UFC by itself. Grade + resolve does."""
    from mma_legend import dwcs, orgs
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.pro_debut = True
    booking.set_room(f, "dwcs")
    booking.after_dwcs_win(f)
    assert booking.current_room(f) != "ufc"
    assert (f.organization or "") != "UFC"
    dwcs.resolve(f, type("O", (), {
        "winner": "player", "method": "KO", "finish_label": "KO",
        "end_period": 1, "f_stats": None, "o_stats": None,
    })(), console=None)
    assert f.organization == "UFC"
    print("PASS DWCS finish resolve -> UFC; hook alone does not")


def main():
    test_no_skip_ufc()
    test_card_and_tag()
    test_auto_perk()
    test_dwcs_to_ufc()
    print("ALL 0.9 CHECKS OK")


if __name__ == "__main__":
    main()
