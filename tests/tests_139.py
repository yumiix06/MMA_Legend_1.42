"""v1.39 combat intelligence regression checks."""
from __future__ import annotations

import random

from mma_legend import combat_intelligence as CI, constants
from mma_legend.engine.fight import simulate_fight
from mma_legend.engine.rules import MMARuleset
from mma_legend.models import Fighter


def _country():
    return {"name": "Bulgaria", "flag": "BG", "bonus": {}}


def make(name="A", style="Wrestling", iq=70, adapt=70):
    f = Fighter.new_player(name, "B", _country(), style, height=180, weight=77)
    f.is_player = name == "Player"
    f.fid = name
    f.pro_debut = True
    f.fight_details = "Instant"
    f.fight_iq = iq
    f.adaptability = adapt
    f.discipline = 70
    f.mental_toughness = 70
    f.confidence = 65
    f.energy = 90
    f.cardio = 70
    f.striking = 62
    f.kicks = 58
    f.grappling = 68
    f.submissions = 58
    f.ground_control = 66
    f.takedown_def = 64
    f.striking_def = 62
    f.submission_def = 62
    f.speed = 65
    f.strength = 65
    f.ko_power = 60
    f.durability = 65
    f.distance_management = 62
    return f


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1, 39, 0)

    player = make("Player", "Wrestling", 82, 84)
    opp = make("Opponent", "Boxing", 55, 48)
    opp.is_player = False

    # Live reads matter: repeated shots make a prepared/intelligent fighter
    # prefer anti-wrestling responses more strongly.
    state = CI.make_state(player, opp)
    base = CI.action_multiplier(
        state, "sprawl", gas=80, opponent_gas=80,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=2, total_rounds=3, score_margin=0)
    for _ in range(4):
        CI.observe(state, self_action=False, action="double_leg", result="miss")
    read = CI.action_multiplier(
        state, "sprawl", gas=80, opponent_gas=80,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=2, total_rounds=3, score_margin=0)
    assert read > base * 1.10

    # Damage-aware decisions suppress compromised weapons rather than merely
    # applying an accuracy penalty after the AI already chose them.
    healthy = CI.action_multiplier(
        state, "head_kick", gas=70, opponent_gas=70,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=2, total_rounds=3, score_margin=0)
    hurt = CI.action_multiplier(
        state, "head_kick", gas=70, opponent_gas=70,
        my_damage={"head":0,"body":0,"legs":35,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=2, total_rounds=3, score_margin=0)
    assert hurt < healthy * 0.8

    # Score awareness: a fighter behind in the final round takes more variance.
    chase = CI.action_multiplier(
        state, "hook", gas=60, opponent_gas=60,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=3, total_rounds=3, score_margin=-2)
    bank = CI.action_multiplier(
        state, "hook", gas=60, opponent_gas=60,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=3, total_rounds=3, score_margin=2)
    assert chase > bank

    # Camp preparation is matchup-specific and bounded.
    opp.grappling = 82; opp.ground_control = 80; opp.submissions = 78
    prep = CI.preparation_blueprint(player, opp, "Wrestling")
    prep["readiness"] = 8
    player.camp_preparation = prep
    assert 0 < CI.takedown_defense_bonus(player, opp, "double_leg") <= 0.05
    assert CI.takedown_entry_bonus(player, opp, "double_leg") <= 0.04
    before = dict(player.camp_preparation)
    CI.advance_preparation(player)
    assert player.camp_preparation["weeks"] == before["weeks"] + 1
    assert player.camp_preparation["readiness"] > before["readiness"]

    # Scouting reveals information in layers rather than showing exact stats at 0 read.
    player.opponent_read = 0
    low = CI.scout_lines(player, opp)
    player.opponent_read = 18
    high = CI.scout_lines(player, opp)
    assert len(high) > len(low)
    assert any("Likely approach" in line for line in high)

    # Low adaptability can stay stubborn when the situation is not urgent;
    # elite adaptability changes a failing takedown plan.
    low_iq = make("LowIQ", "Wrestling", 25, 20); low_iq.is_player = False
    low_state = CI.make_state(low_iq, opp)
    for _ in range(4):
        CI.observe(low_state, self_action=True, action="double_leg", result="miss")
    plan = {"name":"Wrestle-heavy","td":"Aggressive","range":"pocket","pace":"mid","target":"body","defense":"guard"}
    low_plan, _ = CI.between_round_adjustment(
        low_iq, opp, low_state, plan, round_lost=True, gas=70, opponent_gas=70,
        score_margin=-1, my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0})
    assert low_plan["td"] == "Aggressive"

    hi_state = CI.make_state(player, opp)
    for _ in range(4):
        CI.observe(hi_state, self_action=True, action="double_leg", result="miss")
    hi_plan, reason = CI.between_round_adjustment(
        player, opp, hi_state, plan, round_lost=True, gas=70, opponent_gas=70,
        score_margin=-1, my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0})
    assert hi_plan["td"] == "Safe" and "shots" in reason.lower()

    # Scrambles are contested by actual attributes, not a blind transition coin flip.
    strong = make("Strong", "Wrestling", 85, 85); strong.is_player = False
    weak = make("Weak", "Boxing", 35, 35); weak.is_player = False
    strong.grappling=90; strong.speed=85; strong.strength=82
    weak.grappling=35; weak.ground_control=35; weak.speed=40; weak.strength=45
    seq = iter([0.9, 0.01, 0.01])  # no stand, attacker wins top contest, advances position
    pos, outcome = CI.scramble_outcome(strong, weak, "turtle", attacker_gas=80, defender_gas=55, rng=lambda: next(seq))
    assert outcome == "attacker_top" and pos in {"half_guard", "side", "back"}


    # Tactical camp focuses now separate offensive wrestling from defensive
    # anti-wrestling preparation.
    anti = CI.preparation_blueprint(player, opp, "Anti-Wrestling")
    wrest = CI.preparation_blueprint(player, opp, "Wrestling")
    assert anti["anti_wrestling"] > wrest["anti_wrestling"]
    assert wrest["close_distance"] > anti["close_distance"]

    # A strong, fresh chain wrestler can convert a stuffed shot into a real
    # clinch-range secondary takedown instead of merely entering the clinch.
    chain = make("Chain", "Wrestling", 88, 86); chain.is_player = False
    chain.grappling = 90; chain.strength = 82; chain.technique_levels = {"Single Leg": 3, "Inside Trip": 2}
    seq = iter([0.01, 0.01])
    follow = CI.chain_takedown_followup(chain, weak, "double_leg", gas=85,
                                        plan={"td":"Aggressive"}, rng=lambda: next(seq))
    assert follow in {"single_leg", "trip", "throw", "double_leg"}

    # Damage exploitation is tactical: once a leg is visibly compromised,
    # intelligent fighters weight attacks on it more strongly.
    clean_hunt = CI.action_multiplier(
        hi_state, "low_kick", gas=70, opponent_gas=70,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":0,"cuts":0},
        round_no=2, total_rounds=3, score_margin=0)
    hurt_hunt = CI.action_multiplier(
        hi_state, "low_kick", gas=70, opponent_gas=70,
        my_damage={"head":0,"body":0,"legs":0,"cuts":0},
        opponent_damage={"head":0,"body":0,"legs":26,"cuts":0},
        round_no=2, total_rounds=3, score_margin=0)
    assert hurt_hunt > clean_hunt * 1.08

    # Richer scramble outcomes can produce back control from turtle/front
    # headlock exchanges when the actor has a large scrambling edge.
    seq = iter([0.99, 0.01, 0.01])
    pos2, out2 = CI.scramble_outcome(strong, weak, "turtle", attacker_gas=90, defender_gas=45, rng=lambda: next(seq))
    assert out2 == "attacker_top" and pos2 == "back"

    # End-to-end fight integration exposes bout-scoped intelligence telemetry.
    random.seed(139)
    player.camp_preparation = CI.preparation_blueprint(player, opp, "Complete")
    player.camp_preparation["readiness"] = 6
    out = simulate_fight(player, opp, MMARuleset(amateur=False), gameplan="Balanced", console=None, interactive=False)
    assert isinstance(out.intelligence, dict) and "player_prep" in out.intelligence
    assert isinstance(out.intelligence.get("player_actions"), dict)
    assert isinstance(out.intelligence.get("opponent_actions"), dict)
    assert isinstance(out.f_adjustments, list) and isinstance(out.o_adjustments, list)
    assert isinstance(player.last_fight_adjustments, list)

    print("v1.39 combat intelligence checks: PASS")
    return True


if __name__ == "__main__":
    run()
