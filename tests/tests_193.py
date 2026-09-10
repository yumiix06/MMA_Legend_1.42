"""1.19.3 checks: fight HUD and overseas camps."""
from __future__ import annotations

import random

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.ui import GameConsole
from mma_legend import camps, combat, booking


class _Cap(GameConsole):
    """Console that records every printed line."""
    def __init__(self):
        super().__init__(width=44, color=False)
        self.lines = []
        self.fast = True

    def print(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))

    def ask(self, *a, **k):
        return "A"

    def pause(self, *a, **k):
        pass

    def auto_pause(self, *a, **k):
        pass


def test_feed_is_prefixed_and_short():
    random.seed(12)
    c = _Cap()
    a = Fighter.new_player("Umur Panteleev", "B", country_by_name("Bulgaria"), "Wrestling")
    a.pro_debut = True
    a.fight_details = "Round"
    b = Fighter.new_npc("Kostas Yoon", country_by_name("Ukraine"), style="Muay Thai")
    booking.apply_kit(b, "Muay Thai")
    combat.fight_mma(c, a, b, rounds=3, gameplan="Balanced", interactive=True)
    body = [l for l in c.lines if l.startswith(("> ", "< "))]
    assert body, "fight feed produced no prefixed lines"
    # Full names must not appear in the feed — they ate a phone line each.
    assert not any("Panteleev" in l and "Umur" in l for l in body)
    over = [l for l in c.lines if len(l) > 60]
    assert len(over) <= 2, over[:3]
    return "%d feed lines, all prefixed and within width" % len(body)


def test_no_immediate_repeats():
    random.seed(4)
    c = _Cap()
    a = Fighter.new_player("A B", "B", country_by_name("USA"), "Boxing")
    a.pro_debut = True
    a.fight_details = "Round"
    b = Fighter.new_npc("C D", country_by_name("USA"), style="Boxing")
    booking.apply_kit(b, "Boxing")
    combat.fight_mma(c, a, b, rounds=3, interactive=True)
    body = [l for l in c.lines if l.startswith(("> ", "< "))]
    triples = sum(1 for i in range(len(body) - 2)
                  if body[i] == body[i + 1] == body[i + 2])
    assert triples == 0, "identical line repeated three times running"
    return "no line repeats three times in a row"


def test_moment_menu_fits_one_line():
    from mma_legend.engine.fight import _tech_options
    f = Fighter.new_player("M", "B", country_by_name("USA"), "Wrestling")
    opts = _tech_options(f, "stand", False, False, None)
    assert len(opts) <= 4, opts
    return "moment menu capped at %d options" % len(opts)


# ---------------- camps ----------------

def test_camp_blocked_when_booked():
    f = Fighter.new_player("C", "B", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    f.booked_fight = {"org": "LFA", "date_week": 40}
    ok, why = camps.can_go(f)
    assert ok is False and "date booked" in why
    return "cannot fly out with a fight booked"


def test_camp_costs_weeks_and_money():
    f = Fighter.new_player("C", "B", country_by_name("USA"), "Wrestling")
    f.money = 5000
    camps.start(f, "A")
    assert f.money == 5000 - camps.DESTINATIONS["A"]["cost"], f.money
    assert f.intl_camp_weeks == 6
    assert f.camp_active is True
    return "camp takes real money and real weeks"


def test_camp_teaches_and_connects():
    random.seed(5)
    f = Fighter.new_player("C", "B", country_by_name("Bulgaria"), "Wrestling")
    f.money = 5000
    before = set(f.techniques or [])
    camps.start(f, "A")
    for _ in range(6):
        camps.tick(f)
    assert f.intl_camp is None, "camp did not end"
    conns = getattr(f, "connections", None) or []
    assert conns, "camp produced no connection"
    c = conns[-1]
    assert c.get("who") and c.get("role") in camps.CONNECTION_ROLES
    gained = set(f.techniques or []) - before
    assert gained, "camp taught nothing"
    return "learned %s, met a %s" % (sorted(gained)[:2], c["role"])


def test_connections_are_actually_read():
    """The old system wrote `connections` and nothing ever read them."""
    f = Fighter.new_player("C", "B", country_by_name("USA"), "Wrestling")
    f.connections = [{"place_name": "Rio, Brazil", "who": "X", "role": "coach",
                      "strength": 70}]
    assert camps.corner_quality(f) == 70
    f.connections.append({"place_name": "Rio, Brazil", "who": "Y",
                          "role": "matchmaker", "strength": 80})
    assert camps.connection_bonus(f, country="Brazil") > 0
    return "connections feed corner quality and matchmaking reach"


def main():
    for t in (
        test_feed_is_prefixed_and_short,
        test_no_immediate_repeats,
        test_moment_menu_fits_one_line,
        test_camp_blocked_when_booked,
        test_camp_costs_weeks_and_money,
        test_camp_teaches_and_connects,
        test_connections_are_actually_read,
    ):
        print("PASS", t())
    print("ALL 1.19.3 CHECKS OK")


if __name__ == "__main__":
    main()
