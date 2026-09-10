"""1.25.1 senior-review regressions for the 1.25 junior candidate."""
from __future__ import annotations

from mma_legend import career, contracts, identity
from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


def _pro(name="QA", org="UFC", wc="Middleweight"):
    f = Fighter.new_npc(name, country_by_name("USA"), style="MMA")
    f.pro_debut = True
    f.pro_record = [12, 2, 0]
    f.organization = org
    f.room = "ufc" if org == "UFC" else "regional"
    f.promotion_tier = 10 if org == "UFC" else 5
    f.weight_class = wc
    f.fid = name.lower().replace(" ", "_")
    f.story_flags = {"ufc_signed": org == "UFC"}
    return f


def test_release_stays_released_across_sync_and_contract_checks():
    f = _pro()
    contracts.sign(f, "UFC", fights=4, weeks=50, room="ufc")
    f.story_flags.update({"ufc_rank": 4, "org_rank": 4, "org_board": "UFC"})
    contracts.release(f, "declined renewal")
    identity.sync(f)
    assert f.organization is None
    assert contracts.active(f) is None
    assert contracts.can_accept(f, "ACA")[0]
    assert f.story_flags.get("ufc_rank") is None
    assert f.story_flags.get("org_rank") is None
    return "release clears both identity and contract; weekly sync cannot resurrect the deal"


def test_only_explicit_exclusive_corruption_self_heals():
    f = _pro()
    f.org_contract = {}
    identity.sync(f)
    assert f.org_contract == {}, f.org_contract
    f.org_contract = {"org": "", "exclusive": True, "fights_left": 4, "weeks_left": 50}
    identity.sync(f)
    assert f.org_contract.get("org") == "UFC", f.org_contract
    return "repair distinguishes a corrupt exclusive deal from an intentional empty contract"


def test_dwcs_is_not_ufc_ranking_experience():
    p = _pro("Player")
    p.is_player = True
    p.fight_history = [
        {"event": "DWCS", "pro": True, "result": "Win"},
        {"event": "UFC", "pro": True, "result": "Win"},
        {"event": "UFC Fight Night", "pro": True, "result": "Win"},
    ]
    pool = FighterPool()
    pool.fighters = [_pro("Opponent A"), _pro("Opponent B")]
    pool.attach_player(p)
    pool.update_rankings()
    assert p.story_flags.get("ufc_rank") is None, p.story_flags
    assert p not in pool.get_org_top("UFC", p.weight_class, 15)
    assert p not in pool.get_p4p(15)

    p.fight_history.append({"event": "UFC 410", "pro": True, "result": "Win"})
    pool.update_rankings()
    assert isinstance(p.story_flags.get("ufc_rank"), int), p.story_flags
    assert p in pool.get_org_top("UFC", p.weight_class, 15)
    assert p in pool.get_p4p(15)
    return "DWCS does not count; UFC and UFC-branded cards unlock ranking after bout three"


def test_sponsor_benefits_are_metadata_driven():
    f = _pro()
    f.sponsors = ["Optimum Nutrition"]
    assert career.supplement_sponsor(f) == "Optimum Nutrition"
    f.sponsors = ["Protein Shoes"]
    assert career.supplement_sponsor(f) is None
    return "legal-supplement coverage follows sponsor capability metadata, not name keywords"


def main():
    for test in (
        test_release_stays_released_across_sync_and_contract_checks,
        test_only_explicit_exclusive_corruption_self_heals,
        test_dwcs_is_not_ufc_ranking_experience,
        test_sponsor_benefits_are_metadata_driven,
    ):
        print("PASS", test())
    print("ALL 1.25.1 SENIOR-REVIEW CHECKS OK")


if __name__ == "__main__":
    main()
