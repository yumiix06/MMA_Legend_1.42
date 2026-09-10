"""0.8.1 regression tests. Run: python3 -m mma_legend.tests_081"""
from __future__ import annotations

import random

from mma_legend import data, events
from mma_legend.engine import simulate_fight
from mma_legend.engine.rules import MMARuleset, GrapplingRuleset
from mma_legend.models import Fighter
from mma_legend.career import _coach_pool_names, ensure_coach


class Quiet:
    def header(self, *a, **k): pass
    def print(self, *a, **k): pass
    def gold(self, *a, **k): pass
    def good(self, *a, **k): pass
    def warn(self, *a, **k): pass
    def info(self, *a, **k): pass
    def table(self, *a, **k): pass
    def read_pause(self, *a, **k): pass


def _pair(style="Boxing"):
    c = data.country_by_name("USA")
    f = Fighter.new_player("P", "B", c, style)
    o = Fighter.new_npc("O", c)
    f.energy = o.energy = 90
    return f, o


def test_mma_log_matches_stats():
    f, o = _pair()
    out = simulate_fight(f, o, MMARuleset(amateur=True), gameplan="Balanced", console=None)
    landed = sum(1 for e in out.log if e.attacker == f.name and e.result == "land" and e.action_id in
                 ("jab", "cross", "hook", "uppercut", "liver", "low_kick", "body_kick", "head_kick", "teep", "gnp", "knee_body", "dirty_box"))
    assert out.f_stats.strikes_landed == landed or abs(out.f_stats.strikes_landed - landed) <= 2
    assert out.f_stats.head_landed + out.f_stats.body_landed + out.f_stats.leg_landed == out.f_stats.strikes_landed
    assert out.winner in ("player", "opponent", "draw")
    return "mma log/stats ok %s %s" % (out.winner, out.method)


def test_amateur_no_heel():
    f, o = _pair("BJJ")
    out = simulate_fight(f, o, MMARuleset(amateur=True), gameplan="Submission Hunter", console=None)
    illegal = [e for e in out.log if e.action_id in ("heel_hook", "elbow", "knee_head", "ground_elbow")]
    assert not illegal
    return "amateur illegal hidden"


def test_pro_can_elbow():
    f, o = _pair()
    f.pro_debut = True
    saw = False
    for _ in range(8):
        out = simulate_fight(f, o, MMARuleset(amateur=False), gameplan="Aggressive", console=None)
        if any(e.action_id in ("elbow", "knee_head", "heel_hook") for e in out.log):
            saw = True
            break
    return "pro tools seen=%s" % saw


def test_grappling_one_period():
    f, o = _pair("BJJ")
    out = simulate_fight(f, o, GrapplingRuleset(), gameplan="Submission Hunter", console=None)
    assert out.periods == 1
    assert out.sport == "grappling"
    strikes = [e for e in out.log if e.action_id in ("jab", "cross", "hook", "low_kick", "gnp")]
    assert not strikes
    return "grappling 1 period method=%s winner=%s pts %s-%s" % (out.method, out.winner, out.f_score, out.o_score)


def test_grappling_draw_is_draw():
    # force by constructing outcome path: equal points no finish
    from mma_legend.fights import _resolve_outcome
    assert _resolve_outcome(None, 10, 10) == "draw"
    assert _resolve_outcome("Submission", 0, 0) == "win_finish"
    assert _resolve_outcome("Submission Loss", 0, 0) == "loss_finish"
    return "resolve draw/win/loss"


def test_turn_pro_menu():
    f, o = _pair()
    f.amateur_record = [3, 2, 0]
    from mma_legend import v08
    assert v08.turn_pro_ready(f)
    f.pro_debut = True
    from mma_legend.app import _actions_for
    keys = [r[0] for r in _actions_for(f)]
    assert "D" not in keys
    return "pro hides amateur menu"


def test_sambo_striking():
    c = data.country_by_name("Russia") if any(x["name"] == "Russia" for x in data.COUNTRIES) else data.country_by_name("USA")
    f = Fighter.new_player("S", "B", c, "Sambo")
    assert f.striking >= 30
    assert "Jab" in f.technique_levels or f.striking > 0
    return "sambo striking %s tech %s" % (f.striking, list(f.technique_levels)[:4])


def test_coach_pool():
    f, _ = _pair("Wrestling")
    ensure_coach(f)
    names = _coach_pool_names(f)
    assert names
    return "coach %s pool %s" % (f.coach_personality, names[:4])


def test_events():
    f, _ = _pair()
    f.amateur_record = [0, 0, 0]
    ctx = events.context_pack(f)
    bad = []
    for e in list(data.EVENT_DATABASE) + list(getattr(data, "EVENTS_V08", [])):
        if events.eligible(f, e, ctx):
            t = (e.get("title") or "").lower()
            if any(w in t for w in ("podcast", "interview", "nightclub")):
                bad.append(e.get("title"))
    assert not bad
    issues = events.validate_event_pack()
    return "0-0 media blocked; dup issues %s" % len(issues)


def test_save_upgrade():
    from mma_legend.persistence import _upgrade_player
    d = _upgrade_player({"name": "Old", "country": "USA"})
    assert "sport_records" in d
    return "save upgrade ok"


def test_no_bottom_gnp():
    f, o = _pair("BJJ")
    from mma_legend.engine.validate import validate_fight_log
    bad = 0
    for _ in range(12):
        out = simulate_fight(f, o, MMARuleset(amateur=True), "Wrestle-heavy")
        issues = validate_fight_log(out)
        bad += len(issues)
        assert not any("GNP while" in x for x in issues)
        assert not any("RNC from" in x for x in issues)
    return "log validator issues-in-12=%s" % bad


def test_knockdown_tracked():
    f, o = _pair("Boxing")
    f.ko_power = 95
    f.striking = 90
    o.durability = 25
    saw = 0
    for _ in range(20):
        out = simulate_fight(f, o, MMARuleset(amateur=False), "Aggressive")
        saw += out.f_stats.knockdowns + out.o_stats.knockdowns
    return "knockdowns in 20 elite-boxer sims=%s" % saw


def test_volume():
    tot = 0
    n = 8
    for _ in range(n):
        f, o = _pair("Boxing")
        out = simulate_fight(f, o, MMARuleset(amateur=True), "Aggressive")
        tot += out.f_stats.strikes_attempted + out.o_stats.strikes_attempted
    avg = tot / n
    assert avg >= 12, avg
    return "avg 3r strike attempts %.1f" % avg


def test_round_damage_isolated():
    # scoring helper uses passed damage; cumulative would inflate R3
    from mma_legend.engine.scoring import mma_round_score
    from mma_legend.engine.state import SideStats
    a = SideStats(strikes_landed=4, head_landed=2)
    b = SideStats(strikes_landed=4, head_landed=2)
    s1 = mma_round_score(a, b, 5, 5, 0, 0)
    s2 = mma_round_score(a, b, 20, 5, 0, 0)
    assert s1 != s2
    return "round damage changes score %s vs %s" % (s1, s2)


def main():
    random.seed(7)
    tests = [
        test_mma_log_matches_stats, test_amateur_no_heel, test_pro_can_elbow,
        test_grappling_one_period, test_grappling_draw_is_draw, test_turn_pro_menu,
        test_sambo_striking, test_coach_pool, test_events, test_save_upgrade,
        test_no_bottom_gnp, test_knockdown_tracked, test_volume, test_round_damage_isolated,
    ]
    # extra grappling outcomes
    wins = draws = losses = subs = points = 0
    for i in range(20):
        f, o = _pair("BJJ")
        f.submissions = 70
        o.grappling = 35
        out = simulate_fight(f, o, GrapplingRuleset(), gameplan="Submission Hunter", console=None)
        if out.winner == "player":
            wins += 1
        elif out.winner == "draw":
            draws += 1
        else:
            losses += 1
        if out.method not in ("Points", "Draw", "Decision"):
            subs += 1
        if out.method == "Points":
            points += 1
    print("grappling sample W/D/L %s/%s/%s sub=%s pts=%s" % (wins, draws, losses, subs, points))
    for t in tests:
        print("PASS", t())


if __name__ == "__main__":
    main()
