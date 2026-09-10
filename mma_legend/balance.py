"""Balance lab. python3 -m mma_legend.balance"""
from __future__ import annotations

import collections
import random
from typing import Optional

from . import constants as C
from .data import country_by_name
from .engine import simulate_fight
from .engine.rules import MMARuleset, GrapplingRuleset
from .models import Fighter


def _pair(style_a="Boxing", style_b=None, pro=False, elite=False,
          age_a=24, age_b=24, wc="Lightweight"):

    """Numerically equal fighters; only requested style/age may differ."""
    style_b = style_b or style_a
    c = country_by_name("USA")
    a = Fighter.new_player("A", "B", c, style_a)
    b = Fighter.new_player("B", "B", c, style_b)
    b.is_player = False
    a.style, b.style = style_a, style_b
    a.age, b.age = age_a, age_b
    # Equal benchmarks must be equal in division as well as ratings.  Since
    # 1.24 weight class affects real physiology, leaving character-creation
    # weight random would make the old "equal" lab measure class mismatch.
    from .cut import CLASS_LIMIT
    limit = float(CLASS_LIMIT.get(wc, 70.3))
    for who in (a, b):
        who.weight_class = wc
        who.fight_weight_class = wc
        who.natural_weight_class = wc
        who.weight = limit
        who.natural_weight = limit * 1.04
        who.walking_weight = limit * 1.04
        who.bodyfat = 12.0
        who.weight_cut_health = 90
        who.cut_drain = 0
    # Reach and stance are combat attributes in 1.26. Equal fixtures must
    # equalize them just like division and skill ratings.
    b.reach = a.reach
    b.stance = a.stance
    base = 78 if elite else 58
    for stat in C.SKILLS:
        setattr(a, stat, base)
        setattr(b, stat, base)
    a.energy = b.energy = 90
    a.health = b.health = 100
    # Character creation adds two random extras; benchmarks need the same
    # canonical move set every run or the label "equal" is still untrue.
    a.techniques = list(C.DISCIPLINE_STARTING_TECHNIQUES.get(style_a, C.BASICS))
    b.techniques = list(C.DISCIPLINE_STARTING_TECHNIQUES.get(style_b, C.BASICS))
    a.technique_levels = {name: 1 for name in a.techniques}
    b.technique_levels = {name: 1 for name in b.techniques}
    for who, target_age in ((a, age_a), (b, age_b)):
        if target_age >= 30:
            for year in range(30, target_age + 1):
                who.age = year
                who._apply_aging(None)
        who.age = target_age
    if pro:
        a.pro_debut = b.pro_debut = True
        a.pro_record = [4, 1, 0]
        b.pro_record = [4, 1, 0]
    if elite:
        for s in ("striking", "grappling", "cardio", "ko_power", "durability", "fight_iq", "speed"):
            setattr(a, s, 78)
            setattr(b, s, 78)
    return a, b


def _run(n: int, seed: int = 121, **kw) -> dict:
    random.seed(seed)
    tally = collections.Counter()
    kd = 0
    td = 0
    for _ in range(n):
        a, b = _pair(**kw)
        rules = MMARuleset(amateur=not kw.get("pro"))
        out = simulate_fight(a, b, rules, "Balanced")
        method = str(out.method or "Decision").lower()
        if "submission" in method:
            bucket = "SUB"
        elif "tko" in method:
            bucket = "TKO"
        elif "ko" in method:
            bucket = "KO"
        elif "decision" in method or method in ("draw", "points"):
            bucket = "DEC"
        else:
            bucket = "OTHER"
        tally[bucket] += 1
        tally["N"] += 1
        if out.winner == "player":
            tally["W"] += 1
        elif out.winner == "draw":
            tally["D"] += 1
        else:
            tally["L"] += 1
        kd += int(getattr(out.f_stats, "knockdowns", 0) or 0)
        td += int(getattr(out.f_stats, "takedowns_landed", 0) or 0)
    n = max(1, tally["N"])
    return {
        "n": n,
        "win": tally["W"] / n,
        "draw": tally["D"] / n,
        "ko": tally.get("KO", 0) / n,
        "tko": tally.get("TKO", 0) / n,
        "sub": tally.get("SUB", 0) / n,
        "dec": tally.get("DEC", 0) / n,
        "kd": kd / n,
        "td": td / n,
        "methods": dict(tally),
    }


def report(n: int = 400) -> str:
    blocks = [
        ("amateur equal", _run(n, pro=False)),
        ("pro equal", _run(n, pro=True, seed=122)),
        ("elite equal", _run(n, elite=True, pro=True, seed=123)),
        # Age effects are deliberately modest, so use the full sample.  The
        # previous 80-fight probe could invert the matchup through normal RNG
        # variance and falsely report the older fighter as favoured.
        ("age 36 vs 24", _run(n, age_a=36, age_b=24,
                              pro=True, seed=124)),
    ]
    lines = ["BALANCE LAB n~%s" % n]
    for name, d in blocks:
        lines.append(
            "%s  W %.0f%%  KO %.0f%%  TKO %.0f%%  SUB %.0f%%  DEC %.0f%%  KD/f %.2f"
            % (name, d["win"] * 100, d["ko"] * 100, d["tko"] * 100, d["sub"] * 100, d["dec"] * 100, d["kd"])
        )
    return "\n".join(lines)


def persona_careers(n: int = 40, weeks: int = 52) -> str:
    """Light careers through real simulate_fight + training bumps."""
    from . import constants as C
    styles = ["Boxing", "Wrestling", "BJJ", "Muay Thai"]
    w = l = 0
    pw = pl = 0
    belts = 0
    for i in range(n):
        st = styles[i % len(styles)]
        c = country_by_name("Bulgaria")
        f = Fighter.new_player("P%s" % i, "Athletic", c, st)
        f.bjj_belt = "white"
        f.style = st
        for wk in range(weeks):
            f.week += 1
            skill = C.DISCIPLINE_TRAINING_FOCUS.get(st, C.SKILLS)[0]
            setattr(f, skill, min(90, int(getattr(f, skill, 40) or 40) + 1))
            if (not f.pro_debut) and f.amateur_record[0] + f.amateur_record[1] >= 8:
                f.pro_debut = True
            if wk % 4 == 0:
                opp = Fighter.new_npc("O%s" % wk, country_by_name("Bulgaria"), st)
                if f.pro_debut:
                    opp.pro_debut = True
                out = simulate_fight(f, opp, MMARuleset(amateur=not f.pro_debut), "Balanced")
                if out.winner == "player":
                    if f.pro_debut:
                        pw += 1
                        f.pro_record[0] += 1
                    else:
                        w += 1
                        f.amateur_record[0] += 1
                elif out.winner != "draw":
                    if f.pro_debut:
                        pl += 1
                        f.pro_record[1] += 1
                    else:
                        l += 1
                        f.amateur_record[1] += 1
            if st == "BJJ" and wk == 20:
                f.bjj_belt = "blue"
                belts += 1
    am = w + l
    pr = pw + pl
    return "personas am %s-%s (%.0f%%) pro %s-%s (%.0f%%) blue %s" % (
        w, l, (100 * w / max(1, am)), pw, pl, (100 * pw / max(1, pr)), belts,
    )


def main():
    print(report(300))
    print(persona_careers(24, 52))


if __name__ == "__main__":
    main()
