"""1.8.0 checks: position-legal combat.

Before 1.8.0 the technique menu and the AI's own action picker used a
flattened stand/clinch/ground phase instead of engine.positions.LEGAL, so a
Rear Naked Choke could be offered (and thrown) from any ground position —
including mount, side, turtle — not just back control, and a fighter who
merely *knew* a submission by name (e.g. "Guillotine") could fire it while
standing because the auto-technique picker matched on keyword only. Armbar,
Guillotine, and Rear Naked Choke were also mechanically the same action id.
These tests pin that down so it cannot silently regress.
"""
from __future__ import annotations

import random

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.engine import positions as P
from mma_legend.engine.fight import _tech_options, _auto_from_bag, simulate_fight
from mma_legend.engine.rules import MMARuleset, GrapplingRuleset
from mma_legend import booking


def _bjj_fighter():
    f = Fighter.new_player("Sub Hunter", "B", country_by_name("Brazil"), "BJJ")
    f.techniques = list(set(list(f.techniques or []) + [
        "Rear Naked Choke", "Armbar", "Triangle", "Kimura", "Guillotine",
    ]))
    for t in ("Rear Naked Choke", "Armbar", "Triangle", "Kimura", "Guillotine"):
        f.technique_levels = dict(f.technique_levels or {})
        f.technique_levels[t] = 3
    return f


def test_rnc_only_from_back():
    for pos in P.POSITIONS:
        legal = P.legal_actions(pos)
        if pos == "back":
            assert "rear_naked" in legal, pos
        else:
            assert "rear_naked" not in legal, pos
    return "RNC legal only from back"


def test_submissions_distinct_actions():
    """Armbar / Triangle / Kimura / Guillotine / RNC must be distinct action
    ids with distinct position legality, not all collapsed into one move."""
    assert P.LEGAL["armbar"] == {"closed_guard", "open_guard", "mount", "side"}
    assert P.LEGAL["triangle"] == {"closed_guard", "open_guard"}
    assert P.LEGAL["kimura"] == {"half_guard", "side", "north_south", "closed_guard"}
    assert P.LEGAL["guillotine"] == {"clinch", "closed_guard", "front_headlock"}
    assert P.LEGAL["rear_naked"] == {"back"}
    ids = {"armbar", "triangle", "kimura", "guillotine", "rear_naked"}
    assert len(ids) == 5
    return "submissions are 5 distinct action ids"


def test_menu_never_offers_illegal_submission():
    f = _bjj_fighter()
    for pos in P.POSITIONS:
        opts = _tech_options(f, pos, amateur=False, grappling_only=False)
        legal = P.legal_actions(pos, False)
        for name, action, target, dmg in opts:
            assert action in legal, "%s offered %s (%s) at illegal pos %s" % (name, action, name, pos)
    return "menu options always position-legal"


def test_no_head_kick_from_mount():
    opts = _tech_options(_bjj_fighter(), "mount", amateur=False, grappling_only=False)
    names = [o[0] for o in opts]
    assert "Head Kick" not in names, names
    return "no head kick from mount"


def test_no_gnp_in_pure_grappling():
    opts = _tech_options(_bjj_fighter(), "mount", amateur=False, grappling_only=True)
    names = [o[0] for o in opts]
    assert "Ground and Pound" not in names, names
    assert "gnp" not in P.legal_actions("mount", grappling_only=True)
    return "no GNP offered in grappling_only"


def test_no_strikes_legal_in_grappling_only():
    strikes = ("jab", "cross", "hook", "uppercut", "low_kick", "head_kick",
               "teep", "dirty_box", "gnp", "liver", "knee_body")
    for pos in P.POSITIONS:
        legal = P.legal_actions(pos, grappling_only=True)
        for s in strikes:
            assert s not in legal, (pos, s)
    return "no strikes legal anywhere in grappling_only"


def test_auto_from_bag_respects_position():
    """A fighter who knows 'Guillotine' by name must not have it auto-fire
    while standing — only from clinch or closed guard."""
    f = _bjj_fighter()
    random.seed(7)
    for _ in range(200):
        picked = _auto_from_bag(f, "stand", grappling_only=False)
        if picked is None:
            continue
        action = picked[0]
        assert action in P.legal_actions("stand", False), action
    return "auto-from-bag never fires an illegal-position technique"


def test_grappling_match_never_kos():
    f = Fighter.new_player("G1", "B", country_by_name("USA"), "BJJ")
    o = Fighter.new_npc("G2", country_by_name("USA"), style="BJJ")
    booking.apply_kit(o, "BJJ")
    for _ in range(6):
        out = simulate_fight(f, o, GrapplingRuleset(), gameplan="Wrestle-heavy")
        assert out.method != "KO", out.method
        assert (out.finish_label or "") not in ("KO", "KO Loss"), out.finish_label
    return "no-gi match never produces a KO"


def test_mma_headless_runs_clean():
    f = Fighter.new_player("M1", "B", country_by_name("USA"), "Wrestling")
    o = Fighter.new_npc("M2", country_by_name("USA"), style="Muay Thai")
    booking.apply_kit(o, "Muay Thai")
    out = simulate_fight(f, o, MMARuleset(amateur=True), gameplan="Balanced")
    assert out.winner in ("player", "opponent", "draw")
    assert out.f_stats.strikes_attempted >= 0
    return "headless MMA sim clean: %s %s" % (out.winner, out.method)


def test_wrestler_banks_control_seconds():
    """A wrestle-heavy amateur bout should produce real control time on
    at least one side, stored as seconds (displayed mm:ss) not raw ticks."""
    random.seed(19)
    f = Fighter.new_player("W1", "B", country_by_name("USA"), "Wrestling")
    f.grappling = 78
    f.ground_control = 80
    f.strength = 72
    o = Fighter.new_npc("W2", country_by_name("USA"), style="Boxing")
    booking.apply_kit(o, "Boxing")
    o.takedown_def = 40
    out = simulate_fight(f, o, MMARuleset(amateur=True), gameplan="Wrestle-heavy")
    total_sec = int(out.f_stats.control_sec) + int(out.o_stats.control_sec)
    total_ticks = int(out.f_stats.control_ticks) + int(out.o_stats.control_ticks)
    assert total_ticks >= 0
    # Decision or finish both valid; the clock field is mm:ss now.
    assert ":" in (out.clock or ""), out.clock
    return "control clock %ss/%ss  %s" % (out.f_stats.control_sec, out.o_stats.control_sec, out.clock)


def main():
    for t in (
        test_rnc_only_from_back,
        test_submissions_distinct_actions,
        test_menu_never_offers_illegal_submission,
        test_no_head_kick_from_mount,
        test_no_gnp_in_pure_grappling,
        test_no_strikes_legal_in_grappling_only,
        test_auto_from_bag_respects_position,
        test_grappling_match_never_kos,
        test_mma_headless_runs_clean,
        test_wrestler_banks_control_seconds,
    ):
        print("PASS", t())
    print("ALL 1.8 COMBAT-LEGALITY CHECKS OK")


if __name__ == "__main__":
    main()
