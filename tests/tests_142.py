"""v1.42 Taekwondo and kicking-system regression checks."""
from __future__ import annotations
import random
from unittest.mock import patch
from mma_legend import constants, persistence, amateur_sports, data, gym_progression, events, combat_intelligence
from mma_legend.models import Fighter
from mma_legend.engine import TaekwondoRuleset, simulate_fight

COUNTRY={"name":"Bulgaria","flag":"BG","bonus":{}}

def fighter(name="Tester"):
    f=Fighter.new_player(name,"B",COUNTRY,"Taekwondo",height=182,weight=74)
    f.age=20; f.is_player=False; f.money=5000; f.energy=90; f.health=95
    f.kicks=72; f.speed=70; f.distance_management=68; f.striking_def=60; f.fight_iq=62; f.ko_power=55; f.durability=62
    return f

def run():
    assert constants.GAME_VERSION == "1.42.0"
    assert persistence.SAVE_VERSION == 20
    assert "Taekwondo" in amateur_sports.SPORT_KEYS
    assert "Taekwondo" in amateur_sports.OLYMPIC_SPORTS
    r=TaekwondoRuleset()
    assert r.periods == 3 and r.period_seconds == 120
    assert "low_kick" not in r.allowed_actions and "double_leg" not in r.allowed_actions and "side_kick" in r.allowed_actions
    assert amateur_sports.weight_label("Taekwondo",74)=="-74kg"
    # Taekwondo is a first-class background, not only a side-sport menu entry.
    assert "Taekwondo" in constants.DISCIPLINES
    starter=Fighter.new_player("Starter","B",COUNTRY,"Taekwondo",height=182,weight=74)
    assert starter.kicks > starter.striking and "Side Kick" in starter.techniques
    dummy=fighter("Dummy"); dummy.striking_def=45; dummy.distance_management=50
    starter.opponent_read=20; starter.kicks=78; starter.distance_management=72
    assert combat_intelligence.coach_recommendation(starter,dummy) == "Taekwondo Kicking"
    # Named techniques are playable and map into the new action family.
    names={x.get("name") for x in data.TECHNIQUES_DB}
    for n in ("Side Kick","Spinning Back Kick","Spinning Hook Kick","Axe Kick","Tornado Kick","Roundhouse to Head"):
        assert n in names
    # Simulated kyorugi never leaks illegal MMA/kickboxing actions.
    a,b=fighter("A"),fighter("B")
    for who in (a,b):
        for n in ("Side Kick","Roundhouse to Body","Roundhouse to Head","Spinning Back Kick","Spinning Hook Kick","Axe Kick","Tornado Kick"):
            who.learn_technique(n)
    random.seed(42)
    out=simulate_fight(a,b,r,console=None,interactive=False)
    assert out.method.startswith("Round Points") or out.method.startswith("KO") or out.method.startswith("TKO")
    assert all(e.action_id in r.allowed_actions for e in out.log)
    assert out.f_stats.technical_points >= 0 and out.o_stats.technical_points >= 0
    # Taekwondo gym membership progresses belt and teaches Taekwondo syllabus automatically.
    f=fighter(); room=data.TKD_GYMS[0]
    f.specialty_gym=room["name"]; f.specialty_gym_type="tkd"; f.specialty_coach=room["coach"]
    f.specialty_pool=list(room.get("technique_pool") or []); f.tkd_belt="white"
    before=set(f.techniques)
    with patch("mma_legend.gym_progression.random.choice", side_effect=lambda seq:list(seq)[0]):
        for _ in range(3): gym_progression.tick(f)
    assert f.tkd_weeks==3 and f.tkd_grade_points>=9
    assert set(f.techniques)!=before or any(v>1 for v in f.technique_levels.values())
    # New events validate and include TKD/kicking contexts.
    assert len(data.EVENTS_V142) >= 15
    assert events.validate_event_pack()==[]
    assert any((e.get("require") or {}).get("gym_type")=="tkd" for e in data.EVENTS_V142)
    assert any((e.get("require") or {}).get("active_sport")=="Taekwondo" for e in data.EVENTS_V142)
    print("v1.42 taekwondo/kicking checks: PASS")
    return True

if __name__ == "__main__": run()
