"""1.2 world + combat + ladder tests."""
from __future__ import annotations

from mma_legend import booking, orgs, people, events
from mma_legend.data import country_by_name
from mma_legend.engine import simulate_fight, MMARuleset, GrapplingRuleset
from mma_legend.engine.fight import action_from_label
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


def test_action_maps_label():
    assert action_from_label("Go upstairs with a head kick", "stand")[0] == "head_kick"
    assert action_from_label("Hunt the submission", "ground")[0] == "rear_naked"
    assert action_from_label("Keep chopping the leg", "stand")[0] == "low_kick"
    print("PASS action maps label")


def test_no_ko_in_grappling():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "BJJ")
    o = Fighter.new_npc("O", c)
    f.energy = o.energy = 90
    f.fight_details = "Quick"
    for _ in range(8):
        out = simulate_fight(f, o, GrapplingRuleset(), gameplan="Wrestle-heavy", console=None)
        assert out.method != "KO", out.method
        strikes = [e for e in out.log if e.action_id in ("jab", "cross", "hook", "low_kick", "head_kick")]
        assert not strikes
    print("PASS no KO / punches in grappling")


def test_amateur_not_fed_vet_pro():
    c = country_by_name("USA")
    kid = Fighter.new_player("Kid", "B", c, "Boxing")
    vet = Fighter.new_npc("Volkov", c)
    vet.pro_debut = True
    vet.pro_record = [18, 2, 1]
    vet.active = True
    assert booking.opponent_fits(kid, vet) is False
    peer = Fighter.new_npc("Local Am", c)
    peer.pro_debut = False
    peer.pro_record = [0, 0, 0]
    peer.amateur_record = [3, 1, 0]
    peer.active = True
    # Deterministic fixture: new_npc randomizes bodyweight, while
    # opponent_fits correctly rejects cross-division matchmaking.
    peer.weight_class = kid.weight_class
    peer.fight_weight_class = kid.fight_weight_class
    from mma_legend import constants as C
    for s in C.SKILLS:
        setattr(peer, s, getattr(kid, s))
    assert booking.opponent_fits(kid, peer) is True
    print("PASS amateur not fed vet pro")


def test_debut_orgs_are_regional():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.pro_debut = True
    f.pro_record = [0, 0, 0]
    f.fame = 4
    booking.set_room(f, "local")
    names = orgs.eligible_orgs(f)
    for banned in ("PFL", "Bellator", "KSW", "UFC"):
        assert banned not in names, names
    print("PASS debut orgs regional", names)


def test_blue_belt_once():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "BJJ")
    f.story_flags = {"belt_ready": True}
    evt = {"id": "v8c_05", "title": "Blue belt test", "require": {"flag": "belt_ready"}, "trigger": {"type": "conditional"}}
    ctx = events.context_pack(f)
    assert events.eligible(f, evt, ctx)
    f.bjj_belt = "blue"
    f.story_flags["done_event_v8c_05"] = True
    assert events.eligible(f, evt, ctx) is False
    print("PASS blue belt once")


def test_coach_is_person():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Wrestling")
    coach = people.gym_coach(f) or people.ensure_gym_coach(f)
    assert coach is not None
    assert coach.role == "coach"
    assert f.story_flags.get("coach_id") == coach.id
    print("PASS coach is person", coach.name)


def test_rematch_not_a_vet():
    from mma_legend import fights
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.amateur_record = [4, 2, 0]
    f.pro_debut = False
    pool = FighterPool()
    pool.generate_world(40, 10)
    vet = Fighter.new_npc("Emre Kobayashi", c)
    vet.fid = "npc_emre"
    vet.pro_debut = True
    vet.pro_record = [15, 2, 1]
    vet.weight_class = f.weight_class
    pool.fighters.append(vet)
    f.rival = "Emre Kobayashi"
    f.rival_id = "npc_emre"
    f.rivalries = [{"name": "Emre Kobayashi", "fid": "npc_emre", "heat": 40,
                    "am": [3, 3, 0], "pro": [15, 2, 1], "pro_debut": True}]
    preview = fights._rebuild_rival(f, pool)
    assert booking.opponent_fits(f, preview)
    assert not preview.pro_debut
    assert preview.pro_record[0] == 0
    print("PASS rematch rebuilt as amateur peer")


def test_rankings_champ_not_numbered():
    pool = FighterPool()
    pool.generate_world(60, 20)
    pool.update_rankings()
    for wc, numbered in pool.rankings.items():
        champ = pool.champions.get(wc)
        if champ:
            assert champ not in numbered
    print("PASS champ sits in C slot, not #1")


def test_org_card_has_intent():
    pool = FighterPool()
    pool.generate_world(80, 20)
    pool.news = []
    pool._simulate_pro_fights()
    assert pool.news, "expected ticker"
    assert any("[" in line and "]" in line for line in pool.news)
    print("PASS org card has intent", pool.news[0])


def main():
    test_action_maps_label()
    test_no_ko_in_grappling()
    test_amateur_not_fed_vet_pro()
    test_debut_orgs_are_regional()
    test_blue_belt_once()
    test_coach_is_person()
    test_rematch_not_a_vet()
    test_rankings_champ_not_numbered()
    test_org_card_has_intent()
    print("ALL 1.2 CHECKS OK")


if __name__ == "__main__":
    main()
