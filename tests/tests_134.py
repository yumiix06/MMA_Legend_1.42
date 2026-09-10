"""v1.34 Part 1 UI/QoL regression checks."""
from mma_legend.models import Fighter
from mma_legend import app, career, notify
from mma_legend.ui import GameConsole


def _f():
    return Fighter.new_player("UI Tester", "B", {"name":"Bulgaria","flag":"BG","bonus":{}}, "MMA", height=180, weight=77)


class C:
    def __init__(self, answers=None): self.answers=list(answers or []); self.out=[]; self.width=50
    def ask(self,p=""): return self.answers.pop(0) if self.answers else "X"
    def print(self,m="",style=None): self.out.append(str(m))
    def header(self,*a,**k): pass
    def warn(self,m): self.out.append(str(m))
    def info(self,m): self.out.append(str(m))
    def good(self,m): self.out.append(str(m))
    def gold(self,m): self.out.append(str(m))
    def pause(self,*a,**k): pass
    def section(self,*a,**k): pass
    def bar_line(self,*a,**k): return ""


def run():
    f=_f()
    rows=app._actions_for(f)
    names=[r[2] for r in rows]
    # v1.36 intentionally restores the flatter pre-hub weekly navigation while
    # keeping the v1.34 fast-training QoL underneath.
    assert "Life" in names and "Team" in names and "Amateur" in names and "Nutrition" in names
    assert "Fighter" in names and "Timeline" in names
    import io, contextlib
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf): GameConsole(width=44,fast=True,color=False).menu_table(rows)
    rendered=buf.getvalue()
    assert "NO TIME" not in rendered and "1 WEEK" not in rendered
    assert "  D) " in rendered and "Amateur" in rendered

    # Invalid training cannot drain energy or spend a week.
    e=f.energy
    assert career.do_training(C(["Q"]), f) is False
    assert f.energy == e

    # Valid training stores a repeatable session; R uses it with one prompt.
    c=C(["A","A"])
    assert career.do_training(c, f) is True
    assert f.last_training_focus == "A" and f.last_training_intensity == "A"
    f.energy=100
    c2=C(["R"])
    assert career.do_training(c2, f) is True
    assert f.energy <= 90

    # Alerts persist until inbox is opened instead of disappearing on dashboard render.
    notify.push(f,"IMPORTANT","Contract expires soon")
    assert len(notify.unread(f)) == 1
    notify.render(C(), f)
    assert len(notify.unread(f)) == 1
    notify.inbox_menu(C(["X"]), f)
    assert len(notify.unread(f)) == 0

    # QoL fields survive save/load.
    f.last_week_report=["Money +$10"]
    f2=Fighter.from_dict(f.to_dict())
    assert f2.last_training_focus == f.last_training_focus
    assert f2.last_week_report == ["Money +$10"]
    print("v1.34 Part 1 UI/QoL checks: PASS")
    return True

if __name__ == "__main__": run()
