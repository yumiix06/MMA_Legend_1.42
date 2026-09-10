"""1.1 People Booking tests. Run from parent:
python3 -m mma_legend.tests_11
or: cd this folder && python3 -c "import tests_11; tests_11.main()"
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from mma_legend import booking, orgs, people, events, perks, persistence
from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


class Quiet:
    def header(self, *a, **k): pass
    def print(self, *a, **k): pass
    def gold(self, *a, **k): pass
    def good(self, *a, **k): pass
    def warn(self, *a, **k): pass
    def info(self, *a, **k): pass
    def table(self, *a, **k): pass
    def read_pause(self, *a, **k): pass
    def ask(self, *a, **k): return "X"
    def pause(self, *a, **k): pass
    def auto_pause(self, *a, **k): pass
    def milestone(self, *a, **k): pass


def _pro(name="P"):
    c = country_by_name("USA")
    f = Fighter.new_player(name, "B", c, "Boxing")
    f.pro_debut = True
    f.pro_record = [3, 0, 0]
    booking.set_room(f, "local")
    return f


def test_inbox_offer_shape():
    f = _pro()
    pool = FighterPool()
    pool.generate_world(40, 20)
    off = orgs.make_offer(f, "LFA", pool=pool)
    for key in ("card", "tag", "opponent_id", "date_week", "matchmaker_id", "purse_win", "why"):
        assert key in off, key
    assert off["card"] and "MAIN" in off["card"][-1]
    booking.set_booked(f, off)
    assert f.booked_fight["org"] == "LFA"
    assert f.booked_fight.get("opponent_id")
    print("PASS inbox offer shape", off["tag"], off.get("matchmaker_id"))


def test_pro_c_is_fight_route():
    f = _pro()
    from mma_legend.app import _actions_for
    keys = [r[0] for r in _actions_for(f)]
    assert "D" not in keys
    labels = [r[2] for r in _actions_for(f)]
    assert "Fight" in labels
    off = booking.build_offer(f)
    assert off.get("matchmaker_id")
    print("PASS pro C is fight route", off["matchmaker_id"])


def test_no_skip_ufc():
    f = _pro()
    f.pro_record = [3, 0, 0]
    booking.set_room(f, "local")
    names = orgs.eligible_orgs(f)
    assert "UFC" not in names, names
    f.pro_record = [12, 0, 0]
    f.fame = 40
    booking.set_room(f, "local")
    names = orgs.eligible_orgs(f)
    assert "UFC" not in names, names
    booking.set_room(f, "dwcs")
    names = orgs.eligible_orgs(f)
    assert "UFC" in names
    print("PASS no skip UFC from local")


def test_pool_opponent_persists(tmp_path=None):
    f = _pro()
    pool = FighterPool()
    c = country_by_name("USA")
    npc = Fighter.new_npc("Keep Me", c)
    npc.fid = "npc_keep"
    npc.weight_class = f.weight_class
    npc.pro_debut = True
    npc.pro_record = [4, 1, 0]
    npc.active = True
    pool.fighters.append(npc)
    pool.next_id = 2000
    off = booking.build_offer(f, pool=pool, org_id="LFA")
    # Force the known fid onto the offer so persist is testable
    off["opponent"] = npc
    off["opponent_id"] = npc.fid
    booking.set_booked(f, off)
    from mma_legend.fights import fight_result
    # quiet sim
    f.fight_details = "Quick"
    fight_result(Quiet(), f, npc, 200, pool)
    live = pool.get_by_id("npc_keep")
    assert live is not None
    rec = live.pro_record
    assert rec[0] + rec[1] + rec[2] >= 6
    path = Path("/tmp/mma11_test_save.json")
    persistence.save_game(Quiet(), f, pool, path)
    loaded = persistence.load_game(Quiet(), path)
    assert loaded
    f2, p2 = loaded
    again = p2.get_by_id("npc_keep")
    assert again is not None
    print("PASS pool opponent persists", again.pro_record)


def test_rival_by_id():
    f = _pro()
    pool = FighterPool()
    c = country_by_name("USA")
    npc = Fighter.new_npc("Rival Man", c)
    npc.fid = "npc_rival"
    pool.fighters.append(npc)
    f.rival = "Rival Man"
    f.rival_id = "npc_rival"
    path = Path("/tmp/mma11_rival.json")
    persistence.save_game(Quiet(), f, pool, path)
    loaded = persistence.load_game(Quiet(), path)
    f2, p2 = loaded
    assert f2.rival_id == "npc_rival"
    assert p2.get_by_id("npc_rival") is not None
    print("PASS rival by id")


def test_decline_cools_matchmaker():
    f = _pro()
    org = "LFA"
    mm = people.matchmaker_for(org)
    start = people.rapport(f, mm.id)
    people.cool_matchmaker(f, org, -8)
    people.cool_matchmaker(f, org, -8)
    now = people.rapport(f, mm.id)
    assert now < start
    print("PASS decline cools matchmaker", start, "->", now)


def test_event_ban_00():
    f = Fighter.new_player("Kid", "B", country_by_name("USA"), "Boxing")
    ctx = events.context_pack(f)
    bad = []
    from mma_legend import data
    for evt in list(data.EVENT_DATABASE) + list(data.EVENTS_V06) + list(data.EVENTS_V07) + list(data.EVENTS_V08):
        if not events.eligible(f, evt, ctx):
            continue
        title = (evt.get("title") or "").lower()
        blob = title + " " + (evt.get("description") or "").lower()
        for w in ("podcast", "interview", "nightclub", "fight offer", "national team invitation"):
            if w in blob:
                bad.append(evt.get("title"))
    assert not bad, bad
    print("PASS event ban 0-0")


def test_manager_weights():
    f = Fighter.new_player("Kid", "B", country_by_name("USA"), "Boxing")
    f.fame = 0
    hits = 0
    n = 400
    for _ in range(n):
        picks = people.manager_candidates(f, n=3)
        if any(m.quirk == "brand" for m in picks):
            hits += 1
    rate = hits / n
    assert rate < 0.25, rate
    print("PASS manager weights brand rate", round(rate, 3))


def test_auto_perk_still():
    f = _pro()
    f.story_flags = {"decision_wins": 3}
    perks.evaluate(f)
    assert "grinder" in f.perks
    print("PASS perks still grant")


def main():
    random.seed(11)
    test_inbox_offer_shape()
    test_pro_c_is_fight_route()
    test_no_skip_ufc()
    test_pool_opponent_persists()
    test_rival_by_id()
    test_decline_cools_matchmaker()
    test_event_ban_00()
    test_manager_weights()
    test_auto_perk_still()
    print("ALL 1.1 CHECKS OK")


if __name__ == "__main__":
    main()
