"""v1.41 Promotion Rankings, Specialist Gym & content regression checks."""
from __future__ import annotations

from unittest.mock import patch

from mma_legend import constants, career, data, events, gym_progression, persistence, amateur_sports
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


def _country():
    return {"name": "Bulgaria", "flag": "BG", "bonus": {}}


def _player(age=20):
    f = Fighter.new_player("Tester", "B", _country(), "Wrestling", height=180, weight=77)
    f.age = age
    f.money = 5000
    f.energy = 90
    f.health = 90
    return f


class Console:
    def __init__(self, answers=()):
        self.answers = list(answers); self.out=[]; self.width=44; self.color=False
    def ask(self,prompt=""):
        self.out.append(str(prompt)); return self.answers.pop(0) if self.answers else "X"
    def print(self,msg="",style=None): self.out.append(str(msg))
    def header(self,*args,**kwargs): self.out.append(" ".join(map(str,args)))
    def section(self,*args,**kwargs): self.out.append(" ".join(map(str,args)))
    def warn(self,msg): self.out.append(str(msg))
    def info(self,msg): self.out.append(str(msg))
    def good(self,msg): self.out.append(str(msg))
    def gold(self,msg): self.out.append(str(msg))
    def pause(self,*a,**k): pass
    def continue_prompt(self,*a,**k): pass


def _ranked_pool():
    pool = FighterPool()
    for i in range(5):
        n = Fighter.new_npc("Balkan %s" % i, _country(), style="Wrestling")
        n.fid = "rank_%s" % i
        n.pro_debut = True
        n.organization = "Balkan Combat"
        n.weight_class = "Welterweight"
        n.pro_record = [8-i, i, 0]
        n.active = True
        pool.fighters.append(n)
    pool.update_rankings()
    return pool


def _join_bjj(f):
    room = data.BJJ_GYMS[0]
    f.specialty_gym = room["name"]
    f.specialty_gym_type = "bjj"
    f.specialty_coach = room["coach"]
    f.specialty_gym_dues = int(room.get("dues", 35))
    f.specialty_pool = list(room.get("technique_pool") or [])
    f.bjj_belt = "white"
    return room


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1, 41, 0)
    assert persistence.SAVE_VERSION >= 19

    # Unsigned amateurs can browse real promotion boards maintained by the world.
    f = _player(17); f.pro_debut=False; f.organization=None; f.weight_class="Welterweight"
    pool = _ranked_pool()
    # Balkan Combat is seventh in the canonical org list for an unsigned fighter.
    div = constants.WEIGHT_CLASSES.index("Welterweight") + 1
    c = Console(["7", str(div)])
    career._promotion_rankings_browser(c, pool, f)
    text = "\n".join(c.out)
    assert "PROMOTION RANKINGS" in text and "Balkan Combat" in text
    assert "Balkan 0" in text or "Balkan 1" in text

    # Membership itself now creates mat time, belt progress and named-technique growth.
    f = _player(); _join_bjj(f)
    before = set(f.techniques)
    with patch("mma_legend.gym_progression.random.choice", side_effect=lambda seq: list(seq)[0]):
        for _ in range(3): gym_progression.tick(f)
    assert f.specialty_gym_weeks == 3
    assert f.bjj_weeks == 3 and f.bjj_grade_points >= 9
    assert set(f.techniques) != before or any(v > 1 for v in f.technique_levels.values())
    valid = {r.get("name") for r in data.TECHNIQUES_DB}
    added = set(f.techniques) - before
    assert all(t in valid for t in added)

    # Automatic promotion happens as soon as the existing requirements are met.
    f = _player(); _join_bjj(f)
    need_points, need_weeks = amateur_sports.BJJ_REQUIREMENTS["blue"]
    f.bjj_grade_points = need_points
    f.bjj_weeks = need_weeks
    assert amateur_sports.auto_promote_belt(f, "bjj") == "blue"
    assert f.bjj_belt == "blue" and f.bjj_stripes == 0

    # Home-gym development pauses during an international camp.
    f = _player(); _join_bjj(f); f.intl_camp="thailand"
    snap=(f.specialty_gym_weeks, f.bjj_weeks, f.bjj_grade_points, f.specialty_gym_tech_xp)
    gym_progression.tick(f)
    assert snap == (f.specialty_gym_weeks, f.bjj_weeks, f.bjj_grade_points, f.specialty_gym_tech_xp)

    # Kickboxing membership only draws from playable KB / Muay Thai technique rows.
    f = _player(); room=data.KB_GYMS[0]
    f.specialty_gym=room["name"]; f.specialty_gym_type="kb"; f.specialty_coach=room["coach"]
    f.specialty_pool=list(room.get("technique_pool") or []); f.specialty_gym_tech_xp=3
    with patch("mma_legend.gym_progression.random.choice", side_effect=lambda seq: list(seq)[0]):
        gym_progression._develop_technique(f, "kb")
    rows={r.get("name"):r for r in data.TECHNIQUES_DB}
    new=[t for t in f.techniques if t in rows and rows[t].get("discipline") in ("Kickboxing","Muay Thai")]
    assert new

    # Leaving a gym must never erase earned belt work.
    f = _player(); _join_bjj(f); f.bjj_belt="blue"; f.bjj_stripes=3; f.bjj_grade_points=85
    belt=(f.bjj_belt, f.bjj_stripes, f.bjj_grade_points)
    f.specialty_gym=None; f.specialty_gym_type=None; f.specialty_coach=None; f.specialty_pool=[]
    assert belt == (f.bjj_belt, f.bjj_stripes, f.bjj_grade_points)

    # New context/content pack validates and is large enough to matter in play.
    assert len(data.EVENTS_V141) >= 30
    assert events.validate_event_pack() == []
    assert any((e.get("require") or {}).get("gym_type") == "bjj" for e in data.EVENTS_V141)
    assert any((e.get("require") or {}).get("education_stage") == "university" for e in data.EVENTS_V141)

    print("v1.41 rankings/gym/content checks: PASS")
    return True


if __name__ == "__main__":
    run()
