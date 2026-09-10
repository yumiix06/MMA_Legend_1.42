"""
Career management: training, nutrition, supplements, lifestyle, gym, shop, training camps.
"""
import random
from typing import Optional

from .ui import GameConsole, wrap_text, status_strip
from . import cut
from . import constants as _C
from .models import Fighter
from .data import (
    TECHNIQUES_DB, COACHES_DB, SPONSORS_DB,
    TRAINING_CAMPS, NUTRITION_PLANS
)
from .constants import SUPPLEMENTS_DB


# ---------- NUTRITION ----------
def nutrition_menu(console: GameConsole, fighter: Fighter) -> None:
    """Compact nutrition/weight screen. Detailed explanation lives behind ?."""
    from .cut import CLASS_LIMIT
    plans = NUTRITION_PLANS or [
        {"name": "Clean Eating", "quality_target": 80, "weekly_mass_kg": -0.15, "weekly_energy": 1},
        {"name": "Balanced", "quality_target": 72, "weekly_mass_kg": 0.0, "weekly_energy": 0},
        {"name": "Comfort Food", "quality_target": 55, "weekly_mass_kg": 0.15, "weekly_energy": 0},
    ]
    console.header("NUTRITION & WEIGHT")
    status_strip(console, fighter)
    section = getattr(console, "section", lambda title: console.print("\n  " + str(title)))
    walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
    bf = float(getattr(fighter, "bodyfat", 12.0) or 12.0)
    home = getattr(fighter, "fight_weight_class", None) or fighter.weight_class
    console.print("  Walking %.1f kg   Body fat %.1f%%   %s (%s kg)" % (walk, bf, home, CLASS_LIMIT.get(home, "?")))
    console.print("  Plan %s   Nutrition %s/100" % (fighter.meal_plan or "none", int(getattr(fighter, "nutrition", 0) or 0)), style="dim")
    if getattr(fighter, "booked_fight", None):
        try:
            prog = cut.weight_campaign_summary(fighter)
            console.print("  Fight target %.1f kg   %.1f kg left   %s" % (prog["target"], prog["remaining"], prog.get("pace", "on track")), style="yellow")
        except Exception:
            pass

    section("MEAL PLAN")
    for i, plan in enumerate(plans):
        mass = float(plan.get("weekly_mass_kg", 0) or 0)
        arrow = "steady" if abs(mass) < 0.01 else ("%.2fkg/w" % mass)
        console.print("  %s) %-18s %s  •  Q%s" % (i + 1, plan["name"], arrow, int(plan.get("quality_target", 70) or 70)))
    console.print("  C) Change weight class")
    console.print("  S) Fight weight strategy")
    console.print("  ?) How weight works")
    if hasattr(console, "nav_footer"):
        console.nav_footer(home=True)
    else:
        console.print("  X Back   0 Home")
    choice = (console.ask("\n  Nutrition > ") or "X").strip()
    up = choice.upper()
    if up in ("X", "0"):
        return
    if up == "?":
        console.header("WEIGHT HELP", "Simple version")
        console.print("  • Walking weight is your real current body mass.")
        console.print("  • Meal plans move body mass gradually each week.")
        console.print("  • Fight target is the walking weight needed before a realistic final water cut.")
        console.print("  • If you are already within the class limit, there is no dehydration cut.")
        console.print("  • Scale weight never exceeds your actual walking weight.")
        getattr(console, "continue_prompt", console.pause)("Press Enter to return")
        return
    if up == "S":
        cut.pick_weight_strategy(console, fighter)
        return
    if up == "C":
        from .cut import pick_home_class
        pick_home_class(console, fighter)
        return
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(plans):
            raise ValueError
        plan = plans[idx]
    except ValueError:
        console.warn("Invalid.")
        return
    fighter.meal_plan = plan["name"]
    fighter._update_mood()
    console.good("Meal plan set: %s." % plan["name"])
    console.info("Its effects apply on the next weekly tick.")


# ---------- SUPPLEMENTS & DOPING ----------
def supplement_sponsor(fighter) -> str | None:
    """Return the first signed brand that explicitly supplies supplements."""
    capabilities = {
        str(s.get("name") or ""): set(s.get("benefits") or [])
        for s in SPONSORS_DB
    }
    for name in list(getattr(fighter, "sponsors", None) or []):
        if "legal_supplements" in capabilities.get(str(name), set()):
            return str(name)
    return None

def supplement_menu(console: GameConsole, fighter: Fighter) -> None:
    """v1.40 legal performance products + abstract anti-doping hub."""
    from . import performance
    performance.ensure(fighter)
    while True:
        console.header("PERFORMANCE", "Supplements & anti-doping")
        status_strip(console, fighter)
        for line in performance.status_lines(fighter):
            console.print("  " + line)
        console.print("")
        console.print("  A) Legal supplements")
        console.print("  B) Prohibited performance programs")
        console.print("  C) Testing / history")
        console.print("  X) Back")
        ch = (console.ask("Performance > ") or "X").strip().upper()
        if ch in ("X", "0", ""):
            return
        if ch == "A":
            _show_supplement_list(console, fighter, "legal")
            continue
        if ch == "B":
            _show_supplement_list(console, fighter, "prohibited")
            continue
        if ch == "C":
            console.header("ANTI-DOPING")
            for line in performance.status_lines(fighter):
                console.print("  " + line)
            hist = list(getattr(fighter, "doping_history", None) or [])[-8:]
            if hist:
                console.print("")
                for row in hist:
                    console.print("  W%s · %s" % (row.get("week"), row.get("detail")))
            else:
                console.print("  No test history.")
            console.print("  X) Back")
            console.ask("Anti-doping > ")
            continue


def _show_supplement_list(console: GameConsole, fighter: Fighter, category: str) -> None:
    from . import performance
    performance.ensure(fighter)
    if category == "legal":
        items = list(performance.LEGAL_PRODUCTS.items())
        console.header("LEGAL SUPPLEMENTS", "Temporary support — no permanent stats")
        sponsor = supplement_sponsor(fighter)
        for i, (name, spec) in enumerate(items, 1):
            price = "FREE (%s)" % sponsor if sponsor else "$%s" % spec["cost"]
            active = " · %sw left" % fighter.supplement_stack.get(name) if name in fighter.supplement_stack else ""
            console.print("  %s) %-27s %s%s" % (i, name, price, active))
            console.print("     " + spec["description"], style="dim")
        console.print("  X) Back")
        pick = (console.ask("Supplement > ") or "X").strip().upper()
        if pick == "X":
            return
        try:
            name, _spec = items[int(pick)-1]
        except (ValueError, IndexError):
            console.warn("Invalid.")
            return
        msg = performance.buy_legal(fighter, name, covered=bool(sponsor))
        (console.good if not msg.startswith(("Not enough", "Unknown")) else console.warn)(msg)
        return

    items = list(performance.PROHIBITED_PROGRAMS.items())
    console.header("PROHIBITED PROGRAMS", "Temporary effects · health/testing consequences")
    console.warn("These are abstract gameplay programs. The game does not model clearance or evasion timing.")
    active, _ = performance.active_program(fighter)
    for i, (name, spec) in enumerate(items, 1):
        console.print("  %s) %-27s $%s" % (i, name, spec["cost"]))
        console.print("     " + spec["description"], style="dim")
    if active:
        console.print("  S) Stop current program (%s)" % active)
    console.print("  X) Back")
    pick = (console.ask("Program > ") or "X").strip().upper()
    if pick == "X":
        return
    if pick == "S":
        console.warn(performance.stop_program(fighter))
        return
    try:
        name, _spec = items[int(pick)-1]
    except (ValueError, IndexError):
        console.warn("Invalid.")
        return
    confirm = (console.ask("Start prohibited program? A yes / X cancel > ") or "X").strip().upper()
    if confirm != "A":
        return
    msg = performance.start_program(fighter, name)
    (console.good if " started." in msg else console.warn)(msg)


def _show_active_supplements(console: GameConsole, fighter: Fighter) -> None:
    from . import performance
    console.header("ACTIVE PERFORMANCE SUPPORT")
    for line in performance.status_lines(fighter):
        console.print("  " + line)


# ---------- TRAINING (REGULAR) ----------
def do_training(console: GameConsole, fighter: Fighter) -> bool:
    """Run one training week. Returns True only when a valid session happens."""
    from .ui import status_strip
    console.header("TRAINING", "Fast routine: R repeats your previous session")
    status_strip(console, fighter)
    if fighter.fight_cooldown > 0:
        console.warn("Fight recovery — light work is safest.")

    intensity_specs = {
        "A": ("Light", 10, 0.7, 0.02),
        "B": ("Normal", 20, 1.0, 0.05),
        "C": ("Heavy", 30, 1.3, 0.12),
    }
    focus_specs = {
        "A": "Striking", "B": "Kicks", "C": "Grappling", "D": "Submissions",
        "E": "Takedown Defense", "F": "Ground Control", "G": "Cardio",
        "H": "Strength", "I": "Speed", "J": "Fight IQ", "K": "Striking Defense",
        "L": "Submission Defense", "M": "Distance Management", "N": "Balanced",
    }
    last_focus = str(getattr(fighter, "last_training_focus", "N") or "N").upper()
    last_intensity = str(getattr(fighter, "last_training_intensity", "B") or "B").upper()
    if last_focus not in focus_specs: last_focus = "N"
    if last_intensity not in intensity_specs: last_intensity = "B"
    lname, lcost, _lm, lrisk = intensity_specs[last_intensity]
    console.section("FOCUS")
    focus_labels = [
        ("A", "Striking"),
        ("B", "Kicks"),
        ("C", "Grappling"),
        ("D", "Submissions"),
        ("E", "Takedown Defense"),
        ("F", "Ground Control"),
        ("G", "Cardio"),
        ("H", "Strength"),
        ("I", "Speed"),
        ("J", "Fight IQ"),
        ("K", "Striking Defense"),
        ("L", "Submission Defense"),
        ("M", "Distance Management"),
        ("N", "Balanced"),
    ]
    for key, label in focus_labels:
        if key == "N":
            vals = [int(getattr(fighter, st, 0) or 0) for st in _C.SKILLS]
            level = int(round(sum(vals) / max(1, len(vals))))
        else:
            stat = {
                "A":"striking", "B":"kicks", "C":"grappling", "D":"submissions",
                "E":"takedown_def", "F":"ground_control", "G":"cardio", "H":"strength",
                "I":"speed", "J":"fight_iq", "K":"striking_def", "L":"submission_def",
                "M":"distance_management",
            }.get(key)
            level = int(getattr(fighter, stat, 0) or 0) if stat else 0
        console.print("  %s) %-23s %3s" % (key, label, level))
    console.print("")
    console.print("  R) Repeat last session")
    console.print("     %s / %s / %s EN / %s%% risk" % (
        focus_specs[last_focus], lname, lcost, int(lrisk * 100)))
    console.print("  X) Back")
    focus = console.ask("\n  Focus > ").strip().upper()
    if focus in ("X", "0", ""):
        return False
    if focus == "R":
        focus, intensity = last_focus, last_intensity
    elif focus in focus_specs:
        console.section("INTENSITY")
        console.print("  A) Light    10 EN    2% injury risk")
        console.print("  B) Normal   20 EN    5% injury risk")
        console.print("  C) Heavy    30 EN   12% injury risk")
        console.print("  X) Back")
        intensity = console.ask("\n  Intensity > ").strip().upper()
        if intensity in ("X", "0", ""):
            return False
        if intensity not in intensity_specs:
            console.warn("Invalid intensity. Training cancelled.")
            return False
    else:
        console.warn("Invalid focus. Training cancelled — no time or energy spent.")
        return False

    iname, energy_cost, gain_mult, injury_risk = intensity_specs[intensity]
    if intensity == "C" and fighter.energy < 40:
        console.warn("Low energy for Heavy training.")
        heavy_choice = console.ask("A) Continue heavy  B) Switch to light  X) Cancel > ").strip().upper()
        if heavy_choice == "B":
            intensity = "A"
            iname, energy_cost, gain_mult, injury_risk = intensity_specs[intensity]
        elif heavy_choice != "A":
            return False
    if fighter.energy < energy_cost:
        console.warn("Too tired. Need %s energy; you have %s." % (energy_cost, fighter.energy))
        return False

    try:
        from .performance import injury_risk_multiplier
        injury_risk *= injury_risk_multiplier(fighter)
    except Exception:
        pass
    console.info("Session: %s · %s · (1 WEEK · -%s EN · injury %s%%)" % (
        focus_specs[focus], iname, energy_cost, int(injury_risk * 100)))
    fighter.energy -= energy_cost
    fighter.last_training_focus = focus
    fighter.last_training_intensity = intensity

    boost = 1.0
    if fighter.coach_boost and fighter.coach_boost_weeks > 0:
        boost = 1.5
        console.info("Coach boost active (+50% gains).")

    gains = {
        'A': ('striking', 2, ('speed', 1)), 'B': ('kicks', 2, ('speed', 1)),
        'C': ('grappling', 2, ('strength', 1)), 'D': ('submissions', 2, ('fight_iq', 1)),
        'E': ('takedown_def', 2, ('grappling', 1)), 'F': ('ground_control', 2, ('grappling', 1)),
        'G': ('cardio', 3, ('durability', 1)), 'H': ('strength', 2, ('ko_power', 1)),
        'I': ('speed', 2, ('cardio', 1)), 'J': ('fight_iq', 3, ('adaptability', 1)),
        'K': ('striking_def', 2, ('distance_management', 1)),
        'L': ('submission_def', 2, ('grappling', 1)),
        'M': ('distance_management', 2, ('fight_iq', 1)),
    }
    changed = []
    from .physiology import gain_stat, stat_cap
    if focus == 'N':
        disc_skills = {
            'Boxing': ['striking', 'striking_def', 'distance_management', 'speed', 'fight_iq', 'ko_power'],
            'Kickboxing': ['striking', 'kicks', 'striking_def', 'distance_management', 'speed', 'cardio'],
            'Taekwondo': ['kicks', 'speed', 'distance_management', 'striking_def', 'cardio', 'fight_iq'],
            'Muay Thai': ['striking', 'kicks', 'striking_def', 'grappling', 'durability'],
            'Wrestling': ['grappling', 'takedown_def', 'submission_def', 'strength', 'cardio'],
            'BJJ': ['submissions', 'submission_def', 'ground_control', 'fight_iq', 'adaptability'],
            'Sambo': ['grappling', 'submissions', 'submission_def', 'strength', 'ground_control', 'striking', 'kicks'],
            'Combat Sambo': ['grappling', 'submissions', 'submission_def', 'strength', 'ground_control', 'striking', 'kicks'],
            'Judo': ['grappling', 'takedown_def', 'ground_control', 'strength', 'fight_iq'],
            'MMA': list(_C.SKILLS),
        }
        skills_to_train = list(_C.SKILLS) if fighter.amateur_discipline in ['Sambo', 'Combat Sambo', 'MMA'] else disc_skills.get(fighter.amateur_discipline, ['striking', 'grappling', 'cardio', 'fight_iq'])
        for stat in skills_to_train:
            current = getattr(fighter, stat)
            raw = 1 if current < 80 else (0.5 if current < 90 else 0.25)
            perf_mult = 1.0
            try:
                from .performance import training_multiplier
                perf_mult *= training_multiplier(fighter, stat)
                from .education import degree_benefit
                perf_mult *= float(degree_benefit(fighter, "training_mult", 1.0))
            except Exception:
                pass
            gain = int(round(raw * gain_mult * boost * perf_mult))
            if gain > 0:
                actual = gain_stat(fighter, stat, gain)
                if actual:
                    changed.append("%s +%s" % (_C.SKILL_LABELS.get(stat, stat), actual))
        injury_risk *= 0.8
    else:
        primary, gain, secondary = gains[focus]
        current = getattr(fighter, primary)
        perf_mult = 1.0
        try:
            from .performance import training_multiplier
            perf_mult *= training_multiplier(fighter, primary)
            from .education import degree_benefit
            perf_mult *= float(degree_benefit(fighter, "training_mult", 1.0))
        except Exception:
            pass
        actual_gain = int(round(gain * (0.3 if current >= 90 else 0.6 if current >= 80 else 1.0) * gain_mult * boost * perf_mult))
        actual_gain = max(1, actual_gain)
        got = gain_stat(fighter, primary, actual_gain)
        if got:
            changed.append("%s +%s" % (_C.SKILL_LABELS.get(primary, primary), got))
        elif stat_cap(fighter, primary) < 100:
            changed.append("%s at class ceiling" % _C.SKILL_LABELS.get(primary, primary))
        if secondary:
            sec_name, sec_gain = secondary
            sec_cur = getattr(fighter, sec_name)
            sec_mult = 1.0
            try:
                from .performance import training_multiplier
                sec_mult *= training_multiplier(fighter, sec_name)
                from .education import degree_benefit
                sec_mult *= float(degree_benefit(fighter, "training_mult", 1.0))
            except Exception:
                pass
            sec_actual = int(round(sec_gain * (0.4 if sec_cur >= 80 else 1.0) * gain_mult * boost * sec_mult))
            if sec_actual > 0:
                got2 = gain_stat(fighter, sec_name, sec_actual)
                if got2:
                    changed.append("%s +%s" % (_C.SKILL_LABELS.get(sec_name, sec_name), got2))

    if changed:
        console.good("Progress: " + " · ".join(changed[:6]))
    if random.random() < injury_risk:
        injury = random.randint(5, 20)
        fighter.health = max(0, fighter.health - injury)
        console.warn("Injury! Health -%s%%" % injury)
    _spar_discover(console, fighter, focus)
    fighter.relationships["coach"] = min(100, fighter.relationships.get("coach", 50) + 2)
    return True


def _spar_discover(console, fighter, focus: str) -> None:
    """Learn or sharpen a move while training. No extra menu."""
    from . import data
    pool = _coach_pool_names(fighter)
    if not pool:
        return
    known = set(fighter.techniques or [])
    if random.random() < 0.28:
        unknown = [n for n in pool if n not in known]
        if not fighter.pro_debut:
            unknown = [n for n in unknown if "heel" not in n.lower()]
        if unknown:
            pick = random.choice(unknown)
            fighter.learn_technique(pick)
            console.gold("Sparring: you pick up %s." % pick)
            return
    if known and random.random() < 0.22:
        pick = random.choice(list(known))
        if fighter.level_up_technique(pick):
            console.info("Sharper %s." % pick)


# ---------- TRAINING CAMP ----------
CAMP_FOCUSES = {
    "A": ("Striking", {"striking": 4, "speed": 2, "ko_power": 2}),
    "B": ("Wrestling", {"grappling": 4, "ground_control": 3, "strength": 2}),
    "C": ("Cardio", {"cardio": 5, "durability": 2}),
    "D": ("Complete", {"striking": 2, "grappling": 2, "cardio": 2, "fight_iq": 2}),
    "E": ("Anti-Wrestling", {"takedown_def": 4, "grappling": 2, "fight_iq": 2}),
    "F": ("Submission Defense", {"submission_def": 4, "grappling": 2, "fight_iq": 2}),
    "G": ("Pressure & Entries", {"distance_management": 3, "grappling": 2, "cardio": 1}),
}


def _camp_opponent(fighter):
    booked=getattr(fighter,"booked_fight",None) or {}
    opp=booked.get("opponent") if isinstance(booked,dict) else None
    if opp is not None: return opp
    snap=booked.get("opponent_snapshot") if isinstance(booked,dict) else None
    if isinstance(snap,dict):
        try: return Fighter.from_dict(snap)
        except Exception: return None
    return None

def camp_plan_advice(fighter, opponent) -> tuple[str,str]:
    """Coach recommendation derived from the actual booked opponent."""
    og=int(getattr(opponent,"grappling",50) or 50)
    osub=int(getattr(opponent,"submissions",50) or 50)
    octrl=int(getattr(opponent,"ground_control",50) or 50)
    strike=int(getattr(opponent,"striking",50) or 50)+int(getattr(opponent,"kicks",50) or 50)*.45
    grap=og+octrl*.35+osub*.25
    cardio=int(getattr(opponent,"cardio",50) or 50)
    reach=int(getattr(opponent,"reach",0) or 0)-int(getattr(fighter,"reach",0) or 0)
    my_tdd=int(getattr(fighter,"takedown_def",50) or 50)
    my_subdef=int(getattr(fighter,"submission_def",50) or 50)
    my_grap=int(getattr(fighter,"grappling",50) or 50)
    opp_tdd=int(getattr(opponent,"takedown_def",50) or 50)
    if osub >= 72 and osub >= my_subdef + 8:
        return "F","His submission threat is the matchup danger; rehearse escapes, hand-fighting and safe top position."
    if og >= my_tdd + 8 or grap >= strike + 12:
        return "E","He is likely to force wrestling exchanges; prioritize entries, sprawls and wall-work defense."
    if my_grap >= opp_tdd + 10:
        return "G","His takedown defense is a controllable weakness; prepare pressure, entries and chain finishes."
    if strike >= grap + 14 or reach >= 7:
        return "A","His striking/range threat is the main problem; sharpen entries, defense and counters."
    if cardio >= 75 and int(getattr(fighter,"cardio",50) or 50) < 65:
        return "C","Expect a pace fight; conditioning is the largest controllable gap."
    return "D","No single matchup problem dominates; a complete MMA camp protects against multiple threats."

def _start_camp(console, fighter, weeks, key, label, bonus, opponent=None, recommended=False):
    fighter.camp_active=True; fighter.camp_focus=label; fighter.camp_weeks_remaining=weeks; fighter.camp_for_bout=weeks; fighter.camp_bonus=1; fighter.camp_bonus_remaining=dict(bonus)
    if opponent is not None:
        fighter.camp_opponent_style=getattr(opponent,"style",None); fighter.opponent_read=max(int(getattr(fighter,"opponent_read",0) or 0),4+(2 if recommended else 0))
    try:
        from . import combat_intelligence as _ci
        fighter.camp_preparation = _ci.preparation_blueprint(fighter, opponent, label)
    except Exception:
        fighter.camp_preparation = {}
    fighter.energy=max(0,int(getattr(fighter,"energy",100) or 100)-5)
    console.good("Camp: %s for %s weeks.%s"%(label,weeks," · coach-recommended" if recommended else ""))

def pick_and_start_camp(console: GameConsole, fighter: Fighter, weeks: int) -> None:
    weeks=max(2,min(8,int(weeks or 4))); opponent=_camp_opponent(fighter); rec_key=None
    console.header("CAMP","%s weeks to the date"%weeks)
    if opponent:
        console.print("Booked opponent: %s · %s"%(opponent.name,getattr(opponent,"style","MMA")))
        try:
            from . import v08
            for line in v08.scout_lines(fighter,opponent): console.print(line)
        except Exception: pass
        rec_key,reason=camp_plan_advice(fighter,opponent); console.info("Coach recommends %s — %s"%(CAMP_FOCUSES.get(rec_key,CAMP_FOCUSES["D"])[0],reason))
    console.print("  A) Striking")
    console.print("  B) Wrestling")
    console.print("  C) Cardio")
    console.print("  D) Complete")
    console.print("  E) Anti-Wrestling")
    console.print("  F) Submission Defense")
    console.print("  G) Pressure & Entries")
    ch=console.ask("Focus > ").strip().upper(); ch=ch if ch in CAMP_FOCUSES else "D"; name,bonus=CAMP_FOCUSES[ch]
    _start_camp(console,fighter,weeks,ch,name,bonus,opponent,ch==rec_key)

def training_camp_menu(console: GameConsole, fighter: Fighter) -> None:
    console.header("TRAINING CAMP","Prepare for a fight"); camps=TRAINING_CAMPS.get("focuses",[])
    if not camps: console.warn("No training camps available."); console.pause(.6); return
    if fighter.camp_active:
        console.warn("Active camp: %s — %s week(s) left."%(fighter.camp_focus,fighter.camp_weeks_remaining)); console.print("Fight-night sharpness: +%s"%fighter.camp_bonus); console.print("Opponent read: %s/20"%min(20,int(getattr(fighter,"opponent_read",0) or 0)))
        try:
            from . import combat_intelligence as _ci
            _prep = _ci.preparation_summary(fighter)
            if _prep: console.print("Preparation: " + _prep)
        except Exception:
            pass
        console.pause(.8); return
    opponent=_camp_opponent(fighter)
    if opponent:
        console.print("Booked opponent: %s · %s · %s"%(opponent.name,getattr(opponent,"stance","?"),getattr(opponent,"style","MMA")))
        try:
            from . import v08
            for line in v08.scout_lines(fighter,opponent): console.print(line)
        except Exception: pass
        rec_key,reason=camp_plan_advice(fighter,opponent); console.info("Coach plan: %s"%reason)
    else: rec_key=None
    console.print("Camps last 4 weeks. Bonuses arrive week by week.")
    for i,camp in enumerate(camps): console.print("  %s) %s — %s"%(i+1,camp["name"],", ".join("%s+%s"%(k,v) for k,v in camp.get("bonus",{}).items())))
    if opponent: console.print("  S) Study booked opponent (film + Complete MMA camp)")
    console.print("  X) Back"); choice=console.ask("\n  Choice > ").strip().upper()
    if choice=="X": return
    if choice=="S" and opponent:
        camp=next((c for c in camps if "Complete" in c["name"]),camps[-1]); fighter.opponent_read=min(20,int(getattr(fighter,"opponent_read",0) or 0)+5); console.info("Film study: %s. Opponent read improved."%opponent.name)
    else:
        try: camp=camps[int(choice)-1]
        except (ValueError,IndexError): console.warn("Invalid."); console.pause(.5); return
    bonus=dict(camp.get("bonus",{}))
    if fighter.national_team:
        for k in list(bonus)[:2]: bonus[k]=bonus.get(k,0)+1
    key=rec_key or "D"; _start_camp(console,fighter,4,key,camp["name"],bonus,opponent,bool(opponent and camp_plan_advice(fighter,opponent)[0]==key)); console.pause(.8)


def coach_talk_menu(console: GameConsole, fighter: Fighter) -> bool:
    """Team hub. Returns True only when an actual training activity consumes time."""
    console.header("TEAM & GYM")
    status_strip(console, fighter)
    if getattr(fighter, "intl_camp", None):
        try:
            from . import camps
            spec = camps.active(fighter)
            label = spec.get("name") or "international camp"
        except Exception:
            label = "international camp"
        console.warn("You are training in %s." % label)
        console.info("Home coaches and specialist gyms are unavailable until you return.")
        return False

    fighter.sync_techniques()
    section = getattr(console, "section", lambda title: console.print("\n  " + str(title)))
    coach_rel = fighter.relationships.get("coach", 50)
    belt_bits = []
    if getattr(fighter, "bjj_belt", None):
        belt_bits.append("BJJ %s" % str(fighter.bjj_belt).title())
    if getattr(fighter, "judo_belt", None):
        belt_bits.append("Judo %s" % str(fighter.judo_belt).title())
    console.print("  Coach %s/100%s" % (coach_rel, ("  •  " + "  •  ".join(belt_bits)) if belt_bits else ""), style="dim")
    section("TRAINING")
    console.print("  A) Learn a new technique")
    console.print("  B) Drill a known technique")
    console.print("  R) Random technique practice")
    console.print("  G) Gym rooms & teammates")
    section("INFO")
    console.print("  C) Coach advice")
    console.print("  E) Belt / gym progress")
    if hasattr(console, "nav_footer"):
        console.nav_footer(home=True)
    else:
        console.print("  X Back   0 Home")
    choice = console.ask("\n  Team > ").strip().upper()
    if choice in ("X", "0", ""):
        return False

    before_energy = int(getattr(fighter, "energy", 0) or 0)
    if choice == "A":
        _coach_teach_technique(console, fighter)
    elif choice == "B":
        _coach_drill_technique(console, fighter)
    elif choice == "C":
        _coach_advice(console, fighter)
    elif choice == "R":
        _coach_random_practice(console, fighter)
    elif choice == "G":
        gym_menu(console, fighter)
    elif choice == "E":
        from . import amateur_sports, gym_progression
        console.section("Progress")
        if getattr(fighter, "specialty_gym", None):
            for line in gym_progression.status_lines(fighter):
                console.print("  " + line)
        else:
            console.print("  No specialist membership.")
        if getattr(fighter, "bjj_belt", None):
            console.print("  BJJ: " + amateur_sports.belt_progress_line(fighter, "bjj"))
        if getattr(fighter, "judo_belt", None):
            console.print("  Judo: " + amateur_sports.belt_progress_line(fighter, "judo"))
        console.print("  Promotions happen automatically when requirements are met.", style="dim")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(.2))("Press Enter to return")
    else:
        console.warn("Invalid.")
        return False
    # Training actions in this hub all consume energy. Metadata syncs, advice,
    # membership changes and belt evaluation never advance the calendar.
    return int(getattr(fighter, "energy", 0) or 0) < before_energy

def _coach_voice(fighter) -> str:
    p = getattr(fighter, "coach_personality", "") or "Tactical"
    lines = {
        "Strict": "Again. Your stance is terrible.",
        "Technical": "Hands first. Then the rest.",
        "Aggressive": "Walk him down. Don't wait.",
        "Patient": "Don't force it. The opening will come.",
        "Old School": "You don't need ten fancy moves. Master the basics.",
        "Encouraging": "That's it. Much cleaner. Do it again.",
        "Demanding": "If you're tired now, you'll fold in round two.",
        "Tactical": "He reacts to the jab. We're going to use that.",
    }
    return lines.get(p, lines["Tactical"])


def _coach_pool_names(fighter) -> list:
    """~85% of that sport's techniques plus MMA basics. Level is separate."""
    disc = fighter.amateur_discipline or "MMA"
    related = {
        "Boxing": ["Boxing", "MMA"],
        "Wrestling": ["Wrestling", "MMA"],
        "Muay Thai": ["Muay Thai", "Kickboxing", "MMA"],
        "Sambo": ["Sambo", "Wrestling", "MMA"],
        "Combat Sambo": ["Combat Sambo", "Wrestling", "MMA"],
        "Judo": ["Judo", "Wrestling", "BJJ", "MMA"],
        "BJJ": ["BJJ", "MMA"],
        "Kickboxing": ["Kickboxing", "Muay Thai", "MMA"],
        "Taekwondo": ["Taekwondo", "Kickboxing", "MMA"],
    }.get(disc, ["MMA", "Boxing", "Wrestling"])
    names = []
    for t in TECHNIQUES_DB:
        if t.get("discipline") in related:
            names.append(t["name"])
    # keep ~85% so a few remain as "he doesn't teach that"
    random.shuffle(names)
    keep = max(8, int(len(names) * 0.85))
    names = names[:keep]
    for n in getattr(fighter, "specialty_pool", None) or []:
        if n not in names:
            names.append(n)
    return names


def ensure_coach(fighter) -> None:
    from . import data
    if not getattr(fighter, "coach_personality", ""):
        opts = data.COACH_PROFILES.get("personalities") or ["Tactical"]
        fighter.coach_personality = random.choice(opts)
    if not getattr(fighter, "coach_offer_tech", ""):
        _roll_coach_offer(fighter)


def _roll_coach_offer(fighter) -> None:
    known = set(fighter.technique_levels.keys())
    names = _coach_pool_names(fighter)
    cand = []
    for name in names:
        if name in known:
            continue
        row = next((t for t in TECHNIQUES_DB if t["name"] == name), None)
        if row and not fighter.pro_debut and (row.get("amateur_ok") is False or row.get("pro_only")):
            continue
        if row and row.get("prerequisite") and row.get("prerequisite") not in known:
            continue
        cand.append(name)
    fighter.coach_offer_tech = random.choice(cand) if cand else ""
    fighter.coach_offer_week = fighter.week


def tick_coach_offer(fighter) -> None:
    ensure_coach(fighter)
    last = int(getattr(fighter, "coach_offer_week", 0) or 0)
    gap = random.randint(3, 6)
    if fighter.week - last >= gap or not getattr(fighter, "coach_offer_tech", ""):
        _roll_coach_offer(fighter)


def _coach_teach_technique(console: GameConsole, fighter: Fighter) -> None:
    ensure_coach(fighter)
    tick_coach_offer(fighter)
    last = int(getattr(fighter, "coach_tech_week", -99) or -99)
    wait = random.randint(3, 6)
    if fighter.week - last < wait and last > 0:
        console.warn("He already gave you a private. Come back in %s weeks." % (wait - (fighter.week - last)))
        console.print(_coach_voice(fighter))
        return
    if fighter.relationships.get("coach", 50) < 40:
        console.warn("He will not waste a private on you yet.")
        return
    console.print("%s coach. %s." % (fighter.coach_personality or "Tactical", _coach_voice(fighter)))
    offer = getattr(fighter, "coach_offer_tech", "") or ""
    known = set(fighter.technique_levels.keys())
    pool_names = _coach_pool_names(fighter)
    candidates = []
    for t in TECHNIQUES_DB:
        if t["name"] not in pool_names:
            continue
        if t["name"] in known:
            continue
        prereq = t.get("prerequisite")
        if prereq and prereq not in known:
            continue
        if not fighter.pro_debut and (t.get("amateur_ok") is False or t.get("pro_only")):
            continue
        candidates.append(t)
    if offer:
        row = next((t for t in TECHNIQUES_DB if t["name"] == offer), None)
        if row and row not in candidates and offer not in known:
            candidates.insert(0, row)
        console.info("This week's lesson: %s" % offer)
    if not candidates:
        console.warn("Nothing new in his pool. Drill what you have.")
        console.pause(0.6)
        return

    candidates = candidates[:8]
    cost_base = 80 if fighter.national_team else 120
    letters = "ABCDEFGH"
    console.print("Available to learn (his pool only):")
    for i, t in enumerate(candidates):
        cost = cost_base * int(t.get("cost", 1))
        mark = " <<" if t["name"] == offer else ""
        console.print(f"  {letters[i]}) {t['name']} [{t.get('discipline','?')}] — ${cost}{mark}")
    console.print("  X) Back")
    raw = console.ask("\n  Learn > ").strip().upper()
    if raw == "X":
        return
    if raw not in letters[:len(candidates)]:
        console.warn("Use a letter.")
        return
    tech = candidates[letters.index(raw)]
    cost = cost_base * int(tech.get("cost", 1))
    if fighter.money < cost:
        console.warn(f"Need ${cost}. You have ${fighter.money}.")
        console.pause(0.5)
        return
    if fighter.energy < 20:
        console.warn("Too tired to learn (need 20 energy).")
        console.pause(0.5)
        return
    fighter.money -= cost
    fighter.energy = max(0, fighter.energy - 20)
    fighter.learn_technique(tech["name"])
    # Apply small immediate bonus from technique definition
    for k, v in (tech.get("bonus") or {}).items():
        if hasattr(fighter, k):
            amt = max(1, int(v) // 2)
            try:
                from .physiology import gain_stat
                gain_stat(fighter, k, amt)
            except Exception:
                setattr(fighter, k, min(100, getattr(fighter, k) + amt))
    fighter.relationships["coach"] = min(100, fighter.relationships.get("coach", 50) + 3)
    fighter.coach_tech_week = fighter.week
    _roll_coach_offer(fighter)
    console.gold(f"✨ Learned {tech['name']}!")
    console.pause(0.7)


def _coach_random_practice(console: GameConsole, fighter: Fighter) -> None:
    import random
    known = list(getattr(fighter, "techniques", None) or [])
    if not known:
        console.warn("Learn something first.")
        return
    name = random.choice(known)
    fighter.energy = max(0, fighter.energy - 8)
    lv = dict(getattr(fighter, "technique_levels", None) or {})
    cur = int(lv.get(name, 1) or 1)
    upgraded = False
    if cur < 5 and random.random() < 0.45:
        lv[name] = cur + 1
        upgraded = True
    else:
        lv[name] = cur
    fighter.technique_levels = lv
    try:
        from .systems17 import log_session
        log_session(fighter, "spar", name)
    except Exception:
        pass
    try:
        # Hard sessions break people occasionally.
        from . import damage as _dmg
        _dmg.training_injury(fighter, intensity=1.4, console=console)
    except Exception:
        pass
    if upgraded:
        console.gold("Coach: again. %s sharpened to level %s." % (name, lv[name]))
    else:
        console.good("Coach: again. You drilled %s." % name)
    console.pause(0.5)


def _coach_drill_technique(console: GameConsole, fighter: Fighter) -> None:
    if not fighter.technique_levels:
        console.warn("You don't know any techniques yet.")
        console.pause(0.5)
        return
    fighter.sync_techniques()
    items = sorted(fighter.technique_levels.items(), key=lambda x: (-x[1], x[0]))
    if not items:
        console.warn("Nothing to drill.")
        return
    page = 0
    letters = "ABCDEFGH"
    while True:
        chunk = items[page * 8:(page + 1) * 8]
        console.print("Mastery (page %s)" % (page + 1))
        for i, (name, lvl) in enumerate(chunk):
            stars = "★" * lvl + "☆" * (5 - lvl)
            console.print(f"  {letters[i]}) {name} {stars}")
        if (page + 1) * 8 < len(items):
            console.print("  N) Next page")
        if page:
            console.print("  P) Prev page")
        raw = console.ask("\n  Drill > ").strip().upper()
        if raw == "N" and (page + 1) * 8 < len(items):
            page += 1
            continue
        if raw == "P" and page:
            page -= 1
            continue
        if raw not in letters[:len(chunk)]:
            console.warn("Use a letter.")
            return
        name, lvl = chunk[letters.index(raw)]
        break
    if lvl >= 5:
        console.info(f"{name} is already maxed.")
        console.pause(0.5)
        return
    cost = 50 if fighter.national_team else 80
    if fighter.money < cost or fighter.energy < 16:
        console.warn(f"Need ${cost} and 16 energy.")
        console.pause(0.5)
        return
    fighter.money -= cost
    fighter.energy -= 16
    chance = 0.35 + fighter.relationships.get("coach", 50) / 250 + (0.1 if fighter.national_team else 0)
    if random.random() < chance and fighter.level_up_technique(name):
        console.gold(f"💡 {name} → Level {fighter.technique_levels[name]}!")
    else:
        console.info(f"Good reps on {name}, but no level-up this session.")
        fighter.technique_usage_count[name] = fighter.technique_usage_count.get(name, 0) + 3
    console.pause(0.6)


def _coach_advice(console: GameConsole, fighter: Fighter) -> None:
    """Browse-only advice. No free stat/relationship farming from a browse-only screen."""
    tips = [
        "Keep your hands high when you kick.",
        "Don't force the finish — accumulate damage.",
        "Weight cut quality decides fight-night energy.",
        "Film study beats random sparring sometimes.",
        "If cardio fades in round 2, slow the pace.",
    ]
    if fighter.national_team:
        tips.append("National-team camps will push you harder — recover properly.")
    if fighter.pro_debut:
        tips.append("Pro judges reward effective damage and control, not empty activity.")
    else:
        tips.append("Amateur path: build experience and championship results before rushing pro.")
    console.info(random.choice(tips))
    console.pause(0.3)


# ---------- GYM ----------
def specialty_gym_menu(console: GameConsole, fighter: Fighter) -> None:
    from . import data
    from . import gym_progression
    console.header("SPECIALTY GYM", "BJJ, Judo, kickboxing or Taekwondo")
    if getattr(fighter, "intl_camp", None):
        console.warn("You are abroad. Your home specialist gym is unavailable until the international camp ends.")
        return

    gym_progression.ensure(fighter)
    if getattr(fighter, "specialty_gym", None):
        for line in gym_progression.status_lines(fighter):
            console.print("  " + line)
        console.print("")
        console.print("  A) Extra specialist session")
        console.print("  B) View gym syllabus")
        console.print("  L) Leave this gym")
        console.print("  X) Back")
        tr = console.ask("Choice > ").strip().upper()
        if tr == "A":
            gym_progression.manual_session(fighter, console)
            return
        if tr == "B":
            console.section("Syllabus")
            rows = gym_progression.syllabus_lines(fighter, limit=22)
            if not rows:
                console.print("  No specialist syllabus loaded.")
            else:
                for row in rows:
                    console.print("  " + row)
            getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(.2))("Press Enter to return")
            return
        if tr != "L":
            return
        if console.ask("Leave this gym? A yes / B no > ").strip().upper() == "A":
            fighter.specialty_gym = None
            fighter.specialty_gym_type = None
            fighter.specialty_coach = None
            fighter.specialty_pool = []
            fighter.specialty_gym_dues = 0
            # Earned belts/stripes and techniques belong to the fighter. Leaving
            # a room no longer erases grading progress.
            console.warn("Membership ended. Earned belts, stripes and techniques are kept.")
        return

    console.print("  A) BJJ rooms")
    console.print("  B) Kickboxing / Muay Thai rooms")
    console.print("  C) Judo dojos")
    console.print("  D) Taekwondo dojangs")
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    rows = data.BJJ_GYMS if ch == "A" else (data.KB_GYMS if ch == "B" else (data.JUDO_GYMS if ch == "C" else (data.TKD_GYMS if ch == "D" else [])))
    if not rows:
        return
    console.section("Available rooms")
    for i, g in enumerate(rows, start=1):
        pool = list(g.get("technique_pool") or [])
        preview = ", ".join(pool[:3])
        console.print("  %s) %s · coach %s" % (i, g["name"], g["coach"]))
        console.print("     $%s/week%s" % (g["weekly_dues"], (" · " + preview) if preview else ""), style="dim")
    console.print("  X) Back")
    raw = console.ask("Sign > ").strip().upper()
    if raw == "X":
        return
    try:
        g = rows[int(raw) - 1]
    except (ValueError, IndexError):
        console.warn("Invalid gym.")
        return
    console.info("Membership trains in the background each home week. Extra sessions accelerate it.")
    if console.ask("Join %s for $%s/week? A yes / B no > " % (g["name"], g["weekly_dues"])).strip().upper() != "A":
        return
    fighter.specialty_gym = g["name"]
    fighter.specialty_gym_type = "bjj" if ch == "A" else ("judo" if ch == "C" else ("tkd" if ch == "D" else "kb"))
    fighter.specialty_coach = g["coach"]
    fighter.specialty_pool = list(g.get("technique_pool") or [])
    fighter.specialty_gym_dues = int(g.get("weekly_dues", 0) or 0)
    fighter.specialty_gym_weeks = 0
    fighter.specialty_gym_tech_xp = 0
    fighter.specialty_gym_last_learn_week = 0
    fighter.specialty_gym_auto = True
    if ch == "A" and not fighter.bjj_belt:
        fighter.bjj_belt = "white"
        fighter.bjj_stripes = 0
    if ch == "C" and not fighter.judo_belt:
        fighter.judo_belt = "white"
    if ch == "D" and not getattr(fighter, "tkd_belt", None):
        fighter.tkd_belt = "white"
    console.good("Joined %s. %s will now develop with the room automatically." % (
        g["name"], "Belt and technique progress" if ch in ("A", "C", "D") else "Technique progress"))


def gym_menu(console: GameConsole, fighter: Fighter) -> None:
    """Functional team hub, owned by Coach rather than duplicated in Life."""
    from . import data
    console.header("GYM & TEAM", "One home, one specialist membership")
    status_strip(console, fighter)
    console.print("  A) Home MMA sparring")
    console.print("  B) Manage specialist gym")
    console.print("  C) Spar with teammate")
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    if ch in ("X", "0", ""):
        return
    if ch == "A":
        fighter.relationships["coach"] = min(100, fighter.relationships.get("coach", 50) + 3)
        fighter.energy = max(0, fighter.energy - 10)
        _spar_discover(console, fighter, "K")
        console.good("Rounds with your coach.")
        return
    if ch == "B":
        specialty_gym_menu(console, fighter)
        return
    if ch == "C":
        if not fighter.teammate:
            console.info("No named teammate yet. Fight and build gym relationships.")
            return
        fighter.energy = max(0, fighter.energy - 9)
        fighter.relationships["friends"] = min(100, fighter.relationships.get("friends", 50) + 2)
        _spar_discover(console, fighter, "G")
        console.good("Technical rounds with %s." % fighter.teammate)
    return


# ---------- SHOP ----------
def shop_menu(console: GameConsole, fighter: Fighter) -> None:
    console.header("SHOP", f"Cash ${fighter.money:,}")
    console.info("Performance support and everyday purchases.")
    console.print("  A) Supplements & anti-doping")
    console.print("  X) Back")
    choice = (console.ask("Shop > ") or "X").strip().upper()
    if choice == "A":
        supplement_menu(console, fighter)


# ---------- LIFESTYLE ----------
def lifestyle_menu(console: GameConsole, fighter: Fighter, pool=None) -> None:
    fighter.week_kind = getattr(fighter, "week_kind", "none") or "none"
    if fighter.week_kind == "full":
        fighter.week_kind = "none"
    while True:
        console.header("LIFE")
        status_strip(console, fighter)
        try:
            from .education import is_enrolled
            in_school = is_enrolled(fighter) or bool(getattr(fighter, "secondary_completed", False))
        except Exception:
            in_school = getattr(fighter, "school_status", "none") in ("school", "uni")
        section = getattr(console, "section", lambda title: console.print("\n  " + str(title)))
        section("PEOPLE")
        console.print("  A) People / relationships")
        console.print("  B) Manager")
        console.print("  C) Education")
        section("MONEY & RECOVERY")
        console.print("  D) Side job")
        console.print("  E) Shop")
        if int(getattr(fighter, "age", 16) or 16) >= 18:
            console.print("  F) Loan / debt")
        console.print("  N) Night out")
        console.print("  H) Rehab / physio")
        console.print("  I) International camp")
        if getattr(fighter, "fame", 0) >= 4 or getattr(fighter, "pro_debut", False):
            console.print("  S) Sponsors")
            console.print("  P) Promoters")
        if hasattr(console, "nav_footer"):
            console.nav_footer(home=True)
        else:
            console.print("  X Back   0 Home")
        choice = console.ask("\n  Life > ").strip().upper()
        if choice in ("0", "X", ""):
            choice = "0"
        elif choice == "A":
            choice = "P"
        elif choice == "B":
            choice = "M"
        elif choice == "C":
            choice = "U"
        elif choice == "D":
            choice = "K"
        elif choice == "E":
            choice = "11"
        elif choice == "F":
            choice = "L"
        elif choice == "N":
            choice = "PARTY"
        elif choice == "H":
            choice = "W"
        elif choice == "I":
            choice = "Q"
        elif choice == "S":
            choice = "10"
        elif choice == "P":
            choice = "12"
        # legacy number keys still work below
        if choice.upper() == 'P':
            from . import story
            if story.relationship_menu(console, fighter):
                fighter.week_kind = "half"
                break
            continue
        if choice.upper() == "PARTY":
            party_menu(console, fighter)
            if getattr(fighter, "week_kind", "") == "half":
                break
            continue
        if choice.upper() == 'S':
            spend_menu(console, fighter)
            continue
        if choice.upper() == 'U':
            school_menu(console, fighter)
            if getattr(fighter, "week_kind", "") == "half":
                break
            continue
        if choice.upper() == 'M':
            manager_menu(console, fighter, pool)
            continue
        if choice == '0':
            break
        if choice == '10':
            sign_sponsor(console, fighter)
            continue
        if choice == '11':
            shop_menu(console, fighter)
            # extras only — do not spend the week
            continue
        if choice == '12':
            from . import people
            people.meet_promoter_menu(console, fighter)
            continue
        if choice == "K":
            from .systems15 import job_rows, work_shift
            if getattr(fighter, "intl_camp", None):
                console.warn("You are abroad in an international camp. Home side jobs are unavailable.")
                continue
            console.header("SIDE JOBS", "One shift uses the week; pay rises slowly with reliability")
            console.print("  Job                         Pay   Energy Risk  Notes")
            for key, spec, ok, why in job_rows(fighter):
                lock = "" if ok else " [LOCKED]"
                console.print("  %s) %-22s $%-4s -%-5s %-4s  %s%s" % (
                    key, spec["name"], spec["pay"], spec["energy"], spec.get("risk", 1), spec.get("effect", ""), lock))
                if not ok:
                    console.print("     " + why, style="dim")
            pick = (console.ask("Job > ") or "X").strip().upper()
            if pick == "X":
                continue
            msg = work_shift(fighter, pick)
            if msg.startswith("Requires") or msg.startswith("No shift") or "cannot be worked" in msg:
                console.warn(msg)
                continue
            console.good(msg)
            fighter.week_kind = "full"
            break
        if choice == "L":
            from .systems15 import take_loan, repay_debt
            if int(getattr(fighter, "age", 16) or 16) < 18:
                console.warn("Loans are unavailable before age 18.")
                continue
            debt = int(getattr(fighter, "debt", 0) or 0)
            cash = int(getattr(fighter, "money", 0) or 0)
            console.header("LOAN / DEBT")
            console.print("Cash $%s · debt $%s · net $%s" % (cash, debt, cash - debt))
            console.print("Interest: ~1.2% each week on outstanding debt.")
            console.print("  A) Borrow $400")
            console.print("  B) Repay $100")
            console.print("  C) Repay $400")
            console.print("  D) Repay as much as possible")
            console.print("  X) Back")
            act = (console.ask("Debt > ") or "X").strip().upper()
            if act == "A":
                console.warn(take_loan(fighter, 400))
            elif act == "B":
                console.good(repay_debt(fighter, 100))
            elif act == "C":
                console.good(repay_debt(fighter, 400))
            elif act == "D":
                console.good(repay_debt(fighter, None))
            continue
        if choice == "W":
            from . import damage as _dmg
            act = _dmg.active_injuries(fighter)
            if not act:
                console.header("RECOVERY", "No active injury")
                console.print("  A) Take a recovery / physio week  (1 WEEK)")
                console.print("  X) Back")
                pick = (console.ask("Recovery > ") or "X").strip().upper()
                if pick != "A":
                    continue
                from .cut import rehab
                rehab(fighter, console)
                fighter.week_kind = "full"
                break
            console.section("MEDICAL")
            letters = "ABCDEFGH"
            for i, rec in enumerate(act[:8]):
                console.print("  %s) %s — %sw%s" % (
                    letters[i], rec["name"], rec["weeks"],
                    " (treated)" if rec.get("treated") else ""))
                if rec.get("cause"):
                    console.print("     %s" % rec["cause"], style="dim")
                if rec.get("surgery_cost"):
                    console.print("     surgery $%s · physio $%s" % (
                        rec["surgery_cost"], max(120, rec["surgery_cost"] // 4)))
                else:
                    console.print("     rest is the only treatment", style="dim")
            console.print("  R) Rest / rehab this week")
            console.print("  X) Back")
            pick = (console.ask("Treat > ") or "X").strip().upper()
            treated = False
            if pick in letters[:len(act[:8])]:
                rec = act[letters.index(pick)]
                if not rec.get("surgery_cost"):
                    console.warn("Nothing to operate on. Rest it.")
                else:
                    console.print("  A) Surgery $%s   B) Physio $%s   X) Back" % (
                        rec["surgery_cost"], max(120, rec["surgery_cost"] // 4)))
                    how = (console.ask("How > ") or "X").strip().upper()
                    if how == "A":
                        console.good(_dmg.treat(fighter, rec, "surgery", console))
                        treated = True
                    elif how == "B":
                        console.good(_dmg.treat(fighter, rec, "physio", console))
                        treated = True
            if pick == "X":
                continue
            if pick == "R":
                from .cut import rehab
                rehab(fighter, console)
                fighter.week_kind = "full"
                break
            if treated:
                fighter.week_kind = "full"
                break
            continue
        if choice == "Q":
            from . import camps
            if getattr(fighter, "intl_camp", None):
                spec = camps.active(fighter)
                console.header("INTERNATIONAL CAMP", spec.get("name", "Abroad"))
                console.print("  %s week(s) remaining" % int(getattr(fighter, "intl_camp_weeks", 0) or 0))
                console.print("  Focus: " + " / ".join(spec.get("focus", ())[:4]))
                console.print("  Coaches can teach: " + ", ".join(spec.get("teaches", ())))
                console.info("Home specialty gyms, private coaches and side jobs stay locked until you return.")
                console.info("Camp-specific training events resolve as the weeks pass.")
                continue
            ok, why = camps.can_go(fighter)
            if not ok:
                console.warn(why)
                console.pause(0.8)
                continue
            console.section("CAMPS ABROAD")
            console.print(camps.summary(fighter))
            console.print("")
            for k, v in camps.DESTINATIONS.items():
                pv = camps.preview(fighter, k)
                money_note = "" if pv["affordable"] else "  (short $%s)" % pv["shortfall"]
                console.print("  %s) %s" % (k, v["name"]))
                quote = "%sw · $%s%s · Q%s · Net %s" % (
                    v["weeks"], format(v["cost"], ","), money_note,
                    pv["quality"], pv["network"])
                for line in wrap_text(quote, max(12, console.width - 5)):
                    console.print("     " + line)
                focus = "Focus: " + " / ".join(v["focus"][:3])
                for line in wrap_text(focus, max(12, console.width - 5)):
                    console.print("     " + line)
                reward = "Reward: %s rare techniques + connection" % pv["reward_count"]
                for line in wrap_text(reward, max(12, console.width - 5)):
                    console.print("     " + line, style="dim")
                for line in wrap_text(v["note"], max(12, console.width - 5)):
                    console.print("     " + line, style="dim")
            console.print("  X) Stay home")
            pick = (console.ask("Camp > ") or "X").strip().upper()
            if pick not in camps.DESTINATIONS:
                continue
            console.good(camps.start(fighter, pick, console))
            fighter.week_kind = "full"
            break

        console.warn("Invalid.")
        console.pause(0.4)
        continue


def view_sponsors(console: GameConsole, fighter: Fighter) -> None:
    console.header("SPONSOR OFFERS")
    available = []
    for s in SPONSORS_DB:
        if cut.sponsor_allowed(fighter, s) and fighter.fame >= s.get('min_fame', 0):
            available.append(s)
    if not available:
        console.warn("No sponsors available. Build your résumé, fame, and audience!")
    else:
        console.print(f"Available sponsors (Fame: {fighter.fame}/100 · Followers: {fighter.followers}k):")
        for s in available:
            req = s['fame_req']
            color = "green" if fighter.fame >= req else "red"
            console.print(f"  [{color}]{s['name']}[/{color}] — ${s['money']} | Req: {req} | Obligation: {s['obligation']}")
    console.pause(2)


def sign_sponsor(console: GameConsole, fighter: Fighter) -> None:
    console.header("SIGN A SPONSOR")
    available = []
    for s in SPONSORS_DB:
        if cut.sponsor_allowed(fighter, s) and fighter.fame >= s.get('min_fame', 0):
            available.append(s)
    if not available:
        console.warn("No sponsors available. Build your résumé, fame, and audience!")
        console.pause(2)
        return

    console.print(f"Available sponsors (Fame: {fighter.fame}/100 · Followers: {fighter.followers}k):")
    for i, s in enumerate(available):
        req = s['fame_req']
        color = "green" if fighter.fame >= req else "red"
        console.print(f"  {i + 1}) [{color}]{s['name']}[/{color}] — ${s['money']} | Req: {req} | Obligation: {s['obligation']}")
    console.print("  X) Back")

    choice = console.ask("\n  Choice > ").upper()
    if choice == 'X':
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(available):
            sponsor = available[idx]
            if hasattr(fighter, 'sponsors') and fighter.sponsors:
                if sponsor['name'] in fighter.sponsors:
                    console.warn(f"You already have a deal with {sponsor['name']}.")
                    console.pause(1)
                    return
            else:
                fighter.sponsors = []
            from .data import sponsor_conflict
            if sponsor_conflict(sponsor['name'], fighter.sponsors):
                console.warn("Brand conflict with a current sponsor.")
                console.pause(0.6)
                return
            payout = int(sponsor['money'])
            try:
                from .education import degree_benefit
                payout = int(round(payout * float(degree_benefit(fighter, "sponsor_mult", 1.0))))
            except Exception:
                pass
            fighter.money += payout
            fighter.sponsors.append(sponsor['name'])
            console.good(f"Signed with {sponsor['name']}! +${payout}")
            console.info(f"Obligation: {sponsor['obligation']}")
            if supplement_sponsor(fighter) == sponsor['name']:
                console.gold("Sponsor benefit: legal supplements are now supplied free in the Shop.")
        else:
            console.warn("Invalid.")
    except ValueError:
        console.warn("Invalid.")
    console.pause(1)


# ---------- SOCIAL MEDIA ----------
def _follower_gain(fighter: Fighter, base_lo: int, base_hi: int) -> int:
    """Diminishing returns: harder to grow as you get bigger."""
    raw = random.randint(base_lo, base_hi)
    f = max(0, int(fighter.followers))
    if f >= 500:
        raw = max(0, raw // 4)
    elif f >= 200:
        raw = max(0, raw // 3)
    elif f >= 80:
        raw = max(0, int(raw * 0.4))
    elif f >= 30:
        raw = max(0, int(raw * 0.65))
    elif f >= 10:
        raw = max(0, int(raw * 0.85))
    return max(0, raw)


def social_media_menu(console: GameConsole, fighter: Fighter) -> None:
    console.header("SOCIAL MEDIA")
    console.print(f"Current followers: {fighter.followers}k")
    console.print(f"Press Hype: {fighter.press_hype}")
    console.print("Growth slows as your audience gets larger.")
    console.print("\nChoose an action:")
    console.print("  A) Post training clip (+followers, +fame)")
    console.print("  B) Post lifestyle photo (+followers, +happiness)")
    console.print("  C) Trash talk rival (+followers, +rivalry, +press_hype)")
    console.print("  D) Reply to fan comments (+followers, +happiness)")
    console.print("  E) Take a break from social media (+mental_toughness, +energy)")
    console.print("  F) Back")
    choice = console.ask("\n  Choice > ").upper()

    # weekly soft decay already handled elsewhere; small decay if huge
    if fighter.followers > 30 and random.random() < 0.25:
        decay = max(1, fighter.followers // 80)
        fighter.followers = max(0, fighter.followers - decay)

    if choice == 'A':
        gain = _follower_gain(fighter, 1, 3)
        fighter.followers += gain
        fame_gain = 1 if random.random() < 0.5 else 0
        from .notoriety import add_fame
        add_fame(fighter, fame_gain, "training clip")
        fighter.energy = max(0, fighter.energy - 5)
        msg = f"Training clip posted. +{gain}k followers"
        if fame_gain:
            msg += f", Fame +{fame_gain}"
        console.good(msg)
    elif choice == 'B':
        gain = _follower_gain(fighter, 1, 2)
        fighter.followers += gain
        fighter.happiness = min(100, fighter.happiness + 3)
        fighter.energy = max(0, fighter.energy - 3)
        console.good(f"Lifestyle post. +{gain}k followers, Happiness +3")
    elif choice == 'C':
        if fighter.rival:
            gain = _follower_gain(fighter, 2, 4)
            fighter.followers += gain
            fighter.press_hype = min(100, fighter.press_hype + 6)
            fighter.relationships["rival"] = min(100, fighter.relationships["rival"] + 8)
            fighter.energy = max(0, fighter.energy - 5)
            console.good(f"Trash talk lands. +{gain}k followers, Press Hype +6")
        else:
            console.info("You don't have a rival yet.")
    elif choice == 'D':
        gain = _follower_gain(fighter, 1, 2)
        fighter.followers += gain
        fighter.happiness = min(100, fighter.happiness + 2)
        fighter.energy = max(0, fighter.energy - 2)
        console.good(f"Engaged fans. +{gain}k followers, Happiness +2")
    elif choice == 'E':
        fighter.mental_toughness = min(100, fighter.mental_toughness + 3)
        fighter.energy = min(100, fighter.energy + 5)
        console.info("Social media break. Mental Toughness +3, Energy +5")
    elif choice == 'F':
        console.print("Back to lifestyle menu.")
    else:
        console.warn("Invalid.")
    console.pause(1)
    fighter._update_mood()


# ---------- PRESS CONFERENCE ----------
def press_conference(console: GameConsole, fighter: Fighter) -> None:
    console.header("PRESS CONFERENCE")
    if fighter.last_press_conf > 0:
        console.warn(f"You already held a press conference recently. Cooldown: {fighter.last_press_conf} weeks remaining.")
        console.pause(1)
        return

    console.print("You have a chance to build hype for your next fight.")
    console.print("  A) Be humble (+mental_toughness, +reputation)")
    console.print("  B) Be cocky (+press_hype, +fame, +rivalry)")
    console.print("  C) Avoid controversy (+discipline, -hype)")
    choice = console.ask("\nChoice > ").upper()

    if choice == 'A':
        fighter.mental_toughness = min(100, fighter.mental_toughness + 5)
        fighter.reputation += 5
        fighter.press_hype = max(0, fighter.press_hype - 5)
        console.good("Humble approach earns respect. Mental Toughness +5, Reputation +5")
    elif choice == 'B':
        fighter.press_hype = min(100, fighter.press_hype + 15)
        from .notoriety import add_fame
        add_fame(fighter, 5, "press conference")
        fighter.relationships["rival"] = min(100, fighter.relationships["rival"] + 5)
        fighter.confidence = min(100, fighter.confidence + 5)
        console.good("Cocky approach builds hype! Press Hype +15, Fame +5")
    elif choice == 'C':
        fighter.discipline = min(100, fighter.discipline + 5)
        fighter.press_hype = max(0, fighter.press_hype - 10)
        console.info("You steer clear of controversy. Discipline +5")
    else:
        console.warn("Invalid.")
        console.pause(1)
        return

    fighter.last_press_conf = 4
    fighter.energy -= 5
    console.pause(1)
    fighter._update_mood()


# ---------- CAREER STATS ----------
def view_career_stats(console: GameConsole, fighter: Fighter) -> None:
    """Compact fighter sheet: identity first, grouped attributes second."""
    console.header("FIGHTER")
    from . import v08
    from .ui import render_fighter_stats, wrap_text as _wrap
    def line(text, style=None):
        for part in _wrap(str(text), max(16, console.width - 2)):
            console.print("  " + part, style=style)
    total = fighter.get_total_record()
    phase = "Professional" if getattr(fighter, "pro_debut", False) else "Amateur"
    console.section("Career")
    line("%s   Age %s" % (fighter.name, fighter.age))
    line("Amateur %s-%s-%s   Pro %s-%s-%s" % (
        fighter.amateur_record[0], fighter.amateur_record[1], fighter.amateur_record[2],
        fighter.pro_record[0], fighter.pro_record[1], fighter.pro_record[2]))
    line("Total %s-%s-%s   %s" % (total[0], total[1], total[2], phase))
    org = getattr(fighter, "organization", None) or ("Free Agent" if getattr(fighter, "pro_debut", False) else "Amateur circuit")
    line(org)
    try:
        from . import contracts as _contracts
        deal = _contracts.active(fighter)
        if deal:
            left = int(deal.get("fights_left", 0) or 0)
            line("Contract: %s fight%s remaining" % (left, "" if left == 1 else "s"))
    except Exception:
        pass

    console.section("Condition")
    walk = float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 0)) or 0)
    bf = float(getattr(fighter, "bodyfat", 0) or 0)
    line("Weight %.1f kg   %s   Body fat %.1f%%" % (walk, getattr(fighter, "weight_class", "?"), bf))
    line("Energy %s   Health %s   Nutrition %s" % (fighter.energy, fighter.health, fighter.nutrition))
    line("Money $%s   Fame %s   Reputation %s" % (format(int(fighter.money), ","), fighter.fame, fighter.reputation))

    if getattr(fighter, "bjj_belt", None) or getattr(fighter, "judo_belt", None) or getattr(fighter, "tkd_belt", None):
        console.section("Belts")
        if getattr(fighter, "bjj_belt", None):
            stripes = int(getattr(fighter, "bjj_stripes", 0) or 0)
            console.print("  BJJ: %s Belt%s" % (str(fighter.bjj_belt).title(), ("   %s stripe%s" % (stripes, "" if stripes == 1 else "s")) if stripes else ""))
        if getattr(fighter, "judo_belt", None):
            console.print("  Judo: %s Belt" % str(fighter.judo_belt).title())
        if getattr(fighter, "tkd_belt", None):
            console.print("  Taekwondo: %s Belt" % str(fighter.tkd_belt).title())
        try:
            from . import amateur_sports as _as
            for art in ("bjj", "judo", "taekwondo"):
                if ((art == "bjj" and getattr(fighter, "bjj_belt", None)) or
                    (art == "judo" and getattr(fighter, "judo_belt", None)) or
                    (art == "taekwondo" and getattr(fighter, "tkd_belt", None))):
                    console.print("  " + _as.belt_progress_line(fighter, art), style="dim")
        except Exception:
            pass

    render_fighter_stats(console, fighter, detailed=False)

    if getattr(fighter, "specialty_gym", None):
        try:
            from . import gym_progression as _gym_progression
            console.section("Specialist Gym")
            for row in _gym_progression.status_lines(fighter):
                console.print("  " + row)
        except Exception:
            pass

    try:
        from . import amateur_sports
        amateur_sports.ensure(fighter)
        console.section("Amateur Sports")
        shown = 0
        for name in amateur_sports.SPORT_KEYS:
            key = amateur_sports.key_for(name)
            rec = fighter.sport_records[key]
            if sum(rec) or name == fighter.active_amateur_sport:
                nt = "   National Team" if fighter.sport_national_teams.get(key) else ""
                console.print("  %s: %s-%s-%s%s" % (name, rec[0], rec[1], rec[2], nt))
                shown += 1
                if shown >= 5:
                    break
    except Exception:
        pass

    fighter.sync_techniques()
    if fighter.technique_levels:
        console.section("Best Techniques")
        for tech, level in sorted(fighter.technique_levels.items(), key=lambda x: (-x[1], x[0]))[:8]:
            console.print("  %-24s Lv%s" % (tech[:24], level))

    getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(.2))("Press Enter to return")


# ---------- RANKINGS ----------
def _promotion_rankings_browser(console: GameConsole, pool, fighter=None) -> None:
    """Browse every named promotion board, even when the player is unsigned.

    Promotion rankings are world state, not a privilege of the player's
    current contract.  v1.39 only exposed the home board (when signed) and UFC,
    which made the other persistent promotion ladders effectively invisible.
    """
    from . import orgs
    from . import constants as C
    from . import identity as _id

    if hasattr(pool, "attach_player") and fighter is not None:
        pool.attach_player(fighter)
    if hasattr(pool, "update_rankings"):
        try:
            pool.update_rankings()
        except Exception:
            pass

    names = list(orgs.ORGS.keys())
    home = _id.canonical_org(fighter) if fighter is not None else ""
    if home in names:
        names.remove(home)
        names.insert(0, home)

    console.header("PROMOTION RANKINGS", "All organizations")
    for i, name in enumerate(names, start=1):
        spec = orgs.ORGS.get(name, {})
        tag = "  (your promotion)" if name == home else ""
        console.print("  %2d) %-18s T%s · %s%s" % (
            i, name, int(spec.get("tier", 0) or 0), spec.get("region", "World"), tag))
    console.print("  X) Back")
    raw = console.ask("\n  Promotion > " ).strip().upper()
    if raw in ("X", "0", ""):
        return
    try:
        org = names[int(raw) - 1]
    except (ValueError, IndexError):
        console.warn("Invalid promotion.")
        return

    console.header(org + " RANKINGS")
    console.print("  0) Champions snapshot")
    for i, wc in enumerate(C.WEIGHT_CLASSES, start=1):
        console.print("  %2d) %s" % (i, wc))
    hint = ""
    if fighter is not None and getattr(fighter, "weight_class", None) in C.WEIGHT_CLASSES:
        hint = " (Enter = %s)" % fighter.weight_class
    raw = console.ask("\n  Division%s > " % hint).strip()
    if raw == "" and fighter is not None and fighter.weight_class in C.WEIGHT_CLASSES:
        raw = str(C.WEIGHT_CLASSES.index(fighter.weight_class) + 1)
    if raw == "0":
        console.section("Champions")
        any_champ = False
        for wc in C.WEIGHT_CLASSES:
            champ = pool.belt_holder(org, wc) if hasattr(pool, "belt_holder") else None
            if champ is None:
                continue
            any_champ = True
            rec = list(getattr(champ, "pro_record", None) or [0, 0, 0])
            console.print("  %-18s %s · %s-%s-%s" % (wc, champ.name, rec[0], rec[1], rec[2]))
        if not any_champ:
            console.print("  No active champions yet.")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.0))("Press Enter to continue")
        return
    try:
        wc = C.WEIGHT_CLASSES[int(raw) - 1]
    except (ValueError, IndexError):
        console.warn("Invalid division.")
        return

    console.section("%s · %s" % (org, wc))
    champ = pool.belt_holder(org, wc) if hasattr(pool, "belt_holder") else None
    if champ is not None:
        rec = list(getattr(champ, "pro_record", None) or [0, 0, 0])
        info = (getattr(pool, "belts", None) or {}).get("%s|%s" % (org, wc), {})
        console.print("   C. %s  %s-%s-%s · %s defense%s" % (
            champ.name, rec[0], rec[1], rec[2], int(info.get("defenses", 0) or 0),
            "" if int(info.get("defenses", 0) or 0) == 1 else "s"))
    board = pool.get_org_top(org, wc, 15) if hasattr(pool, "get_org_top") else []
    if not board and champ is None:
        console.print("  No ranked fighters in this division yet.")
    player_seen = False
    for i, row in enumerate(board, start=1):
        rec = list(getattr(row, "pro_record", None) or [0, 0, 0])
        mine = fighter is not None and (row is fighter or (
            getattr(row, "fid", None) is not None and getattr(row, "fid", None) == getattr(fighter, "fid", object())))
        player_seen = player_seen or mine
        console.print("  %2d. %s  %s-%s-%s%s" % (
            i, row.name, rec[0], rec[1], rec[2], "  <- YOU" if mine else ""))
    if fighter is not None and home == org and fighter.weight_class == wc:
        if champ is fighter:
            console.gold("  You are the champion.")
        elif not player_seen:
            rank = (getattr(fighter, "story_flags", None) or {}).get("org_rank")
            if isinstance(rank, int) and rank <= 15:
                console.info("  Your current rank: #%s." % rank)
            elif getattr(fighter, "pro_debut", False):
                console.info("  You are on this roster but currently outside the top 15.")
    getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.0))("Press Enter to continue")


def view_rankings(console: GameConsole, pool, fighter=None) -> None:
    """Home-org board first. UFC is a separate list."""
    from . import identity as _id
    home = _id.canonical_org(fighter) if fighter is not None else ""
    console.header("RANKINGS")
    console.print("  P) Promotion rankings (all organizations)")
    if home and home != "UFC":
        console.print("  A) %s board" % home)
        console.print("  B) UFC weight class")
        console.print("  C) UFC pound-for-pound")
        console.print("  D) Legacy / Hall of Fame")
    else:
        console.print("  A) UFC weight class")
        console.print("  B) UFC pound-for-pound")
        console.print("  C) Legacy / Hall of Fame")
    console.print("  E) Upcoming promotion cards")
    console.print("  F) Recent completed cards")
    console.print("  G) Promotion rankings (all organizations)")
    console.print("  X) Back")
    choice = console.ask("\n  Choice > ").strip().upper()
    if choice == "X":
        return
    if choice in ("P", "G"):
        _promotion_rankings_browser(console, pool, fighter)
        return
    if choice == "F":
        console.section("Recent Cards")
        try:
            from . import promotion_events
            rows = promotion_events.completed_card_lines(pool, limit=6)
        except Exception:
            rows = []
        if not rows:
            console.print("  No completed promotion cards yet.")
        for line in rows:
            console.print("  " + line if not str(line).startswith("  ") else str(line))
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")
        return
    if choice == "E":
        console.section("Upcoming Cards")
        events = sorted((getattr(pool, "events", None) or []), key=lambda e: int(e.get("week", 0) or 0))[:12]
        if not events:
            console.print("  No cards announced yet.")
        for ev in events:
            bouts = list(ev.get("bouts") or [])
            head = next((b for b in bouts if b.get("slot") == "main"), bouts[0] if bouts else {})
            a = pool.get_by_id(head.get("red_id")) if head.get("red_id") != "PLAYER" else fighter
            b = pool.get_by_id(head.get("blue_id")) if head.get("blue_id") != "PLAYER" else fighter
            label = "%s vs %s" % (getattr(a, "name", "TBA"), getattr(b, "name", "TBA"))
            console.print("  w%s %s · %s" % (ev.get("week"), ev.get("org"), ev.get("location")))
            console.print("     %s%s" % (label, " · TITLE" if head.get("title") else ""))
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")
        return
    if home and home != "UFC" and choice == "A":
        wc = getattr(fighter, "weight_class", None) or "Lightweight"
        console.section("%s · %s" % (home, wc))
        if hasattr(pool, "update_rankings"):
            try:
                pool.attach_player(fighter)
                pool.update_rankings()
            except Exception:
                pass
        board = pool.get_org_top(home, wc, 12) if hasattr(pool, "get_org_top") else []
        if fighter is not None and fighter not in board:
            board = [fighter] + list(board)
            board = board[:12]
        if not board:
            console.print("  Thin roster this cycle. Win and the board fills.")
        for i, f in enumerate(board, start=1):
            rec = f.pro_record or [0, 0, 0]
            mine = fighter is not None and (f is fighter or getattr(f, "fid", None) == getattr(fighter, "fid", object()))
            console.print("  %2d. %s  %s-%s-%s%s" % (
                i, f.name, rec[0], rec[1], rec[2], "  <- YOU" if mine else ""))
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")
        return
    if home and home != "UFC":
        if choice == "C":
            choice = "B"
        elif choice == "B":
            choice = "A"
        elif choice == "D":
            choice = "C"
    if choice == "C":
        console.section("Legacy / Hall of Fame")
        try:
            from . import legacy
            inductees = list(getattr(pool, "hall_of_fame", None) or [])
            if inductees:
                console.section("Hall of Fame")
                for row in sorted(inductees, key=lambda x: float(x.get("score", 0) or 0), reverse=True)[:8]:
                    rec = row.get("record") or [0,0,0]
                    console.print("  %s · %s · %s-%s-%s" % (row.get("name"), row.get("tier"), rec[0], rec[1], rec[2]))
            else:
                console.print("  No retired inductees yet.")
            console.section("All-Time Record Book")
            book = legacy.record_book(pool, player=fighter, limit=3)
            labels = (("Pro wins","pro_wins"),("Title defenses","title_defenses"),
                      ("UFC defenses","ufc_defenses"),("Championship wins","championships"),
                      ("Performance bonuses","performance_bonuses"))
            for label, key in labels:
                vals = book.get(key) or []
                if vals:
                    console.print("  %s: %s (%s)" % (label, vals[0][1].name, vals[0][0]))
            doubles = []
            seen = set()
            for info in (getattr(pool, "belts", None) or {}).values():
                if not isinstance(info, dict): continue
                fid = info.get("fid"); org = info.get("org")
                if not fid: continue
                count = sum(1 for x in (getattr(pool, "belts", None) or {}).values()
                            if isinstance(x, dict) and x.get("fid") == fid and x.get("org") == org)
                if count >= 2 and (fid,org) not in seen:
                    seen.add((fid,org)); who = pool.get_by_id(fid)
                    if who is fighter or fid == getattr(fighter, "fid", None): who = fighter
                    if who: doubles.append("%s (%s)" % (who.name, org))
            if doubles:
                console.section("Two-Division Champions")
                for line in doubles[:8]: console.print("  " + line)
            if fighter is not None:
                score = legacy.hall_score(pool, fighter)
                stats = legacy.title_stats(pool, fighter)
                console.section("Your Legacy")
                console.print("  Hall score %.1f · %s" % (score, legacy.hall_tier(score)))
                console.print("  Titles %s · defenses %s · UFC defenses %s" % (
                    stats["title_wins"], stats["defenses"], stats["ufc_defenses"]))
        except Exception as exc:
            console.warn("Legacy board unavailable: %s" % exc)
        lineage = list(getattr(pool, "title_history", None) or [])[-5:]
        if lineage:
            console.section("Recent Title Lineage")
            for item in reversed(lineage):
                console.print("  w%s %s %s: %s %s" % (
                    item.get("week", 0), item.get("org", ""), item.get("weight_class", ""),
                    item.get("fighter") or "Vacant", item.get("action", "")))
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")
        return

    if choice == "B":
        console.section("UFC Pound-for-Pound")
        p4p = pool.get_p4p(15) if hasattr(pool, "get_p4p") else []
        if not p4p:
            console.print("  No UFC roster ranked yet.")
        for i, f in enumerate(p4p):
            rec = f.pro_record
            mine = fighter is not None and f is fighter
            console.print(
                f"  {i+1:>2}. {f.name} ({getattr(f, 'country_flag', '') or ''})  "
                f"{rec[0]}-{rec[1]}-{rec[2]}  {f.weight_class}"
                + ("  <- YOU" if mine else "")
            )
        if getattr(pool, "news", None):
            console.section("Recent")
            for line in pool.news[-4:]:
                console.print(f"  • {line}")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")
        return

    # Weight class — pick class or show all briefly
    console.print("Weight classes:")
    from . import constants as C
    for i, wc in enumerate(C.WEIGHT_CLASSES):
        console.print(f"  {i+1}) {wc}")
    console.print("  0) All champions snapshot")
    hint = ""
    if fighter is not None:
        hint = " (Enter = %s)" % fighter.weight_class
    raw = console.ask("\n  Class%s > " % hint).strip()
    if raw == "" and fighter is not None:
        raw = str(C.WEIGHT_CLASSES.index(fighter.weight_class) + 1)
    if raw == "0":
        console.section("UFC Champions")
        for wc in C.WEIGHT_CLASSES:
            ch = pool.champions.get(wc) if hasattr(pool, "champions") else None
            if ch:
                r = ch.pro_record
                info = (getattr(pool, "belts", None) or {}).get("UFC|" + wc, {})
                console.print(f"  {wc:<18} {ch.name}  {r[0]}-{r[1]}-{r[2]} · {int(info.get('defenses',0) or 0)} def")
            else:
                console.print(f"  {wc:<18} —")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")
        return
    try:
        wc = C.WEIGHT_CLASSES[int(raw) - 1]
    except (ValueError, IndexError):
        console.warn("Invalid.")
        return
    console.section(f"UFC {wc}")
    ch = pool.champions.get(wc) if hasattr(pool, "champions") else None
    if ch:
        r = ch.pro_record
        info = (getattr(pool, "belts", None) or {}).get("UFC|" + wc, {})
        console.print("   C. %s  %s-%s-%s · %s defense%s" % (
            ch.name, r[0], r[1], r[2], int(info.get("defenses",0) or 0),
            "" if int(info.get("defenses",0) or 0) == 1 else "s"))
    top = pool.get_top_10(wc) if hasattr(pool, "get_top_10") else []
    if not top and not ch:
        console.print("  No ranked fighters in this class.")
    me = False
    for i, f in enumerate(top[:15]):
        r = f.pro_record
        mine = (fighter is not None and f is fighter) or (
            fighter is not None and getattr(f, "fid", None) is not None
            and getattr(f, "fid", None) == getattr(fighter, "fid", object()))
        tag = "  <- YOU" if mine else ""
        if mine:
            me = True
        console.print("  %2d. %s  %s-%s-%s%s" % (i + 1, f.name, r[0], r[1], r[2], tag))
    if ch is not None and fighter is not None and ch is fighter:
        console.gold("  You are the champion of this division.")
        me = True
    if fighter is not None and not me:
        if (getattr(fighter, "organization", "") or "") == "UFC":
            if fighter.weight_class == wc:
                console.info("  You are on the UFC roster but not ranked in the top 15 yet.")
        elif fighter.weight_class == wc:
            console.print("  You are not in the UFC. Ranked spots are UFC only.", style="dim")
    getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")

def party_menu(console: GameConsole, fighter: Fighter) -> None:
    console.header("PARTY")
    if getattr(fighter, "hangover_weeks", 0) > 0:
        console.warn("You are still hungover.")
    console.print("  A) Quiet night ($15)  mood+")
    console.print("  B) Party ($40)  fame+ risk")
    console.print("  C) Club ($70)  only if anyone knows you")
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    if ch == "X":
        return
    if ch in ("B", "C") and fighter.energy < 35:
        console.warn("You are tired. Party will wreck the week.")
        if console.ask("Still go? A yes / B no: ").strip().upper() != "A":
            return
    if fighter.fight_cooldown == 0 and fighter.camp_active and ch in ("B", "C"):
        console.warn("Camp week. Coach will notice.")
    if ch == "A" and fighter.money >= 15:
        fighter.money -= 15
        fighter.happiness = min(100, fighter.happiness + 6)
        fighter.energy = max(0, fighter.energy - 4)
        fighter.weekly_spend = getattr(fighter, "weekly_spend", 0) + 15
        console.good("Quiet night.")
        fighter.week_kind = "half"
    elif ch == "B" and fighter.money >= 40:
        fighter.money -= 40
        fighter.happiness = min(100, fighter.happiness + 10)
        fighter.energy = max(0, fighter.energy - 10)
        fighter.nutrition = max(0, fighter.nutrition - 8)
        fighter.discipline = max(0, fighter.discipline - 4)
        fighter.hangover_weeks = max(fighter.hangover_weeks, 1)
        fighter.weekly_spend = getattr(fighter, "weekly_spend", 0) + 40
        if fighter.fame >= 5:
            from .notoriety import add_fame
            add_fame(fighter, 1, "night out visibility")
        console.warn("You went out. Hangover incoming.")
        fighter.week_kind = "half"
    elif ch == "C":
        from .events import can_media
        if not can_media(fighter):
            console.warn("Nobody is putting you on a list at 0-0.")
            console.pause(0.5)
            return
        if fighter.money < 70:
            console.warn("Broke.")
            return
        fighter.money -= 70
        from .notoriety import add_fame
        add_fame(fighter, 2, "club appearance")
        fighter.press_hype = min(100, fighter.press_hype + 4)
        fighter.energy = max(0, fighter.energy - 14)
        fighter.hangover_weeks = max(fighter.hangover_weeks, 2)
        fighter.weekly_spend = getattr(fighter, "weekly_spend", 0) + 70
        console.warn("Club. Photos exist now.")
        fighter.week_kind = "half"
    else:
        console.warn("Cancelled or not enough cash.")
    console.pause(0.5)


def spend_menu(console: GameConsole, fighter: Fighter) -> None:
    console.header("SPEND")
    console.print("Money $%s" % fighter.money)
    console.print("Living food/rent is auto. This is extras only.")
    console.print("  1) Gear $40")
    console.print("  2) Physio $50")
    console.print("  3) Night out snack $12")
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    costs = {"1": (40, "striking", 1), "2": (50, "health", 12), "3": (12, "happiness", 4)}
    if ch not in costs:
        return
    cost, stat, amt = costs[ch]
    if fighter.money < cost:
        console.warn("Not enough.")
        return
    fighter.money -= cost
    fighter.weekly_spend = getattr(fighter, "weekly_spend", 0) + cost
    cur = getattr(fighter, stat, 0)
    setattr(fighter, stat, min(100, int(cur) + amt))
    if ch == "2":
        inj = getattr(fighter, "injury", None) or {}
        if inj.get("weeks"):
            inj["weeks"] = max(0, int(inj["weeks"]) - 2)
            fighter.injury = inj
            console.info("Physio cut injury time.")
        dmg = getattr(fighter, "damage", {}) or {}
        for k in list(dmg):
            if k != "total":
                dmg[k] = max(0, int(dmg.get(k,0)) - 8)
        dmg["total"] = sum(dmg.get(k,0) for k in ("cuts","nose","eyes","body","legs"))
        fighter.damage = dmg
    console.good("Spent $%s" % cost)
    console.pause(0.4)


def school_menu(console: GameConsole, fighter: Fighter) -> bool:
    from .education import menu
    return bool(menu(console, fighter))


def manager_menu(console: GameConsole, fighter: Fighter, pool=None) -> None:
    from . import orgs, people
    console.header("MANAGER")
    if not fighter.pro_debut:
        console.warn("Amateur. No serious manager mail.")
        console.pause(0.4)
        return
    current = people.current_manager(fighter)
    if not current:
        people.manager_office_menu(console, fighter)
        return
    rel = people.rapport(fighter, current.id)
    console.print("%s (%s) · %s · %d%% cut  |  rapport %d/100  |  you: %s  fame %s" % (
        current.name, current.archetype, fighter.manager or current.agency,
        current.cut_pct, rel, fighter.organization or "free agent", fighter.fame))
    console.print("  A) Open fight offers")
    console.print("  B) Push for a better purse on your booked date")
    console.print("  C) Ask for a transfer / new org")
    console.print("  S) Sign / stay with an organization")
    console.print("  D) Fire manager")
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    if ch == "D":
        people.fire_manager(fighter)
        console.info("Unsigned. Inbox goes quiet. %s won't forget it fast." % current.name)
        return
    if ch == "B":
        booked = getattr(fighter, "booked_fight", None)
        if not isinstance(booked, dict):
            console.warn("No date to negotiate.")
            return
        if booked.get("negotiated"):
            console.warn("Already pushed this card.")
            return
        ok, new_purse, line = people.negotiate_purse(fighter, booked)
        if ok:
            booked["purse_win"] = new_purse
            booked["negotiated"] = True
            console.good(line)
        else:
            booked["negotiated"] = True
            console.warn(line)
        return
    if ch == "S":
        names = orgs.eligible_orgs(fighter) or [orgs.home_org(getattr(fighter, "country", "") or "")]
        wins = int((fighter.pro_record or [0])[0])
        if wins < 2:
            console.warn("Orgs want a couple of pro wins before an exclusive deal. Take local dates first.")
            return
        for i, name in enumerate(names[:8]):
            console.print("  %s) %s" % ("ABCDEFGH"[i], name))
        raw = console.ask("Sign > ").strip().upper()
        letters = "ABCDEFGH"
        if raw in letters[:len(names[:8])]:
            org = names[letters.index(raw)]
            orgs.sign_org(fighter, org)
            console.good("Paper with %s." % org)
        return
    if ch not in ("A", "C"):
        return
    # Booking lives in exactly one place. This used to call inbox_night with
    # pool=None, so offers built from the manager menu had no world to draw
    # opponents from and could disagree with the same offer seen elsewhere.
    from . import matchroom
    matchroom.book(console, fighter, pool)
    return
    offers = orgs.inbox(fighter, n=4 if ch == "C" else 3)
    if not offers:
        console.warn("Nothing this week. Win and wait.")
        return
    letters = "ABCDEFGH"
    for i, off in enumerate(offers):
        mark = " SUPERFIGHT" if off.get("superfight") else ""
        console.print("  %s) %s  $%s  week %s  %s%s" % (
            letters[i], off["org"], off["purse_win"], off["date_week"], off["tag"], mark))
    raw = console.ask("Take > ").strip().upper()
    if raw not in letters[:len(offers)]:
        return
    off = offers[letters.index(raw)]
    orgs.sign_org(fighter, off["org"])
    from .fights import generate_random_opponent
    opp = generate_random_opponent(fighter)
    fighter.booked_fight = {
        "room": fighter.room, "org": off["org"], "opponent": opp,
        "date_week": off["date_week"], "purse_win": off["purse_win"],
        "purse_show": off["purse_show"], "tag": off["tag"],
        "card": ["MAIN  YOU vs %s" % opp.name],
    }
    pick_and_start_camp(console, fighter, max(2, off["date_week"] - fighter.week))
    console.good("Signed with %s. Fight week %s." % (off["org"], off["date_week"]))
