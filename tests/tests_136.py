"""v1.36 UI recovery / navigation safety regression checks."""
from contextlib import redirect_stdout
from io import StringIO

from mma_legend.models import Fighter
from mma_legend.world import FighterPool
from mma_legend import app, career, story
from mma_legend.ui import GameConsole


def _f():
    return Fighter.new_player("Navigation Tester", "B", {"name":"Bulgaria","flag":"BG","bonus":{}}, "Combat Sambo", height=185, weight=98)


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
    f=_f(); pool=FighterPool()

    # The reported bug: entering Team and backing out must never spend a week,
    # even when sync_techniques normalizes metadata while the screen opens.
    f.techniques=["Jab"]; f.technique_levels={}
    f.week_kind="none"; w=f.week; en=f.energy
    app._dispatch_action(C(["X"]), f, pool, "T")
    assert f.week == w and f.week_kind == "none" and f.energy == en

    # Life itself is browse-only until a specific action completes.
    f.week_kind="none"; en=f.energy
    app._dispatch_action(C(["X"]), f, pool, "E")
    assert f.week_kind == "none" and f.energy == en

    # People -> Back also costs nothing; opening the submenu alone is not a half-week.
    f.week_kind="none"; en=f.energy
    career.lifestyle_menu(C(["A","X","X"]), f, pool)
    assert f.week_kind == "none" and f.energy == en

    # School's X used to fall through to "skip class". It is now a true no-time Back.
    f.school_status="school"; grade=f.school_grade; en=f.energy; f.week_kind="none"
    assert career.school_menu(C(["X"]), f) is False
    assert f.school_grade == grade and f.energy == en and f.week_kind == "none"

    # Opening Rehab with no injury no longer auto-consumes a recovery week.
    f.injury={}; f.story_flags["injuries"]=[]; f.week_kind="none"; en=f.energy
    career.lifestyle_menu(C(["H","X","X"]), f, pool)
    assert f.week_kind == "none" and f.energy == en

    # Coach advice is browse-only and cannot be farmed for free stats/rapport.
    iq=f.fight_iq; rel=f.relationships.get("coach",50)
    career.coach_talk_menu(C(["C"]), f)
    assert f.fight_iq == iq and f.relationships.get("coach",50) == rel

    # A real Team practice does mark the week as spent through the explicit contract.
    f.techniques=["Jab"]; f.technique_levels={"Jab":1}; f.energy=100; f.week_kind="none"
    app._dispatch_action(C(["R"]), f, pool, "T")
    assert f.week_kind == "full" and f.energy < 100

    # UI menus use ANSI colour when enabled, but remain readable plain text without it.
    buf=StringIO()
    with redirect_stdout(buf):
        GameConsole(width=50, fast=True, color=True).menu_table([("A","🏋️","Train",""),("H","","Stats","")])
    rendered=buf.getvalue()
    assert "\x1b[" in rendered and "Train" in rendered and "NO TIME" not in rendered

    print("v1.36 UI recovery/navigation checks: PASS")
    return True


if __name__ == "__main__": run()
