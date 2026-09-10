"""v1.37 UI freeze/polish regression checks."""
import contextlib, io
from mma_legend import app, constants, ui, amateur_sports
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


def _f():
    return Fighter.new_player("UI Tester", "B", {"name":"Bulgaria","flag":"🇧🇬","bonus":{}}, "Judo", height=180, weight=77)


def _render(f, compact=False):
    f.ui_compact=compact
    c=ui.GameConsole(width=44, fast=True, color=False)
    b=io.StringIO()
    with contextlib.redirect_stdout(b): ui.render_dashboard(c,f)
    return b.getvalue()


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1, 37, 0)

    # Weekly menu uses only a small number of recognition emojis.
    f=_f(); rows=app._actions_for(f)
    icons=[r[1] for r in rows if r[1]]
    assert icons == []

    # Compact mode is a real behavior now, not a dead preference.
    f.pro_debut=True; f.organization="LFA"; f.week=20
    f.booked_fight={"org":"LFA","date_week":24,"opponent_snap":{"name":"Opponent"},"title":True,"short_notice":True}
    normal=_render(f,False); compact=_render(f,True)
    assert len(compact.splitlines()) < len(normal.splitlines())
    assert max(map(len, normal.splitlines())) <= 44 and max(map(len, compact.splitlines())) <= 44
    assert "Weight:" in normal and "Contract:" not in normal  # no deal signed
    assert "Weight:" not in compact

    # Color preference is declared/persistent through Fighter serialization.
    f.ui_color=False
    loaded=Fighter.from_dict(f.to_dict())
    assert loaded.ui_color is False

    # Belt progress is concise and advances toward the next grade.
    f.bjj_belt="white"; f.bjj_grade_points=30; f.bjj_weeks=7
    line=amateur_sports.belt_progress_line(f,"bjj")
    assert "toward Blue Belt" in line and "%" in line

    # Browse-only Team/Life remain free after the polish pass.
    class C:
        def __init__(self, answers): self.answers=list(answers); self.out=[]; self.width=44; self.color=False
        def ask(self,p=""): self.out.append(p); return self.answers.pop(0) if self.answers else "X"
        def print(self,m="",style=None): self.out.append(str(m))
        def header(self,*a,**k): self.out.append(" ".join(map(str,a)))
        def section(self,*a,**k): self.out.append(" ".join(map(str,a)))
        def warn(self,m): self.out.append(str(m))
        def info(self,m): self.out.append(str(m))
        def good(self,m): self.out.append(str(m))
        def gold(self,m): self.out.append(str(m))
        def pause(self,*a,**k): pass
        def continue_prompt(self,*a,**k): pass
    p=FighterPool(); f2=_f(); f2.week_kind="none"; w=f2.week; en=f2.energy
    app._dispatch_action(C(["X"]),f2,p,"T")
    assert f2.week==w and f2.energy==en and f2.week_kind=="none"
    app._dispatch_action(C(["X"]),f2,p,"E")
    assert f2.week==w and f2.energy==en and f2.week_kind=="none"
    app._dispatch_action(C(["X"]),f2,p,"P")
    assert f2.week==w and f2.energy==en and f2.week_kind=="none"

    print("v1.37 UI freeze checks: PASS")
    return True

if __name__ == "__main__": run()
