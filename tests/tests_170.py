"""1.19 damage feedback, signatures, judges."""
from __future__ import annotations

from types import SimpleNamespace

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.engine import fight as F
from mma_legend.engine import scoring as SC
from mma_legend.engine.fight import simulate_fight
from mma_legend.engine.rules import MMARuleset
from mma_legend.engine.positions import legal_actions


def test_hurt_legs_kill_the_double():
    who = SimpleNamespace(damage={"legs": 20, "body": 0, "head": 0, "eyes": 0, "cuts": 0})
    clean = SimpleNamespace(damage={})
    assert F._part_mod(who, "double_leg") < F._part_mod(clean, "double_leg")
    assert F._prey_mod(who, "double_leg") > 1.0
    return "legs punish the shooter, help the wrestler attacking them"


def test_body_slows_hooks():
    who = SimpleNamespace(damage={"legs": 0, "body": 16, "head": 0, "eyes": 0, "cuts": 0})
    clean = SimpleNamespace(damage={})
    assert F._part_mod(who, "hook") < 0.9
    assert F._part_mod(clean, "hook") == 1.0
    assert F._prey_mod(who, "liver") > 1.0
    return "liver money"


def test_signature_on_the_back():
    who = SimpleNamespace(techniques=["Rear Naked Choke", "Armbar"])
    legal = legal_actions("back", False, "top")
    hits = F._signature_acts(who, "back", "top", legal)
    assert "rear_naked" in hits
    return "RNC is a moment from the back"


def test_judges_can_split():
    a = SimpleNamespace(knockdowns=0, strikes_landed=12, submission_attempts=0,
                        head_landed=6, body_landed=3)
    b = SimpleNamespace(knockdowns=0, strikes_landed=11, submission_attempts=0,
                        head_landed=5, body_landed=4)
    cards = []
    for lean in ("damage", "control", "volume"):
        cards.append(SC.score_round(a, b, 6, 5, 2, 2, lean=lean))
    # Not asserting a split every seed — only that each card is a legal 10-point pair.
    for sa, sb in cards:
        assert sa + sb in (19, 20, 18, 17) or (sa, sb) == (10, 10)
        assert 7 <= sa <= 10 and 7 <= sb <= 10
    return "cards %s" % cards


def test_fight_runs_with_hurt_body():
    a = Fighter.new_player("A", "M", country_by_name("USA"), "Boxing")
    b = Fighter.new_npc("B", country_by_name("USA"))
    a.damage = {"legs": 12, "body": 10, "head": 4, "eyes": 2, "cuts": 1, "total": 29}
    b.style = "Wrestling"
    b.techniques = ["Double Leg", "Trip"]
    out = simulate_fight(a, b, MMARuleset(amateur=True), gameplan="Balanced")
    assert out.method
    return out.method


def main():
    for t in (test_hurt_legs_kill_the_double, test_body_slows_hooks,
              test_signature_on_the_back, test_judges_can_split,
              test_fight_runs_with_hurt_body):
        print("PASS", t.__name__, t())
    print("ALL 1.19 OK")


if __name__ == "__main__":
    main()
