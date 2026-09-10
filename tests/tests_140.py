"""v1.40 Performance & Education regression checks."""
from __future__ import annotations

from unittest.mock import patch

from mma_legend import constants, career, education, events, performance
from mma_legend.models import Fighter
from mma_legend.physiology import effective_stat
from mma_legend.systems15 import take_loan, clamp_money, tick_debt


def _country():
    return {"name":"Bulgaria","flag":"BG","bonus":{}}


def _f(age=16):
    f = Fighter.new_player("Tester", "B", _country(), "Wrestling", height=180, weight=77)
    f.age = age
    f.money = 3000
    f.energy = 90
    f.health = 90
    return f


class Console:
    def __init__(self, answers): self.answers=list(answers); self.out=[]; self.width=44; self.color=False
    def ask(self,prompt=""): self.out.append(str(prompt)); return self.answers.pop(0) if self.answers else "X"
    def print(self,msg="",style=None): self.out.append(str(msg))
    def header(self,*args,**kwargs): self.out.append(" ".join(map(str,args)))
    def section(self,*args,**kwargs): self.out.append(" ".join(map(str,args)))
    def warn(self,msg): self.out.append(str(msg))
    def info(self,msg): self.out.append(str(msg))
    def good(self,msg): self.out.append(str(msg))
    def gold(self,msg): self.out.append(str(msg))
    def pause(self,*a,**k): pass
    def continue_prompt(self,*a,**k): pass


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1, 40, 0)

    # Legal supplements are temporary modifiers, never raw-stat purchases.
    f = _f(20)
    raw = (f.strength, f.ko_power, f.cardio)
    msg = performance.buy_legal(f, "Creatine")
    assert "active" in msg
    assert (f.strength, f.ko_power, f.cardio) == raw
    assert performance.stat_modifier(f, "strength") > 0
    assert effective_stat(f, "strength") >= f.strength
    for _ in range(4):
        performance.tick(f)
    assert "Creatine" not in f.supplement_stack
    assert (f.strength, f.ko_power, f.cardio) == raw

    # Prohibited programs are bounded temporary expression with burden/scrutiny.
    f = _f(22)
    raw_strength = f.strength
    msg = performance.start_program(f, "Anabolic Program")
    assert "started" in msg.lower()
    assert f.strength == raw_strength
    assert performance.stat_modifier(f, "strength") == 5
    before_burden = f.doping_health_burden
    with patch("mma_legend.performance.random.random", return_value=1.0):
        performance.tick(f)
    assert f.doping_health_burden > before_burden
    assert f.strength == raw_strength

    # Sample collection/result states exist; violation consequences are delayed.
    f = _f(24); f.pro_debut=True; f.organization="UFC"; f.room="ufc"
    performance.start_program(f, "Blood-Boosting Program")
    f.doping_sample = {"status":"pending","result_week":f.week,"adverse_probability":1.0}
    with patch("mma_legend.performance.random.random", return_value=0.0):
        performance.tick(f)
    assert f.doping_violations == 1
    assert f.suspension_weeks >= 26
    assert not f.doping_program

    # No debt is possible below 18, including overdraft/event routes.
    f = _f(17); f.debt=500
    assert "unavailable" in take_loan(f, 400).lower()
    assert f.debt == 0
    f.money = -800; f.debt = 100
    clamp_money(f)
    assert f.money == 0 and f.debt == 0
    f.money = 10
    events.apply_effects(f, {"money":-500, "debt":300})
    assert f.money == 0 and f.debt == 0
    f.debt = 200
    tick_debt(f)
    assert f.debt == 0

    # Training shows current skill values directly in the selection column.
    f = _f(17); f.striking=63; f.grappling=71; f.strength=66
    c = Console(["X"])
    assert career.do_training(c, f) is False
    text="\n".join(c.out)
    assert "A) Striking" in text and "63" in text
    assert "C) Grappling" in text and "71" in text
    assert "H) Strength" in text and "66" in text

    # Secondary school has attendance/grade requirements and does not auto-university.
    f = _f(18)
    education.ensure(f)
    f.education_stage="secondary"; f.secondary_completed=False; f.school_grade=70; f.school_attendance=80
    education.tick(f)
    assert f.secondary_completed and f.education_stage == "gap"
    assert f.university_degree is None

    # University is a real 8-semester/240-credit course with scholarship and exams.
    f.national_team=True; f.active_amateur_sport="Wrestling"; f.school_grade=88
    msg=education.enroll(f,"Sports Science")
    assert "Enrolled" in msg
    assert f.education_stage=="university" and f.university_scholarship>=50
    assert education.tuition_per_week(f) < education.DEGREES["Sports Science"]["tuition"]
    f.university_semester_weeks=25
    education.tick(f)
    assert f.university_exam_due
    f.university_average=90; f.university_attendance=95; f.discipline=80
    with patch("mma_legend.education.random.randint", return_value=0):
        assert education.take_exam(f)
    assert f.university_credits==30 and f.university_semester==2 and f.university_semester_weeks==0

    # Pausing freezes semester time; resuming preserves credits.
    f.university_semester_weeks=12
    assert "paused" in education.pause_university(f).lower()
    before=f.university_semester_weeks
    education.tick(f)
    assert f.university_semester_weeks==before
    assert "resumed" in education.resume_university(f).lower()

    # Degree completion exposes small, domain-specific benefits.
    f.education_stage="degree"; f.university_degree="Sports Science"
    assert education.degree_benefit(f,"training_mult",1.0) > 1.0
    f.university_degree="Physiotherapy"
    assert education.degree_benefit(f,"rehab_mult",1.0) < 1.0
    f.university_degree="Law"
    assert education.degree_benefit(f,"contract_mult",1.0) > 1.0

    # Browsing education is free; study is half-week.
    f = _f(17); education.ensure(f); f.week_kind="none"
    c=Console(["X"])
    assert education.menu(c,f) is False and f.week_kind=="none"
    c=Console(["A"])
    assert education.menu(c,f) is True and f.week_kind=="half"

    print("v1.40 performance/education checks: PASS")
    return True


if __name__ == "__main__":
    run()
