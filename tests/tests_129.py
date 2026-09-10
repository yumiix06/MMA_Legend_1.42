"""v1.29 gates: focus-aware amateur calendar, history and simulation modes."""
from __future__ import annotations

from types import SimpleNamespace

from mma_legend import amateur_sports, app, data, persistence
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


class Quiet:
    width = 44
    def __init__(self, answers=()):
        self.answers = list(answers); self.lines = []
    def ask(self, *args, **kwargs):
        return self.answers.pop(0) if self.answers else "X"
    def _add(self, value="", *args, **kwargs): self.lines.append(str(value))
    print = info = warn = good = gold = header = section = _add
    def pause(self, *args, **kwargs): pass
    def auto_pause(self, *args, **kwargs): pass
    def continue_prompt(self, *args, **kwargs): pass


def _player(sport="Judo"):
    p = Fighter.new_player("Test Fighter", "B", data.country_by_name("Bulgaria"),
                           sport, 180, 77)
    amateur_sports.ensure(p)
    p.active_amateur_sport = sport
    p.story_flags["compete_in"] = sport
    return p


def test_hub_and_dashboard_expose_only_active_sport():
    side = _player("Judo")
    q = Quiet(["X"]); app._amateur_hub(q, side, FighterPool())
    shown = "\n".join(q.lines)
    assert "Local Judo match" in shown and "Local MMA" not in shown
    labels = [row[2] for row in app._actions_for(side)]
    assert "Fight" not in labels and "Book Amateur Fight" not in labels

    mma = _player("MMA")
    q = Quiet(["X"]); app._amateur_hub(q, mma, FighterPool())
    shown = "\n".join(q.lines)
    assert "Book local MMA fight" in shown and "Local MMA tournament" in shown and "Local Judo match" not in shown
    return "amateur hub and dashboard hide MMA while focused elsewhere, and hide side-sport entries in MMA"


def test_calendar_has_real_dates_and_four_year_olympics():
    for sport in amateur_sports.SPORT_KEYS:
        if sport == "MMA":
            continue
        p = _player(sport); p.week = 1
        key = amateur_sports.key_for(sport)
        p.sport_experience[key] = 500
        p.sport_national_teams[key] = True
        p.sport_championships[key]["continental"]["gold"] = 1
        events = amateur_sports.calendar_entries(p, sport, years=5)
        year_one = [e for e in events if e["career_year"] == 1]
        assert sum(e["level"] == "regional" for e in year_one) == 0  # Bulgaria is a small federation
        assert sum(e["level"] == "national" for e in year_one) == 2
        assert sum(e["level"] == "continental" for e in year_one) == 1
        assert sum(e["level"] == "world" for e in year_one) == 1
        assert any(e["name"].endswith("European Championships") for e in year_one if e["level"] == "continental")
        olympics = [e for e in events if e["level"] == "olympic"]
        if sport in amateur_sports.OLYMPIC_SPORTS:
            assert olympics and olympics[0]["career_year"] == 4 and olympics[0]["season_week"] == 40
        else:
            assert not olympics
    return "small-country calendar skips regionals and carries two Nationals, one European, Worlds and the next valid Olympics"


def test_registration_is_bound_to_sport_and_runs_on_event_week():
    p = _player("Judo"); p.week = 4; p.sport_experience["judo"] = 100
    q = Quiet(["1"])
    assert amateur_sports.competition_calendar(q, p, FighterPool())
    assert p.competition_sport == "Judo" and p.competition_level == "national"
    assert p.competition_due_week == 12
    assert not amateur_sports.choose_sport(Quiet(["C"]), p)
    assert p.active_amateur_sport == "Judo"

    called = {}
    original = amateur_sports.championship
    def fake(console, fighter, pool, **kwargs):
        called.update(kwargs); return True
    amateur_sports.championship = fake
    try:
        p.week = 12
        assert amateur_sports.check_scheduled_competition(Quiet(["C"]), p, FighterPool())
    finally:
        amateur_sports.championship = original
    assert called["level_override"] == "national" and called["mode"] == "Instant"
    assert p.competition_signup is None and p.competition_due_week == 0
    return "registration persists its sport/date, blocks focus drift and resolves only on event week"


def test_side_fight_mode_and_history_metadata():
    p = _player("Combat Sambo"); p.energy = 100; p.health = 100
    stats = SimpleNamespace(grappling_points=5, as_dict=lambda: {"strikes_landed": 8})
    outcome = SimpleNamespace(winner="player", method="Decision", end_period=3,
                              f_stats=stats, o_stats=SimpleNamespace(grappling_points=1))
    original = amateur_sports.simulate_fight
    amateur_sports.simulate_fight = lambda *args, **kwargs: outcome
    try:
        assert amateur_sports.compete(Quiet(), p, FighterPool(), mode="Instant",
                                      event_name="Combat Sambo National Championships",
                                      competition_level="national")
    finally:
        amateur_sports.simulate_fight = original
    row = p.fight_history[-1]
    assert row["sport"] == "combat_sambo" and row["mode"] == "Instant"
    assert row["competition_level"] == "national" and row["week"] == p.week
    assert amateur_sports.recent_fights(p, "Combat Sambo")[0].startswith("W vs ")
    return "other-sport fights support Instant mode and retain dated sport/event/opponent history"


def test_save_v15_owns_scheduled_sport_fields():
    p = _player("Boxing")
    p.competition_signup = "Boxing National Championships"
    p.competition_sport = "Boxing"; p.competition_level = "national"; p.competition_due_week = 12
    upgraded = persistence._upgrade_player(p.to_dict())
    assert persistence.SAVE_VERSION >= 19
    assert upgraded["competition_sport"] == "Boxing"
    assert upgraded["competition_level"] == "national" and upgraded["competition_due_week"] == 12
    return "save v17 preserves the scheduled competition's sport, level and absolute date"


def main():
    for test in (
        test_hub_and_dashboard_expose_only_active_sport,
        test_calendar_has_real_dates_and_four_year_olympics,
        test_registration_is_bound_to_sport_and_runs_on_event_week,
        test_side_fight_mode_and_history_metadata,
        test_save_v15_owns_scheduled_sport_fields,
    ):
        print("PASS", test())
    print("ALL 1.29 FOCUS-AWARE AMATEUR CALENDAR CHECKS OK")


if __name__ == "__main__":
    main()
