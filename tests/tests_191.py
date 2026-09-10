"""1.19.1 checks: record integrity and contract persistence."""
from __future__ import annotations

from pathlib import Path

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.world import FighterPool
from mma_legend import record as R, contracts, orgs, persistence


class _Q:
    color = False
    fast = True
    width = 40

    def __getattr__(self, n):
        return lambda *a, **k: ""

    def ask(self, *a, **k):
        return "A"


def test_npc_career_not_wiped():
    """An NPC has a record but no history. Deriving purely from history used
    to erase their whole career on their first fight: 4-1 became 1-0."""
    n = Fighter.new_npc("K", country_by_name("USA"))
    n.fid = "x"
    n.pro_debut = True
    n.pro_record = [4, 1, 0]
    R.commit(n, "Foe", "Win", "KO", 1, event="LFA", sport="mma", amateur=False)
    assert n.pro_record == [5, 1, 0], n.pro_record
    return "NPC 4-1 + win = 5-1"


def test_corrupt_record_still_repaired():
    """The other semantic must survive: a bogus record over a real ledger is
    corruption and gets rebuilt from the ledger."""
    f = Fighter.new_player("U", "M", country_by_name("Bulgaria"), "Boxing")
    f.pro_debut = True
    f.pro_record = [17, 5, 0]
    f.fight_history = [
        {"opponent": "A", "result": "Win", "event": "Balkan Combat", "sport": "mma"},
        {"opponent": "B", "result": "Win", "event": "Cage Warriors", "sport": "mma"},
        {"opponent": "C", "result": "Loss", "event": "Cage Warriors", "sport": "mma"},
    ]
    assert R.sync(f) == [2, 1, 0], f.pro_record
    return "bogus 17-5 over a 3-row ledger repairs to 2-1"


def test_no_double_count():
    """_apply_outcome must not touch pro W-L; record.commit owns it."""
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.organization = "LFA"
    o = Fighter.new_npc("O", country_by_name("USA"))
    o.fid = "o1"
    o.pro_debut = True
    o.pro_record = [4, 1, 0]
    from mma_legend.fights import _apply_outcome
    _apply_outcome(_Q(), f, o, "win_decision", None, 100, False)
    assert f.pro_record == [0, 0, 0], f.pro_record
    assert o.pro_record == [4, 1, 0], o.pro_record
    return "_apply_outcome leaves pro W-L alone"


def test_amateur_still_counted_inline():
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    o = Fighter.new_npc("O", country_by_name("USA"))
    from mma_legend.fights import _apply_outcome
    before = list(f.amateur_record)
    _apply_outcome(_Q(), f, o, "win_decision", None, 100, True)
    assert f.amateur_record[0] == before[0] + 1, f.amateur_record
    return "amateur record still incremented inline"


def test_contract_survives_save():
    """org_contract was never a declared dataclass field, so from_dict()
    dropped it on every load and signings silently vanished."""
    assert "org_contract" in Fighter.__dataclass_fields__
    f = Fighter.new_player("RT", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    pool = FighterPool()
    pool.generate_world(20, 10)
    orgs.sign_org(f, "KSW")
    assert contracts.active(f) is not None
    p = Path("/tmp/_ml_contract_rt.json")
    persistence.save_game(_Q(), f, pool, p)
    f2, _ = persistence.load_game(_Q(), p)
    live = contracts.active(f2)
    assert live is not None, "contract lost on save/load"
    assert live["org"] == "KSW"
    return "contract survives save/load"


def test_exclusivity_after_load():
    f = Fighter.new_player("E", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    orgs.sign_org(f, "KSW")
    assert contracts.can_accept(f, "PFL")[0] is False
    assert contracts.can_accept(f, "KSW")[0] is True
    return "exclusivity holds"


def main():
    for t in (
        test_npc_career_not_wiped,
        test_corrupt_record_still_repaired,
        test_no_double_count,
        test_amateur_still_counted_inline,
        test_contract_survives_save,
        test_exclusivity_after_load,
    ):
        print("PASS", t())
    print("ALL 1.19.1 CHECKS OK")


if __name__ == "__main__":
    main()
