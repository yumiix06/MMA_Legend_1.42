"""1.22 Phase-2 checks: tactical targeting, mobile UI, camp value and handoff safety."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from mma_legend import balance, camps, data, damage, events
from mma_legend.data import country_by_name
from mma_legend.engine.fight import _damage_hunt_weight, _damage_target_hint
from mma_legend.models import Fighter
from mma_legend.ui import GameConsole, render_dashboard, wrap_text


class Quiet:
    def __init__(self, answers=None):
        self.answers = list(answers or [])
        self.lines = []
        self.fast = True
        self.color = False
        self.width = 44

    def ask(self, *_a, **_k):
        return self.answers.pop(0) if self.answers else ""

    def print(self, text="", *_a, **_k): self.lines.append(str(text))
    def header(self, *a, **_k): self.lines.extend(str(x) for x in a)
    def info(self, text="", *_a, **_k): self.lines.append(str(text))
    def warn(self, text="", *_a, **_k): self.lines.append(str(text))
    def good(self, text="", *_a, **_k): self.lines.append(str(text))
    def read_pause(self, *_a, **_k): pass
    def _c(self, text, *_a): return str(text)


def _f():
    return Fighter.new_player("Phase Two", "B", country_by_name("USA"), "Boxing")


def test_exact_leg_targeting():
    body = damage.BodyMap()
    body.loc["lead_leg"] = 28
    body.loc["rear_leg"] = 74
    assert _damage_target_hint("low_kick", body, 82) == "rear_leg"
    assert _damage_target_hint("low_kick", body, 30) == "lead_leg"
    before_lead = body.loc["lead_leg"]
    before_rear = body.loc["rear_leg"]
    body.hit("low_kick", 2, "rear_leg")
    assert body.loc["lead_leg"] == before_lead
    assert body.loc["rear_leg"] > before_rear
    return "high-IQ AI attacks the actually damaged leg"


def test_cut_targeting_and_worsening():
    body = damage.BodyMap()
    body.cuts["left brow"] = 61
    assert _damage_target_hint("cross", body, 80) == "cut:left brow"
    assert _damage_target_hint("cross", body, 40) == "head"
    before = body.cuts["left brow"]
    with patch("mma_legend.damage.random.randint", return_value=9):
        after = body.worsen_cut("left brow", "cross", 3)
    assert after > before and body.cuts["left brow"] == after
    assert _damage_hunt_weight("cross", body, 80) > 1.0
    return "smart AI can work an existing cut instead of a random brow"


def test_hud_exposes_both_legs_and_stays_phone_safe():
    body = damage.BodyMap()
    body.loc.update({"head": 12, "body": 34, "lead_leg": 18, "rear_leg": 76})
    body.cuts["right brow"] = 44
    q = Quiet()
    GameConsole.fight_damage_line(q, body, mine=False)
    line = q.lines[-1]
    assert "H12 B34 L76 C44" in line
    assert "L/R18/76" in line
    assert len(line) <= 44, line
    return "HUD keeps H/B/L/C scan order and reveals lead/rear leg damage"


def test_feed_menu_and_long_token_width():
    c = GameConsole(width=44, fast=True, color=False)
    buf = StringIO()
    with redirect_stdout(buf):
        c.feed("A very long exchange description where the fighter changes levels, drives through the hips and finishes on the fence", mine=False, tag="TD")
        c.menu_table([
            ("A", "", "Training camp", "Travel abroad for a specialist room with rare techniques and career connections"),
        ])
        c.panel("TOKEN", ["x" * 93])
    lines = buf.getvalue().splitlines()
    assert lines
    assert max(map(len, lines)) <= 44, max(lines, key=len)
    return "fight feed, menus and long tokens obey 44-column output"


def test_dashboard_compact_and_correct_overseas_clock():
    f = _f()
    f.money = 12345
    f.intl_camp = "thailand"
    f.intl_camp_weeks = 3
    f.camp_active = True
    f.camp_focus = "Phuket, Thailand"
    f.camp_weeks_remaining = 0  # old dashboard incorrectly read this field
    f.injury = {"area": "deep cut", "weeks": 2, "severity": 2}
    f.damage = {"total": 18}
    f.last_week_note = "Hard sparring exposed the rear leg and forced a tactical adjustment."
    c = GameConsole(width=44, fast=True, color=False)
    buf = StringIO()
    with redirect_stdout(buf):
        render_dashboard(c, f)
    lines = buf.getvalue().splitlines()
    assert any("Abroad:" in ln and "3w left" in ln for ln in lines), buf.getvalue()
    assert max(map(len, lines)) <= 44, max(lines, key=len)
    # A representative busy dashboard should be useful without becoming a
    # 40-line status dump again.
    assert len(lines) <= 34, len(lines)
    return "dashboard groups state and uses intl_camp_weeks correctly"


def test_camp_prices_follow_reward_profile():
    costs = {k: v["cost"] for k, v in camps.DESTINATIONS.items()}
    for spec in camps.DESTINATIONS.values():
        assert spec["cost"] == camps._quoted_cost(spec)
    assert costs["D"] > costs["B"] > costs["E"], costs
    assert costs["D"] >= 6000 and min(costs.values()) >= 3500, costs
    pv = camps.preview(_f(), "D")
    assert pv["quality"] == 5 and pv["network"] == 5 and pv["reward_count"] >= 3
    return "camp quote scales with weeks, quality, techniques and network upside"


def test_legacy_event_letter_choice_still_works():
    f = _f()
    # Base event pack uses the old format: "A) ..." inside label, no key.
    evt = next(e for e in data.EVENT_DATABASE if any(
        str(c.get("label", "")).startswith("A) Take a week off")
        for c in (e.get("choices") or [])))
    target = next(c for c in evt["choices"] if str(c.get("label", "")).startswith("A)"))
    before = {k: getattr(f, k) for k in target.get("effects", {}) if hasattr(f, k)}
    events.handle_event(Quiet(["A"]), f, evt)
    changed = any(getattr(f, k) != v for k, v in before.items())
    assert changed, (evt.get("id"), target, before)
    return "legacy A/B/C event labels remain selectable after Phase-1 input fix"


def test_combat_balance_guardrail():
    # Phase 2 changes tactical selection/targeting, not the underlying hit/KO
    # constants. Verify the new intelligence did not reintroduce slot bias or
    # turn ordinary pro fights into finish spam.
    r = balance._run(180, pro=True, seed=1222)
    # Existing tests_194 carries the stricter 40-60 clone-by-style test. This
    # smoke check is deliberately wider because a 180-fight method sample can
    # move several points even while the stricter clone/style suites stay healthy.
    assert 0.34 <= r["win"] <= 0.66, r
    assert 0.35 <= r["dec"] <= 0.80, r
    return "180 equal pro fights remain fair with a sane decision rate"


def main():
    tests = (
        test_exact_leg_targeting,
        test_cut_targeting_and_worsening,
        test_hud_exposes_both_legs_and_stays_phone_safe,
        test_feed_menu_and_long_token_width,
        test_dashboard_compact_and_correct_overseas_clock,
        test_camp_prices_follow_reward_profile,
        test_legacy_event_letter_choice_still_works,
        test_combat_balance_guardrail,
    )
    for test in tests:
        print("PASS", test())
    print("ALL 1.22 PHASE-2 CHECKS OK")


if __name__ == "__main__":
    main()
