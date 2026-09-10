"""v1.35 Part 2 UI/QoL regression checks."""
from mma_legend.models import Fighter
from mma_legend import constants, ux, fights, matchroom


def _f(name="UI Tester"):
    return Fighter.new_player(name, "B", {"name":"Bulgaria","flag":"BG","bonus":{}}, "Wrestling", height=180, weight=77)


class C:
    def __init__(self, answers=None): self.answers=list(answers or []); self.out=[]; self.width=50
    def ask(self,p=""): self.out.append(str(p)); return self.answers.pop(0) if self.answers else "X"
    def print(self,m="",style=None): self.out.append(str(m))
    def header(self,*a,**k): self.out.append(" | ".join(map(str,a)))
    def section(self,*a,**k): self.out.append(" | ".join(map(str,a)))
    def panel(self,title,lines,*a,**k): self.out.append(str(title)); self.out.extend(map(str,lines))
    def warn(self,m): self.out.append(str(m))
    def info(self,m): self.out.append(str(m))
    def good(self,m): self.out.append(str(m))
    def gold(self,m): self.out.append(str(m))
    def pause(self,*a,**k): pass
    def continue_prompt(self,*a,**k): pass
    def bar_line(self,label,val,*a,**k): return f"{label} {val}"


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1,35,0)
    f=_f()

    # New UI state is schema-owned and survives save/load.
    f.ui_compact=True; f.ui_week_report=False; f.ui_tutorial_active=True; f.ui_tutorial_step=2
    f.preferred_gameplan="Wrestle-heavy"; f.last_gameplan={"name":"Wrestle-heavy","td":"Aggressive"}
    f2=Fighter.from_dict(f.to_dict())
    assert f2.ui_compact and not f2.ui_week_report and f2.ui_tutorial_step==2
    assert f2.preferred_gameplan=="Wrestle-heavy" and f2.last_gameplan["td"]=="Aggressive"

    # Career calendar surfaces a booked bout as an exact player-relevant date.
    f.week=20
    f.booked_fight={"date_week":24,"org":"Balkan Combat","event_name":"Balkan Combat 4","opponent_snap":{"name":"Test Rival"}}
    rows=ux.calendar_entries(f)
    assert any(r[0]==24 and r[1]=="FIGHT" and "Test Rival" in r[2] for r in rows)

    # Guided start is non-blocking and progresses only after its actual first-week action.
    g=_f("Guide")
    g.ui_tutorial_active=True; g.ui_tutorial_step=0
    ux.observe_tutorial_choice(g,"A",acted=False); assert g.ui_tutorial_step==0
    ux.observe_tutorial_choice(g,"A",acted=True); assert g.ui_tutorial_step==1
    ux.observe_tutorial_choice(g,"D",acted=False); assert g.ui_tutorial_step==2
    ux.observe_tutorial_choice(g,"T",acted=False); assert g.ui_tutorial_step==3
    ux.observe_tutorial_choice(g,"C",acted=False); assert g.ui_tutorial_complete and not g.ui_tutorial_active

    # Matchup-aware gameplan recommendation has real, testable behavior.
    wrestler=_f("Wrestler"); striker=_f("Striker")
    wrestler.grappling=80; wrestler.ground_control=75; wrestler.submissions=65
    striker.grappling=35; striker.ground_control=35; striker.submission_def=40
    assert fights.recommend_gameplan(wrestler,striker) in ("Wrestle-heavy","Submission Hunter")

    # Fight-prep hub is browse-only; backing out cannot alter career state.
    f.booked_fight={"date_week":24,"org":"Balkan Combat","opponent_snap":striker.to_dict()}
    before=f.to_dict()
    matchroom.show_booked(C(["X"]),f)
    assert f.to_dict()==before

    print("v1.35 Part 2 UI/QoL checks: PASS")
    return True

if __name__ == "__main__": run()
