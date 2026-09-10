"""1.17 renewal, debug save, world size."""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import contracts, orgs, persistence
from mma_legend.world import FighterPool


def _pro():
    f = Fighter.new_player("Umur", "M", country_by_name("Bulgaria"), "Boxing")
    f.pro_debut = True
    f.pro_record = [17, 5, 0]
    f.fame = 40
    return f


def test_term_expiry_queues_resign():
    f = _pro()
    orgs.sign_org(f, "Cage Warriors", fights=4, weeks=2)
    contracts.tick(f)
    contracts.tick(f)
    assert contracts.active(f) is None
    pending = (f.story_flags or {}).get("pending_renewal")
    assert isinstance(pending, dict) and pending.get("org") == "Cage Warriors"
    assert f.organization == "Cage Warriors"
    line = contracts.accept_renewal(f)
    assert contracts.active(f) is not None
    assert f.story_flags.get("pending_renewal") in (None, {})
    return line


def test_debug_snapshot_has_records():
    pool = FighterPool()
    pool.generate_world(20, 12)
    f = _pro()
    f.organization = "Cage Warriors"
    f.weight_class = "Middleweight"
    f.fight_history = [{"result": "Win"}, {"result": "Loss"}, {"result": "Win"}]
    f.story_flags["pro_fights_done"] = 22
    snap = persistence.debug_snapshot(f, pool)
    assert snap["history_n"] == 3
    assert snap["history_wl"] == [2, 1]
    assert snap["pro_fights_done"] == 22
    assert "pool_n" in snap
    return "debug keys ok"


def test_new_world_is_large():
    # Default signature, not a brittle source-text assertion.
    import inspect
    params = inspect.signature(FighterPool.generate_world).parameters
    assert params["n_amateurs"].default == 840
    assert params["n_pros"].default == 560
    return "defaults 840/560 across seven amateur ecosystems"


def main():
    for t in (test_term_expiry_queues_resign, test_debug_snapshot_has_records, test_new_world_is_large):
        print("PASS", t.__name__, t())
    print("ALL 1.17 OK")


if __name__ == "__main__":
    main()
