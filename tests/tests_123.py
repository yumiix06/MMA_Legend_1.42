"""1.23 Phase-3 checks: contextual events, event DSL validation and release UI."""
from __future__ import annotations

import random
from collections import Counter

from mma_legend import ai, data, events
from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.ui import GameConsole


GROUPS = {
    "wins", "losses", "injuries", "camps", "money",
    "gyms", "teammates", "family", "media", "career",
}


class CaptureConsole(GameConsole):
    """No stdin/sleeps; records exactly what event UI would print."""
    def __init__(self):
        super().__init__(width=44, fast=True, color=False)
        self.lines = []

    def print(self, msg="", style=None):
        self.lines.append(str(msg))

    def header(self, title, subtitle=None):
        self.lines.append("=" * self.width)
        self.lines.append(str(title).center(self.width))
        if subtitle:
            self.lines.append(str(subtitle).center(self.width))
        self.lines.append("=" * self.width)

    def ask(self, *_a, **_k):
        return ""

    def pause(self, *_a, **_k):
        pass

    def read_pause(self, *_a, **_k):
        pass


def _f():
    f = Fighter.new_player("Phase Three", "B", country_by_name("USA"), "Boxing")
    f.age = 26
    f.week = 120
    f.money = 2000
    f.energy = 70
    f.health = 80
    f.fame = 10
    f.reputation = 10
    f.amateur_record = [6, 2, 0]
    f.school_status = "none"
    return f


def _satisfy(evt):
    """Construct a plausible fighter satisfying the declarative requirements.

    If this helper cannot make a new event eligible, the event is probably dead
    because of an accidental hidden text/category gate.
    """
    f = _f()
    req = evt.get("require") or {}

    if req.get("pro"):
        f.pro_debut = True
        f.pro_record = [max(4, int(req.get("min_pro_wins", 0) or 0)), 2, 0]
    if req.get("amateur"):
        f.pro_debut = False
        f.pro_record = [0, 0, 0]

    if req.get("min_wins") is not None:
        need = int(req["min_wins"])
        if f.pro_debut:
            f.pro_record[0] = max(f.pro_record[0], max(0, need - f.amateur_record[0]))
        else:
            f.amateur_record[0] = max(f.amateur_record[0], need)
    if req.get("max_wins") is not None:
        cap = int(req["max_wins"])
        if f.pro_debut:
            # Keep any explicit pro-win floor and reduce amateur history first.
            pro_floor = int(req.get("min_pro_wins", 0) or 0)
            f.pro_record[0] = max(pro_floor, min(f.pro_record[0], cap))
            f.amateur_record[0] = max(0, min(f.amateur_record[0], cap - f.pro_record[0]))
        else:
            f.amateur_record[0] = min(f.amateur_record[0], cap)
    if req.get("min_pro_wins") is not None:
        f.pro_debut = True
        f.pro_record[0] = max(f.pro_record[0], int(req["min_pro_wins"]))
    if req.get("min_losses") is not None:
        target = f.pro_record if f.pro_debut else f.amateur_record
        target[1] = max(target[1], int(req["min_losses"]))
    if req.get("max_losses") is not None:
        target = f.pro_record if f.pro_debut else f.amateur_record
        target[1] = min(target[1], int(req["max_losses"]))

    if evt.get("category") == "media" and f.get_total_record()[0] < 3:
        f.amateur_record[0] = 3
    if req.get("last"):
        last = req["last"][0] if isinstance(req["last"], list) else req["last"]
        f.recent_results = [str(last)]

    if req.get("min_age") is not None:
        f.age = max(f.age, int(req["min_age"]))
    if req.get("max_age") is not None:
        f.age = min(f.age, int(req["max_age"]))
    for attr, key in (
        ("fame", "min_fame"), ("reputation", "min_rep"),
        ("energy", "min_energy"), ("health", "min_health"),
        ("money", "min_money"), ("week", "min_week"),
        ("followers", "min_followers"), ("debt", "min_debt"),
    ):
        if req.get(key) is not None:
            setattr(f, attr, max(getattr(f, attr), int(req[key])))
    for attr, key in (
        ("reputation", "max_rep"), ("energy", "max_energy"),
        ("health", "max_health"), ("money", "max_money"),
        ("week", "max_week"), ("followers", "max_followers"),
        ("debt", "max_debt"),
    ):
        if req.get(key) is not None:
            setattr(f, attr, min(getattr(f, attr), int(req[key])))

    if req.get("min_streak") is not None:
        f.current_streak = int(req["min_streak"])
    if req.get("max_streak") is not None:
        f.current_streak = int(req["max_streak"])
    if req.get("injured") is not None:
        f.injury = {"area": "knee", "weeks": 2, "severity": 2} if req["injured"] else {}
    if req.get("min_damage") is not None:
        f.damage["total"] = int(req["min_damage"])
    if req.get("camp") is True:
        f.camp_active = True
    if req.get("intl_camp") is True:
        f.intl_camp = "thailand"
        f.intl_camp_weeks = 3
        f.camp_active = True
    if req.get("booked") is True:
        f.booked_fight = {"opponent": "QA Opponent", "weeks": 4}
    if req.get("teammate") is True:
        f.teammate = "Milo Petrov"
    if req.get("manager") is True:
        f.manager = "QA Manager"
        f.manager_id = "mgr_qa"
    if req.get("gym") is True:
        f.specialty_gym = "QA MMA"
        f.specialty_gym_type = "mma"
    if req.get("org") is not None:
        want = req["org"]
        if want is True:
            f.organization = "LFA"
        elif isinstance(want, list):
            f.organization = str(want[0])
        else:
            f.organization = str(want)
    if req.get("min_sponsors") is not None:
        f.sponsors = ["QA Sponsor %s" % i for i in range(int(req["min_sponsors"]))]

    for rel in ("family", "friends", "coach", "partner", "rival"):
        lo = req.get("min_rel_" + rel)
        hi = req.get("max_rel_" + rel)
        if lo is not None:
            f.relationships[rel] = max(f.relationships.get(rel, 0), int(lo))
        if hi is not None:
            f.relationships[rel] = min(f.relationships.get(rel, 0), int(hi))
    return f


def test_phase3_pack_shape_and_dsl():
    assert len(data.EVENTS_V123) == 60
    groups = Counter(e.get("phase3_group") for e in data.EVENTS_V123)
    assert set(groups) == GROUPS, groups
    assert all(groups[g] == 6 for g in GROUPS), groups
    later = len(getattr(data, "EVENTS_V125", [])) + len(getattr(data, "EVENTS_V127", []))
    assert len(data.all_events()) >= 451 + later
    assert events.validate_event_pack() == []
    return "60 Phase-3 events, ten contextual groups, %s total, DSL valid" % len(data.all_events())


def test_every_phase3_event_is_reachable():
    bad = []
    for evt in data.EVENTS_V123:
        f = _satisfy(evt)
        if not events.eligible(f, evt, events.context_pack(f)):
            bad.append(evt["id"])
    assert not bad, "unreachable Phase-3 events: %s" % bad
    return "all 60 new events have at least one valid context"


def test_context_gates_are_real():
    streak_evt = next(e for e in data.EVENTS_V123 if e["id"] == "v123_004")
    f = _satisfy(streak_evt)
    assert events.eligible(f, streak_evt, events.context_pack(f))
    f.current_streak = 1
    assert not events.eligible(f, streak_evt, events.context_pack(f))

    mate_evt = next(e for e in data.EVENTS_V123 if e["id"] == "v123_015")
    f = _satisfy(mate_evt)
    assert events.eligible(f, mate_evt, events.context_pack(f))
    f.teammate = None
    assert not events.eligible(f, mate_evt, events.context_pack(f))

    # Regression: substring "grades" used to make "upgrades" a school event.
    gym_evt = next(e for e in data.EVENTS_V123 if e["id"] == "v123_033")
    f = _satisfy(gym_evt)
    f.age = 30
    f.school_status = "none"
    assert events.eligible(f, gym_evt, events.context_pack(f))
    return "streak/teammate gates work; 'upgrades' no longer trips school gate"


def test_all_event_cards_fit_phone_width():
    worst = (0, "", "")
    for evt in data.all_events():
        f = _satisfy(evt)
        c = CaptureConsole()
        events.handle_event(c, f, evt)
        for line in c.lines:
            n = len(str(line))
            if n > worst[0]:
                worst = (n, evt.get("id", "?"), str(line))
    assert worst[0] <= 44, worst
    return "all %s event cards render at <=44 columns (worst %s)" % (len(data.all_events()), worst[0])


def _profile(kind):
    f = _f()
    if kind == "rising_am":
        f.amateur_record = [6, 1, 0]; f.current_streak = 3; f.recent_results = ["W"]
    elif kind == "hurt_loss":
        f.amateur_record = [3, 4, 0]; f.current_streak = -2; f.recent_results = ["L"]
        f.injury = {"area":"hand","weeks":3,"severity":2}; f.health = 48; f.money = 90
    elif kind == "pro":
        f.pro_debut = True; f.pro_record = [5, 2, 0]; f.amateur_record = [7, 2, 0]
        f.current_streak = 2; f.recent_results = ["W"]; f.organization = "LFA"; f.fame = 12
    elif kind == "contender":
        f.pro_debut = True; f.pro_record = [10, 2, 0]; f.amateur_record = [8, 2, 0]
        f.current_streak = 4; f.recent_results = ["W"]; f.organization = "UFC"; f.fame = 24
        f.manager = "Manager"; f.manager_id = "mgr"; f.followers = 15000
    elif kind == "camp":
        f.pro_debut = True; f.pro_record = [4, 1, 0]; f.amateur_record = [6, 1, 0]
        f.camp_active = True; f.intl_camp = "thailand"; f.intl_camp_weeks = 3
        f.booked_fight = {"opponent":"Opponent","weeks":4}; f.energy = 64; f.fame = 10
    f.specialty_gym = "QA MMA"
    f.teammate = "Milo Petrov"
    return f


def test_event_frequency_not_dominated_by_new_pack():
    # Conditional selection frequency (ignoring quiet weeks) across different
    # career states. A content expansion should be visible, not swallow every
    # historical story/event pack.
    random.seed(1230)
    shares = {}
    for kind in ("rising_am", "hurt_loss", "pro", "contender", "camp"):
        f = _profile(kind)
        ctx = events.context_pack(f)
        pool = [e for e in data.all_events(newest_first=True) if events.eligible(f, e, ctx)]
        weights = [ai.event_score(f, e, ctx) for e in pool]
        picks = random.choices(pool, weights=weights, k=2500)
        share = sum(str(e.get("id", "")).startswith("v123_") for e in picks) / len(picks)
        shares[kind] = share
        assert 0.06 <= share <= 0.48, (kind, share, len(pool))
    return "new-pack conditional share stays contextual: " + ", ".join(
        "%s %.0f%%" % (k, v * 100) for k, v in shares.items())


def test_teammate_placeholder_uses_real_name():
    evt = next(e for e in data.EVENTS_V123 if e["id"] == "v123_037")
    f = _satisfy(evt)
    c = CaptureConsole()
    events.handle_event(c, f, evt)
    text = "\n".join(c.lines)
    assert "Milo Petrov" in text and "{teammate}" not in text
    return "context text resolves teammate name"


def main():
    for test in (
        test_phase3_pack_shape_and_dsl,
        test_every_phase3_event_is_reachable,
        test_context_gates_are_real,
        test_all_event_cards_fit_phone_width,
        test_event_frequency_not_dominated_by_new_pack,
        test_teammate_placeholder_uses_real_name,
    ):
        print("PASS", test())
    print("ALL 1.23 PHASE-3 CHECKS OK")


if __name__ == "__main__":
    main()
