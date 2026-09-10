"""v1.36.1 focused menu cleanup regression checks."""
from mma_legend.models import Fighter
from mma_legend.world import FighterPool
from mma_legend import app


class C:
    def __init__(self, answers=None): self.answers=list(answers or []); self.out=[]; self.width=50
    def ask(self,p=""): self.out.append(str(p)); return self.answers.pop(0) if self.answers else "X"
    def print(self,m="",style=None): self.out.append(str(m))
    def header(self,*a,**k): self.out.append(" | ".join(map(str,a)))
    def section(self,*a,**k): self.out.append(" | ".join(map(str,a)))
    def warn(self,m): self.out.append(str(m))
    def info(self,m): self.out.append(str(m))
    def good(self,m): self.out.append(str(m))
    def gold(self,m): self.out.append(str(m))
    def pause(self,*a,**k): pass
    def continue_prompt(self,*a,**k): pass
    def bar_line(self,label,val,*a,**k): return f"{label} {val}"


def _f():
    return Fighter.new_player("Menu Tester", "B", {"name":"Bulgaria","flag":"BG","bonus":{}}, "MMA", height=180, weight=77)


def run():
    f=_f(); pool=FighterPool()
    rows=app._actions_for(f)
    labels=[r[2] for r in rows]
    assert "Fight" not in labels and "Fight Prep" not in labels
    assert all("NO TIME" not in str(x) for row in rows for x in row)
    assert [r[1] for r in rows if r[1]] == []

    # Amateur booking is inside Amateur and backing out remains free.
    c=C(["X"]); w=f.week; en=f.energy; f.week_kind="none"
    app._dispatch_action(c, f, pool, "D")
    assert f.week == w and f.energy == en and f.week_kind == "none"

    # Legacy C cannot secretly book an amateur fight anymore.
    c=C([]); app._dispatch_action(c, f, pool, "C")
    assert not getattr(f,"booked_fight",None)
    assert any("Open Amateur" in x for x in c.out)

    # Amateur menu visibly owns the local fight route.
    c=C(["X"]); app._amateur_hub(c, f, pool)
    shown="\n".join(c.out)
    assert "Book local MMA fight" in shown and "Local MMA tournament" in shown and "MMA championships" in shown

    # Once pro, Fight returns to the weekly menu.
    f.pro_debut=True
    assert "Fight" in [r[2] for r in app._actions_for(f)]

    print("v1.36.1 menu cleanup checks: PASS")
    return True

if __name__ == "__main__": run()
