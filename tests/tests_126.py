"""1.26 combat reconstruction release gates."""
from __future__ import annotations

import copy
import random

from mma_legend import constants as C, data
from mma_legend.models import Fighter
from mma_legend.techniques import CONCEPT_SKILLS, REACTION_TECHNIQUES
from mma_legend.engine import positions as P
from mma_legend.engine.fight import _tech_options, simulate_fight
from mma_legend.engine.rules import (
    MMARuleset, GrapplingRuleset, BoxingRuleset, KickboxingRuleset, WrestlingRuleset,
)


def _fighter(name="A", style="MMA"):
    return Fighter.new_npc(name, data.country_by_name("USA"), style=style)


def test_skill_sheet_and_reach_are_real_fields():
    f = _fighter()
    assert len(C.SKILLS) == len(C.SKILL_WEIGHTS) == 15
    for stat in ("striking_def", "submission_def", "distance_management"):
        assert stat in C.SKILLS and 1 <= getattr(f, stat) <= 100
    assert 150 <= f.reach <= 218 and f.stance in ("Orthodox", "Southpaw")
    return "15 weighted skills plus persistent reach/stance initialize on fighters"


def test_concepts_migrate_once_and_leave_coach_data():
    names = {row["name"] for row in data.TECHNIQUES_DB}
    assert not names.intersection(CONCEPT_SKILLS)
    f = _fighter()
    f.techniques += ["Distance Management", "Boxing Defense"]
    f.technique_levels.update({"Distance Management": 5, "Boxing Defense": 3})
    before = f.distance_management, f.striking_def
    f.story_flags.pop("v126_concepts_migrated", None)
    f.sync_techniques()
    once = f.distance_management, f.striking_def
    f.sync_techniques()
    assert once == (before[0] + 3, before[1] + 2)
    assert once == (f.distance_management, f.striking_def)
    assert not set(f.techniques).intersection(CONCEPT_SKILLS)
    return "legacy concepts convert once into visible skills and cannot be taught"


def test_every_move_has_structured_metadata():
    assert data.TECHNIQUES_DB
    for row in data.TECHNIQUES_DB:
        assert row.get("role") in ("action", "reaction"), row
        if row["role"] == "reaction":
            assert row["name"] in REACTION_TECHNIQUES and row.get("action_id") is None
        else:
            assert row.get("action_id") and row.get("kind") in ("strike", "grappling", "submission")
    f = _fighter(style="Boxing")
    f.techniques += list(REACTION_TECHNIQUES)
    options = {name for pos in P.POSITIONS for name, *_ in _tech_options(f, pos, False, False)}
    assert not options.intersection(REACTION_TECHNIQUES)
    return "%d moves carry action/role metadata; reactions never become attack buttons" % len(data.TECHNIQUES_DB)


def test_expanded_position_graph_is_legal():
    for pos in ("open_guard", "front_headlock", "north_south", "leg_entanglement"):
        assert pos in P.POSITIONS and P.legal_actions(pos), pos
    assert P.apply_transition("stand", "snap_down")[0] == "front_headlock"
    assert P.apply_transition("open_guard", "leg_entry")[0] == "leg_entanglement"
    assert P.LEGAL["heel_hook"] == {"leg_entanglement"}
    assert P.LEGAL["north_south_choke"] == {"north_south"}
    return "open guard, front headlock, north-south and leg entanglement are connected"


def test_every_sport_enforces_its_actions():
    random.seed(1260)
    for rules in (MMARuleset(False), GrapplingRuleset(), BoxingRuleset(),
                  KickboxingRuleset(), WrestlingRuleset()):
        for _ in range(8):
            out = simulate_fight(_fighter("A"), _fighter("B"), rules)
            bad = [event.action_id for event in out.log if not rules.allows_action(event.action_id)]
            assert not bad, (rules.name, bad[:5])
    return "menus, AI and resolution share one action gate across all five sports"


def test_reach_and_distance_win_range_not_damage():
    random.seed(1261)
    controlled = conceded = 0
    for _ in range(50):
        a, b = _fighter("Long", "Boxing"), _fighter("Short", "Boxing")
        for who in (a, b):
            who.pro_debut = True
            who._fight_plan = {"range": "outside", "defense": "movement"}
        a.reach, b.reach = 205, 165
        a.distance_management, b.distance_management = 88, 25
        out = simulate_fight(a, b, BoxingRuleset())
        controlled += out.range_control["player"]
        conceded += out.range_control["opponent"]
    assert controlled > conceded * 1.45, (controlled, conceded)
    return "long, skilled fighter won %d-%d range contests without a damage multiplier" % (controlled, conceded)


def test_striking_defense_reduces_clean_connections():
    def rate(defense):
        landed = attempted = 0
        random.seed(1262)
        for _ in range(45):
            a, b = _fighter("Att", "Boxing"), _fighter("Def", "Boxing")
            a.striking = 65; a.distance_management = 55
            b.striking_def = defense; b.distance_management = 55
            out = simulate_fight(a, b, BoxingRuleset())
            landed += out.f_stats.strikes_landed
            attempted += out.f_stats.strikes_attempted
        return landed / max(1, attempted)
    low, high = rate(25), rate(85)
    assert high < low - 0.055, (low, high)
    return "striking defense lowers connection rate %.0f%% -> %.0f%%" % (low * 100, high * 100)


def main():
    for test in (
        test_skill_sheet_and_reach_are_real_fields,
        test_concepts_migrate_once_and_leave_coach_data,
        test_every_move_has_structured_metadata,
        test_expanded_position_graph_is_legal,
        test_every_sport_enforces_its_actions,
        test_reach_and_distance_win_range_not_damage,
        test_striking_defense_reduces_clean_connections,
    ):
        print("PASS", test())
    print("ALL 1.26 COMBAT RECONSTRUCTION CHECKS OK")


if __name__ == "__main__":
    main()
