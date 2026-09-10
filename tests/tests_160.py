"""1.18 record sync + fight still runs."""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import record
from mma_legend.engine.fight import simulate_fight
from mma_legend.engine.rules import MMARuleset


def test_pro_rows_only():
    f = Fighter.new_player("U", "M", country_by_name("Bulgaria"), "Boxing")
    f.pro_debut = True
    f.pro_record = [17, 5, 0]
    f.fight_history = [
        {"opponent": "A", "result": "Win", "event": "Balkan Combat", "sport": "mma"},
        {"opponent": "B", "result": "Win", "event": "Cage Warriors", "sport": "mma"},
        {"opponent": "C", "result": "Loss", "event": "Cage Warriors", "sport": "mma"},
        {"opponent": "D", "result": "Loss", "event": "Local no-gi", "sport": "grappling"},
        {"opponent": "E", "result": "Win", "event": "", "sport": "mma"},
    ]
    rec = record.sync(f)
    assert rec == [2, 1, 0], rec
    assert f.story_flags["pro_fights_done"] == 3
    return "pro 2-1 from named orgs"


def test_repair_dict():
    d = {
        "pro_record": [17, 5, 0],
        "fight_history": [
            {"result": "Win", "event": "Cage Warriors", "sport": "mma"},
            {"result": "Loss", "event": "Cage Warriors", "sport": "mma"},
        ],
        "story_flags": {"pro_fights_done": 22},
    }
    out = record.repair_dict(d)
    assert out["pro_record"] == [1, 1, 0]
    assert out["story_flags"]["pro_fights_done"] == 2
    return "repair overwrites drift"


def test_fight_still_ends():
    a = Fighter.new_player("A", "M", country_by_name("USA"), "Boxing")
    b = Fighter.new_npc("B", country_by_name("USA"))
    b.style = "Wrestling"
    out = simulate_fight(a, b, MMARuleset(amateur=True), gameplan="Balanced")
    assert out is not None and out.method
    return "fight %s" % out.method


def main():
    for t in (test_pro_rows_only, test_repair_dict, test_fight_still_ends):
        print("PASS", t.__name__, t())
    print("ALL 1.18 OK")


if __name__ == "__main__":
    main()
