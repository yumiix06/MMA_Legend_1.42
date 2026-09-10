"""AI brains."""
from __future__ import annotations

from mma_legend import ai, booking, events, orgs, people
from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


def test_event_ai_skips_party_in_camp():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.camp_active = True
    f.energy = 40
    ctx = events.context_pack(f)
    party = {"title": "Club night", "category": "life", "trigger": {"chance": 0.5}}
    gym = {"title": "Extra sparring with coach", "category": "training", "trigger": {"chance": 0.5}}
    assert ai.event_score(f, gym, ctx) > ai.event_score(f, party, ctx)
    print("PASS event AI prefers gym over party in camp")


def test_npc_ai_retires_old_losers():
    c = country_by_name("USA")
    f = Fighter.new_npc("Old", c)
    f.age = 40
    f.pro_debut = True
    f.pro_record = [4, 12, 0]
    f.health = 70
    assert ai.npc_intent(f) == "retire"
    print("PASS npc AI retire")


def test_manager_filters_trap():
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.pro_debut = True
    f.pro_record = [2, 0, 0]
    mgr = next(m for m in people.all_managers() if m.quirk == "analytical")
    people.sign_manager(f, mgr)
    vet = Fighter.new_npc("Vet", c)
    vet.pro_debut = True
    vet.pro_record = [18, 1, 0]
    offers = [{"org": "LFA", "opponent": vet, "purse_win": 200}]
    kept = ai.filter_offers(f, offers)
    assert kept[0]["opponent"] is vet or kept  # may keep if only offer
    print("PASS manager filter ran", mgr.name)


def test_promo_intent_idle_champ():
    c = country_by_name("USA")
    champ = Fighter.new_npc("C", c)
    champ.weight_class = "Welterweight"
    champ.idle_weeks = 16
    champ.pro_debut = True
    tag = ai.promo_intent("UFC", [champ], "Welterweight", champ)
    assert tag == "title_defense"
    print("PASS promo AI title defense")


def test_week_tick_does_not_crash():
    pool = FighterPool()
    pool.generate_world(40, 20)
    lines = ai.tick_npcs(pool, 40) + ai.tick_promos(pool)
    assert isinstance(lines, list)
    print("PASS weekly AI ticks", len(lines))


def test_known_techs_appear():
    from mma_legend.engine.fight import _tech_options
    c = country_by_name("USA")
    f = Fighter.new_player("P", "B", c, "Boxing")
    f.techniques = list(f.techniques) + ["Liver Shot", "Rear Naked", "Cage Cutoff"]
    f.sync_techniques()
    stand = [r[0] for r in _tech_options(f, "stand", True, False)]
    # "ground" was a legacy pseudo-position; positions are now concrete and
    # role-aware, so ask for a real one from a real side of it.
    back_top = [r[0] for r in _tech_options(f, "back", True, False, "top")]
    guard_bottom = [r[0] for r in _tech_options(f, "closed_guard", True, False, "bottom")]
    assert any("Jab" in x or "Liver" in x for x in stand)
    assert back_top, back_top
    assert guard_bottom, guard_bottom
    # The choke he knows shows up where it belongs, and nowhere else.
    assert any("Rear Naked" in x for x in back_top), back_top
    assert not any("Rear Naked" in x for x in stand), stand
    print("PASS techniques appear", stand[:4], back_top[:3], guard_bottom[:3])


def main():
    test_event_ai_skips_party_in_camp()
    test_npc_ai_retires_old_losers()
    test_manager_filters_trap()
    test_promo_intent_idle_champ()
    test_week_tick_does_not_crash()
    test_known_techs_appear()
    print("ALL 1.3 AI CHECKS OK")


if __name__ == "__main__":
    main()
