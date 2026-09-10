"""Headless career batch. python3 -m mma_legend.sim_careers"""
from __future__ import annotations

import random
from collections import Counter

from mma_legend import booking, orgs, events, fights
from mma_legend.data import country_by_name
from mma_legend.engine import simulate_fight, MMARuleset, GrapplingRuleset
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


class Quiet:
    def header(self, *a, **k): pass
    def print(self, *a, **k): pass
    def gold(self, *a, **k): pass
    def good(self, *a, **k): pass
    def warn(self, *a, **k): pass
    def info(self, *a, **k): pass
    def table(self, *a, **k): pass
    def read_pause(self, *a, **k): pass
    def ask(self, *a, **k): return "B"
    def pause(self, *a, **k): pass
    def auto_pause(self, *a, **k): pass
    def milestone(self, *a, **k): pass
    def section(self, *a, **k): pass
    def menu_table(self, *a, **k): pass


def _kid(seed):
    random.seed(seed)
    c = country_by_name("USA")
    f = Fighter.new_player("Sim%d" % seed, "B", c, random.choice(["Boxing", "Wrestling", "BJJ", "Muay Thai"]))
    f.fight_details = "Quick"
    return f


def fight_once(f, pool):
    opp = fights.find_opponent_from_pool(f, pool)
    if opp is None:
        opp = fights.generate_random_opponent(f)
    if not booking.opponent_fits(f, opp) and not f.pro_debut:
        opp = fights.generate_random_opponent(f)
    out = simulate_fight(f, opp, MMARuleset(amateur=not f.pro_debut), gameplan="Balanced", console=None)
    if out.winner == "player":
        rec = f.amateur_record if not f.pro_debut else f.pro_record
        rec[0] += 1
    elif out.winner == "opponent":
        rec = f.amateur_record if not f.pro_debut else f.pro_record
        rec[1] += 1
    else:
        rec = f.amateur_record if not f.pro_debut else f.pro_record
        rec[2] += 1
    return out, opp


def run_batch(n_careers=80, weeks=90, seed0=1):
    issues = Counter()
    methods = Counter()
    am_w = am_l = am_d = 0
    pro_w = pro_l = pro_d = 0
    bad_match = 0
    org_first = Counter()
    finishes = 0
    grap_ko = 0
    belts = 0
    inbox_major = 0
    for i in range(n_careers):
        f = _kid(seed0 + i)
        pool = FighterPool()
        pool.generate_world(80, 40)
        pool.attach_player(f) if hasattr(pool, "attach_player") else None
        turned = False
        for w in range(weeks):
            f.week = w + 1
            f.energy = min(100, f.energy + 8)
            # train a little
            f.striking = min(88, f.striking + (1 if w % 3 == 0 else 0))
            f.cardio = min(88, f.cardio + (1 if w % 4 == 0 else 0))
            if f.fight_cooldown:
                f.fight_cooldown = max(0, f.fight_cooldown - 1)
                pool.simulate_week()
                continue
            if not f.pro_debut and (f.amateur_record[0] + f.amateur_record[1]) >= 6 and f.amateur_record[0] >= 4:
                f.pro_debut = True
                turned = True
                booking.set_room(f, "local")
            if f.pro_debut and w % 6 == 0:
                names = orgs.eligible_orgs(f)
                org_first[names[0] if names else "none"] += 1
                if any(x in names for x in ("PFL", "Bellator", "KSW", "UFC")) and f.pro_record[0] < 6:
                    inbox_major += 1
                    issues["major_too_soon"] += 1
            if w % 3 == 0:
                out, opp = fight_once(f, pool)
                methods[out.method] += 1
                if out.finish_label:
                    finishes += 1
                if not f.pro_debut:
                    if out.winner == "player":
                        am_w += 1
                    elif out.winner == "opponent":
                        am_l += 1
                    else:
                        am_d += 1
                    if getattr(opp, "pro_debut", False) and (opp.pro_record or [0])[0] >= 8:
                        bad_match += 1
                        issues["am_vs_vet"] += 1
                else:
                    if out.winner == "player":
                        pro_w += 1
                    elif out.winner == "opponent":
                        pro_l += 1
                    else:
                        pro_d += 1
                f.fight_cooldown = 2
            # events
            evt = events.generate_random_event(f)
            if evt and (evt.get("title") or "").lower().find("blue belt") >= 0:
                belts += 1
            pool.simulate_week()
        # grappling probe
        o = fights.generate_random_opponent(f)
        gout = simulate_fight(f, o, GrapplingRuleset(), console=None)
        if gout.method == "KO":
            grap_ko += 1
            issues["grap_ko"] += 1

    total_am = max(1, am_w + am_l + am_d)
    total_pro = max(1, pro_w + pro_l + pro_d)
    report = {
        "careers": n_careers,
        "am_record": (am_w, am_l, am_d),
        "am_win_pct": round(100 * am_w / total_am, 1),
        "pro_record": (pro_w, pro_l, pro_d),
        "pro_win_pct": round(100 * pro_w / total_pro, 1),
        "methods": dict(methods),
        "finish_share": round(100 * finishes / max(1, sum(methods.values())), 1),
        "bad_am_vs_vet": bad_match,
        "grap_ko": grap_ko,
        "blue_belt_fires": belts,
        "inbox_major_too_soon": inbox_major,
        "first_org": dict(org_first.most_common(6)),
        "issues": dict(issues),
    }
    return report


def main():
    print("Running batch...")
    r = run_batch(60, 80, 7)
    for k, v in r.items():
        print("%s: %s" % (k, v))


if __name__ == "__main__":
    main()
