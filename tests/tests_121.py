"""1.21 regression checks: progression, events, tactical damage and UI."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from mma_legend import aging, ai, app, balance, camps, cut, damage, data, events, fights, record
from mma_legend.data import country_by_name
from mma_legend.engine.fight import _damage_hunt_weight
from mma_legend.models import Fighter
from mma_legend.ui import GameConsole


class Quiet:
    def __init__(self, answers=None):
        self.answers = list(answers or [])
        self.lines = []
        self.fast = False
        self.color = False

    def ask(self, *_a, **_k):
        return self.answers.pop(0) if self.answers else ""

    def print(self, text="", *_a, **_k): self.lines.append(str(text))
    def header(self, *a, **_k): self.lines.extend(str(x) for x in a)
    def info(self, text="", *_a, **_k): self.lines.append(str(text))
    def warn(self, text="", *_a, **_k): self.lines.append(str(text))
    def good(self, text="", *_a, **_k): self.lines.append(str(text))
    def gold(self, text="", *_a, **_k): self.lines.append(str(text))
    def pause(self, *_a, **_k): pass
    def read_pause(self, *_a, **_k): pass
    def _c(self, text, *_a): return str(text)


def _f(physique="B"):
    return Fighter.new_player("Test Fighter", physique, country_by_name("USA"), "Boxing")


def test_one_birthday_per_year():
    f = _f()
    for _ in range(104):
        f.advance_week(None)
    assert f.week == 105
    assert f.age == 18, (f.week, f.age)
    return "104 spent weeks = two birthdays"


def test_physique_bodyfat():
    expected = {"A": 9.0, "B": 12.0, "C": 16.0, "D": 13.0, "E": 20.0, "F": 14.0}
    got = {key: _f(key).bodyfat for key in expected}
    assert got == expected, got
    return "six physiques initialize distinct body fat"


def test_recent_result_once():
    f = _f()
    o = Fighter.new_npc("Opponent", country_by_name("USA"), "Boxing")
    f.pro_debut = True
    o.pro_debut = True
    f.recent_results = []
    fights._apply_outcome(Quiet(), f, o, "win_decision", "Decision", 0, False)
    record.commit(f, o.name, "Win", "Unanimous Decision", 3, amateur=False)
    assert f.recent_results == ["W"], f.recent_results
    return "one fight = one form result"


def test_injury_one_clock():
    f = _f()
    cut.apply_injury(f, "knee", 2)
    before = damage.weeks_out(f)
    f.advance_week(None)
    after = damage.weeks_out(f)
    assert before == 24 and after == 23, (before, after, f.injury)
    assert f.injury.get("weeks") == 23
    return "structured injury heals one week per week"


def test_event_requirements_and_effects():
    f = _f()
    ctx = events.context_pack(f)
    assert not events.eligible(f, {"id": "age", "require": {"min_age": 21}}, ctx)
    parent = next(e for e in data.EVENTS_V14 if e.get("id") == "v14_04")
    assert events.eligible(f, parent, ctx), "parents must not match the word rent"
    events.apply_effects(f, {"team": "Elite MMA"})
    assert f.team == "Elite MMA"
    return "age, rent boundary and string effects work"


def test_blank_event_choice_is_not_a():
    f = _f()
    start = f.money
    evt = {
        "id": "blank", "title": "Choice", "description": "Pick.",
        "choices": [{"key": "A", "label": "Take cash", "effects": {"money": 500}}],
    }
    events.handle_event(Quiet([""]), f, evt)
    assert f.money == start
    return "blank input has no hidden choice"


def test_all_event_packs_validated():
    assert len(data.EVENTS_V121) == 30
    assert len(data.all_events()) >= 391
    assert events.validate_event_pack() == []
    return "1.21 event pack preserved; all current packs validate"


def test_ai_can_pick_new_event_pack():
    f = _f()
    f.recent_results = ["L"]
    target = next(e for e in data.EVENTS_V121 if e.get("id") == "v121_01")

    def choose(population, weights, k):
        assert target in population, "1.21 events missing from AI pool"
        return [target]

    with patch.object(ai.random, "random", return_value=0.0), \
            patch.object(ai.random, "choices", side_effect=choose):
        assert ai.pick_event(f) is target
    return "AI event picker includes the newest content pack"


def test_balance_fixtures_are_honest():
    a, b = balance._pair(elite=True, pro=True)
    for stat in ("striking", "grappling", "cardio", "ko_power",
                 "durability", "fight_iq", "speed"):
        assert getattr(a, stat) == getattr(b, stat), stat
    old, young = balance._pair(age_a=36, age_b=24, pro=True)
    assert old.speed < young.speed and old.cardio < young.cardio
    return "equal fixtures are equal and age decline is represented"


def test_live_damage_targeting():
    body = damage.BodyMap()
    body.loc["lead_leg"] = 72
    assert _damage_hunt_weight("low_kick", body, 80) > 1.7
    assert _damage_hunt_weight("jab", body, 80) == 1.0
    body.loc["body"] = 70
    assert _damage_hunt_weight("liver", body, 80) > 1.6
    return "AI hunts damage without boosting unrelated moves"


def test_body_map_hud_width():
    q = Quiet()
    body = damage.BodyMap()
    body.loc.update({"head": 12, "body": 34, "lead_leg": 56, "rear_leg": 20})
    body.cuts["left brow"] = 44
    GameConsole.fight_damage_line(q, body, mine=True)
    assert q.lines and "H12 B34 L56 C44" in q.lines[-1]
    assert len(q.lines[-1]) <= 44, q.lines[-1]
    return "live body map fits a phone line"


def test_panels_wrap_to_phone_width():
    console = GameConsole(width=44, fast=True, color=False)
    buf = StringIO()
    with redirect_stdout(buf):
        console.panel("Recovery", [
            "Week: broken knuckle — seven weeks until full medical clearance"
        ])
    assert max(map(len, buf.getvalue().splitlines())) <= 44
    return "long status panels wrap to phone width"


def test_camps_are_major_investments():
    costs = [v["cost"] for v in camps.DESTINATIONS.values()]
    assert min(costs) >= 1800 and max(costs) >= 4000, costs
    return "foreign camps cost $%s-$%s" % (min(costs), max(costs))


def test_cancel_spends_no_time():
    f = _f()
    f.week_kind = "none"
    app._dispatch_action(Quiet(), f, None, "")
    assert f.week_kind == "none"
    q = Quiet(["X"])
    q.fast = False
    app._options_menu(q)
    assert q.fast is False
    return "invalid/back actions remain free"


def main():
    tests = (
        test_one_birthday_per_year, test_physique_bodyfat,
        test_recent_result_once, test_injury_one_clock,
        test_event_requirements_and_effects, test_blank_event_choice_is_not_a,
        test_all_event_packs_validated, test_ai_can_pick_new_event_pack,
        test_balance_fixtures_are_honest, test_live_damage_targeting,
        test_body_map_hud_width, test_panels_wrap_to_phone_width,
        test_camps_are_major_investments,
        test_cancel_spends_no_time,
    )
    for test in tests:
        print("PASS", test())
    print("ALL 1.21 CHECKS OK")


if __name__ == "__main__":
    main()
