"""1.9 checks: contracts, camp integrity, UFC difficulty.

Pins down the bugs reported from live phone play:
  - signing a fight started an 8-week camp and then fought the same week
  - a "signed" fighter could still take dates from rival promotions
  - the UFC arrived far too easily
"""
from __future__ import annotations

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend import contracts, orgs, booking, systems17


def _pro():
    f = Fighter.new_player("P", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.week = 40
    return f


def test_signing_creates_contract():
    """sign_org used to set a label and nothing else, so nothing was enforced."""
    f = _pro()
    orgs.sign_org(f, "KSW")
    c = contracts.active(f)
    assert c is not None, "signing must create a real contract"
    assert c["org"] == "KSW"
    assert c["fights_left"] >= 1
    assert c["weeks_left"] >= 1
    return "contract created: %s" % contracts.line(f)


def test_exclusivity():
    f = _pro()
    orgs.sign_org(f, "KSW")
    assert contracts.can_accept(f, "KSW")[0] is True
    assert contracts.can_accept(f, "PFL")[0] is False
    assert contracts.can_accept(f, "Bellator")[0] is False
    # The Contender Series is the one permitted door.
    assert contracts.can_accept(f, "DWCS")[0] is True
    # systems17 must agree — it is a wrapper over the same gate.
    assert systems17.contract_locked(f, "PFL") is True
    assert systems17.contract_locked(f, "KSW") is False
    return "exclusivity enforced, DWCS feeder allowed"


def test_free_agent_can_take_anything():
    f = _pro()
    f.org_contract = {}
    assert contracts.can_accept(f, "PFL")[0] is True
    assert contracts.active(f) is None
    return "free agent unrestricted"


def test_contract_burns_down():
    f = _pro()
    orgs.sign_org(f, "LFA", fights=2)
    contracts.note_fight(f)
    assert contracts.active(f)["fights_left"] == 1
    contracts.note_fight(f)
    # Fought out: no longer an active deal, so a new one can be negotiated.
    assert contracts.active(f) is None
    return "fights burn down and the deal ends"


def test_contract_term_expires():
    f = _pro()
    orgs.sign_org(f, "LFA", fights=9, weeks=3)
    for _ in range(3):
        contracts.tick(f)
    assert contracts.active(f) is None, "deal should lapse when the term runs out"
    return "calendar term expires independently of fights"


def test_legacy_contract_migrates():
    """A 1.7/1.8 save has no weeks_left. It must not read as expired."""
    f = _pro()
    f.org_contract = {"org": "KSW", "fights_left": 3}
    c = contracts.active(f)
    assert c is not None, "legacy contract must migrate, not vanish"
    assert c["weeks_left"] > 0
    assert systems17.contract_locked(f, "UFC") is True
    return "legacy contract migrated with weeks_left=%s" % c["weeks_left"]


def test_ufc_is_hard():
    f = _pro()
    # A decent regional fighter should have no direct UFC path at all.
    f.pro_record = [7, 1, 0]
    f.fame = 40
    f.promotion_tier = 8
    f.recent_results = ["W"] * 5
    assert orgs.direct_ufc_chance(f) == 0.0, "7 wins should not be a UFC call"
    # Even a strong record is only a modest chance.
    f.pro_record = [12, 1, 0]
    f.fame = 60
    ch = orgs.direct_ufc_chance(f)
    assert 0.0 < ch <= 0.12, ch
    # A losing record is never a call.
    f.pro_record = [10, 6, 0]
    assert orgs.direct_ufc_chance(f) == 0.0
    return "direct UFC gated: best case %.1f%%" % (ch * 100)


def test_booked_date_is_in_the_future():
    """The reported bug: camp was started and the fight happened the same week."""
    f = _pro()
    f.week = 100
    offer = {"org": "LFA", "date_week": 108, "purse_win": 500, "purse_show": 100}
    booking.set_booked(f, offer)
    assert f.booked_fight["date_week"] > f.week, "fight must be scheduled ahead"
    assert f.camp_for_bout >= 1
    # And a date that arrives already stale gets pushed out, never run instantly.
    f2 = _pro()
    f2.week = 100
    booking.set_booked(f2, {"org": "LFA", "date_week": 100})
    assert f2.booked_fight["date_week"] > 100
    return "booked dates always land in the future"


def test_one_fight_at_a_time():
    f = _pro()
    f.week = 50
    booking.set_booked(f, {"org": "LFA", "date_week": 56})
    first = dict(f.booked_fight)
    # A second booking must replace, never stack.
    booking.set_booked(f, {"org": "KSW", "date_week": 60})
    assert isinstance(f.booked_fight, dict)
    assert f.booked_fight["org"] == "KSW"
    assert first["org"] == "LFA"
    return "only one booked date is ever held"


def main():
    for t in (
        test_signing_creates_contract,
        test_exclusivity,
        test_free_agent_can_take_anything,
        test_contract_burns_down,
        test_contract_term_expires,
        test_legacy_contract_migrates,
        test_ufc_is_hard,
        test_booked_date_is_in_the_future,
        test_one_fight_at_a_time,
    ):
        print("PASS", t())
    print("ALL 1.9 CONTRACT / BOOKING CHECKS OK")


if __name__ == "__main__":
    main()
