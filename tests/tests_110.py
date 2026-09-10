"""1.10 checks: the Contender Series door and the unified NPC layer."""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import dwcs, npc, people, orgs


def _contender():
    f = Fighter.new_player("C", "B", country_by_name("USA"), "Wrestling")
    f.pro_debut = True
    f.pro_record = [6, 1, 0]
    f.recent_results = ["W", "W", "W"]
    f.fame = 15
    f.week = 90
    return f


class _Out:
    """Minimal stand-in for a FightOutcome."""
    def __init__(self, winner="player", method="Decision", finish=None,
                 end_period=3, f=None, o=None):
        from mma_legend.engine.fight import FightStats
        self.winner = winner
        self.method = method
        self.finish_label = finish
        self.end_period = end_period
        self.f_stats = f or FightStats()
        self.o_stats = o or FightStats()


# ---------------- DWCS door ----------------

def test_dwcs_needs_earning():
    f = Fighter.new_player("X", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.pro_record = [2, 0, 0]
    ok, why = dwcs.eligible(f)
    assert ok is False and "6 pro wins" in why, why
    # Amateurs never get the call.
    a = Fighter.new_player("A", "B", country_by_name("USA"), "Boxing")
    assert dwcs.eligible(a)[0] is False
    return "invitation must be earned"


def test_dwcs_eligible_contender():
    f = _contender()
    ok, why = dwcs.eligible(f)
    assert ok is True, why
    assert dwcs.invite_chance(f) > 0
    return "contender eligible, invite chance %.0f%%" % (dwcs.invite_chance(f) * 100)


def test_dwcs_streak_required():
    f = _contender()
    f.recent_results = ["W", "L", "W"]
    ok, why = dwcs.eligible(f)
    assert ok is False and "streak" in why, why
    return "a live streak is required"


def test_dwcs_win_is_not_enough():
    """The whole point of the show: a grinding decision earns nothing."""
    from mma_legend.engine.fight import FightStats
    fs, os_ = FightStats(), FightStats()
    fs.strikes_landed, os_.strikes_landed = 30, 28
    earned, label, why = dwcs.grade(_Out(f=fs, o=os_))
    assert earned is False, (label, why)
    assert "grind" in label or "grind" in why.lower()
    return "grinding decision earns no contract"


def test_dwcs_finish_signs_you():
    earned, label, why = dwcs.grade(
        _Out(method="KO", finish="KO", end_period=1))
    assert earned is True, (label, why)
    return "finish earns the contract: %s" % label


def test_dwcs_dominant_decision_signs_you():
    from mma_legend.engine.fight import FightStats
    fs, os_ = FightStats(), FightStats()
    fs.strikes_landed, os_.strikes_landed = 90, 20
    fs.knockdowns, os_.knockdowns = 2, 0
    fs.takedowns_landed, os_.takedowns_landed = 4, 0
    fs.control_ticks, os_.control_ticks = 30, 2
    earned, label, why = dwcs.grade(_Out(f=fs, o=os_))
    assert earned is True, (label, why)
    return "dominant decision earns it: %s" % label


def test_dwcs_loss_earns_nothing():
    earned, label, _why = dwcs.grade(_Out(winner="opponent"))
    assert earned is False and label == "loss"
    return "a loss ends the look"


def test_dwcs_resolve_signs_to_ufc():
    f = _contender()
    dwcs.resolve(f, _Out(method="KO", finish="KO", end_period=1))
    assert f.story_flags.get("ufc_signed") is True
    assert (f.organization or "") == "UFC"
    return "resolve signs the fighter to the UFC"


def test_dwcs_resolve_no_contract_returns_to_regional():
    from mma_legend.engine.fight import FightStats
    f = _contender()
    fs, os_ = FightStats(), FightStats()
    fs.strikes_landed, os_.strikes_landed = 30, 29
    dwcs.resolve(f, _Out(f=fs, o=os_))
    assert not f.story_flags.get("ufc_signed")
    assert dwcs.appearances(f) == 1
    return "no contract, back to the regional scene"


def test_dwcs_limited_looks():
    f = _contender()
    f.story_flags["dwcs_appearances"] = 2
    ok, why = dwcs.eligible(f)
    assert ok is False and "looks" in why
    return "at most two looks at the show"


# ---------------- unified NPC layer ----------------

def test_npc_roles_cover_everyone():
    for role in ("fighter", "coach", "manager", "promoter", "matchmaker", "media"):
        assert role in npc.ROLES, role
    return "all six roles defined"


def test_npc_profile_works_for_person_and_fighter():
    prom = people.promoter_for("UFC")
    assert prom is not None
    p1 = npc.profile(prom)
    assert p1["role"] == "promoter" and p1["traits"]
    f = Fighter.new_npc("Ivan", country_by_name("Bulgaria"), style="Sambo")
    f.fid = "npc_1"
    p2 = npc.profile(f)
    assert p2["role"] == "fighter" and p2["traits"]
    # Same shape for both — that is the point.
    assert set(p1) == set(p2)
    return "one profile shape for Person and Fighter"


def test_npc_traits_are_deterministic():
    prom = people.promoter_for("UFC")
    assert npc.traits(prom) == npc.traits(prom)
    a = Fighter.new_npc("A", country_by_name("USA"))
    a.fid = "npc_77"
    b = Fighter.new_npc("B", country_by_name("USA"))
    b.fid = "npc_77"
    # Same id -> same personality, with no stored fields and no save cost.
    assert npc.traits(a) == npc.traits(b)
    return "traits are stable and save-free"


def test_npcs_are_distinct():
    ids = ["npc_%d" % i for i in range(40)]
    seen = set()
    for i in ids:
        f = Fighter.new_npc("N", country_by_name("USA"))
        f.fid = i
        seen.add(tuple(npc.traits(f)))
    assert len(seen) > 20, len(seen)
    return "%d distinct personalities across 40 NPCs" % len(seen)


def test_role_transitions_declared():
    prom = people.promoter_for("UFC")
    f = Fighter.new_npc("R", country_by_name("USA"))
    f.fid = "npc_9"
    # A fighter can retire into coaching or management later.
    assert npc.can_become(f, "coach") is True
    assert npc.can_become(f, "manager") is True
    # A promoter is the end of the line.
    assert npc.can_become(prom, "fighter") is False
    return "role transition map ready for retire-into-coaching"


def test_competencies_reflect_role():
    mgr = people.all_managers()[0]
    c = npc.competencies(mgr)
    assert set(c) == set(npc.COMPETENCIES)
    # A manager should skew toward negotiation over pure technique.
    assert c["negotiation"] >= 25
    return "competencies biased by role"


def main():
    for t in (
        test_dwcs_needs_earning,
        test_dwcs_eligible_contender,
        test_dwcs_streak_required,
        test_dwcs_win_is_not_enough,
        test_dwcs_finish_signs_you,
        test_dwcs_dominant_decision_signs_you,
        test_dwcs_loss_earns_nothing,
        test_dwcs_resolve_signs_to_ufc,
        test_dwcs_resolve_no_contract_returns_to_regional,
        test_dwcs_limited_looks,
        test_npc_roles_cover_everyone,
        test_npc_profile_works_for_person_and_fighter,
        test_npc_traits_are_deterministic,
        test_npcs_are_distinct,
        test_role_transitions_declared,
        test_competencies_reflect_role,
    ):
        print("PASS", t())
    print("ALL 1.10 DWCS / NPC CHECKS OK")


if __name__ == "__main__":
    main()
