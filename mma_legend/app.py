"""Character creation, the main menu, and the week-by-week game loop."""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Phone editors tap this file as a script. Relative imports need a package.
if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    _parent = str(_here.parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    __package__ = "mma_legend"
    if "mma_legend" not in sys.modules:
        import importlib
        sys.modules["mma_legend"] = importlib.import_module("mma_legend")

from . import career
from . import constants as C
from . import data
from . import diagnostics
from . import events
from . import story
from . import fights
from . import persistence
from .models import Fighter
from .ui import GameConsole, render_dashboard, render_fighter_stats, status_strip
from .world import FighterPool

_DISCIPLINE_CHOICES = {
    "A": ("Boxing", "+striking, +speed, +IQ"),
    "B": ("Wrestling", "+grappling, +takedown def, +strength, +cardio"),
    "C": ("Muay Thai", "+striking, +kicks, +durability"),
    "D": ("Combat Sambo", "+grappling, +submissions, +striking"),
    "E": ("BJJ", "+submissions, +ground control, +IQ"),
    "F": ("Judo", "+throws, +takedown defense, +control"),
    "G": ("Taekwondo", "+kicks, +speed, +distance control"),
    "H": (None, "Balanced start, no bonus"),
}


def choose_amateur_discipline(console: GameConsole) -> str | None:
    console.header("CHOOSE YOUR BACKGROUND")
    console.print("Your amateur background shapes your starting skills:")
    for key, (name, desc) in _DISCIPLINE_CHOICES.items():
        console.print(f"  {key}) {name or 'None':<12} ({desc})")
    choice = console.ask("\n  Choice > ").strip().upper()
    discipline, _ = _DISCIPLINE_CHOICES.get(choice, (None, ""))
    if choice not in _DISCIPLINE_CHOICES:
        console.warn("Invalid. Using balanced start.")
    elif discipline:
        console.good(f"Selected {discipline}!")
    else:
        console.info("Balanced start. No background bonus.")
    console.auto_pause("Background chosen")
    return discipline



def _pick_country(console: GameConsole):
    countries = list(data.COUNTRIES)
    console.print("COUNTRY: X random  /  type name  /  number")
    page = 0
    size = 8
    while True:
        chunk = countries[page*size:(page+1)*size]
        for i, c in enumerate(chunk):
            n = page*size + i + 1
            console.print("  %d) %s %s" % (n, c.get("flag",""), c["name"]))
        console.print("  N next  P prev  X random")
        raw = console.ask("Country > ").strip()
        up = raw.upper()
        if up == "X":
            return random.choice(countries)
        if up == "N":
            page = (page + 1) % max(1, (len(countries)+size-1)//size)
            continue
        if up == "P":
            page = (page - 1) % max(1, (len(countries)+size-1)//size)
            continue
        matches = [c for c in countries if raw.lower() in c["name"].lower()]
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(countries):
                return countries[idx]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            for c in matches[:8]:
                console.print("  - " + c["name"])
            continue
        console.warn("Not found.")


def create_fighter(console: GameConsole) -> Fighter:
    console.header("CREATE YOUR FIGHTER")
    name = console.ask("Enter your fighter's name: ").strip()
    while not name:
        name = console.ask("Name cannot be empty: ").strip()

    country_data = _pick_country(console)

    console.print("\nPHYSIQUE:", style="bold")
    console.print("  A) Lean")
    console.print("  B) Athletic")
    console.print("  C) Stocky")
    console.print("  D) Tall")
    console.print("  E) Heavy-built")
    console.print("  F) Compact")
    physique = console.ask("Choice (A-F): ").strip().upper()
    while physique not in list("ABCDEF"):
        physique = console.ask("Invalid. A-F: ").strip().upper()

    discipline = choose_amateur_discipline(console)

    console.print("\nSIZE: A) Choose height & weight  B) Random")
    size_mode = console.ask("Choice (A/B): ").strip().upper()
    height = weight = None
    if size_mode == "A":
        raw_h = console.ask("Height in cm (160-200, empty=random): ").strip()
        raw_w = console.ask("Weight in kg (52-120, empty=random): ").strip()
        try:
            if raw_h:
                height = max(160, min(200, int(raw_h)))
        except ValueError:
            height = None
        try:
            if raw_w:
                weight = max(52, min(120, int(raw_w)))
        except ValueError:
            weight = None
    fighter = Fighter.new_player(name, physique, country_data, discipline, height=height, weight=weight)
    from .cut import physique_from_letter
    fighter.physique_type = physique_from_letter(physique)
    console.info("%s cm / %s kg / %s / %s" % (fighter.height, fighter.weight, fighter.weight_class, fighter.physique_type))

    console.print("EDUCATION: A) Secondary school  B) Left school")
    sc = console.ask("Choice > ").strip().upper()
    if sc == "B":
        fighter.education_stage = "none"
        fighter.school_status = "none"
        fighter.secondary_completed = False
    else:
        fighter.education_stage = "secondary"
        fighter.school_status = "school"
        fighter.secondary_completed = False
    fighter.fight_details = "Round"
    return fighter


def create_quick_fighter(console: GameConsole) -> Fighter:
    """Skip the form. Random body, style, country. A few amateur weeks already lived."""
    first = ("James", "Alex", "Marco", "Ivan", "Omar", "Luis", "Noah", "Kenji",
             "Rafael", "Ahmed", "Adam", "Leo", "Viktor", "Mateo", "Sean")
    last = ("Silva", "Garcia", "Smith", "Ivanov", "Kim", "Novak", "Costa",
            "Murphy", "Petrov", "Khan", "Brown", "Alvarez", "Popov")
    try:
        from .world import _FIRST, _LAST
        first, last = _FIRST, _LAST
    except Exception:
        pass
    countries = list(data.COUNTRIES) or [{"name": "USA", "flag": "🇺🇸", "bonus": {}}]
    country_data = random.choice(countries)
    if not isinstance(country_data, dict):
        country_data = {"name": "USA", "flag": "🇺🇸", "bonus": {}}
    name = "%s %s" % (random.choice(first), random.choice(last))
    physique = random.choice(list("ABCDEF"))
    discipline = random.choice(["Boxing", "Wrestling", "BJJ", "Muay Thai", "Combat Sambo", "Judo", "Taekwondo"])
    fighter = Fighter.new_player(name, physique, country_data, discipline)
    from .cut import physique_from_letter
    fighter.physique_type = physique_from_letter(physique)
    fighter.fight_details = "Round"
    fighter.age = random.randint(17, 20)
    if fighter.age < 18:
        fighter.education_stage = "secondary"
        fighter.school_status = "school"
        fighter.secondary_completed = False
    else:
        fighter.secondary_completed = True
        fighter.education_stage = random.choice(["gap", "gap", "university"])
        fighter.school_status = "uni" if fighter.education_stage == "university" else "none"
        if fighter.education_stage == "university":
            from .education import DEGREES, scholarship_offer
            fighter.university_degree = random.choice(list(DEGREES))
            fighter.university_semester = random.randint(1, 3)
            fighter.university_credits = (fighter.university_semester - 1) * 30
            fighter.university_scholarship = scholarship_offer(fighter)
    fighter.week = 1 + (fighter.age - 16) * 52 + random.randint(8, 24)
    w = random.randint(2, 5)
    l = random.randint(0, 2)
    fighter.amateur_record = [w, l, 0]
    rec = dict(getattr(fighter, "sport_records", None) or {})
    rec["mma"] = [w, l, 0]
    fighter.sport_records = rec
    fighter.fame = max(1, w - l)
    fighter.reputation = 4 + w * 2
    fighter.sync_techniques()
    if discipline == "BJJ" and not fighter.bjj_belt:
        fighter.bjj_belt = "white"
    console.gold("QUICK PLAY — %s" % name)
    console.print("%s · %s · %s · %s-%s amateur · week %s" % (
        fighter.country, fighter.weight_class, discipline, w, l, fighter.week))
    console.pause(0.6)
    return fighter


def main_menu(console: GameConsole) -> str:
    """Simple startup menu, deliberately close to the pre-1.35 flow."""
    console.header("🥊 MMA LEGEND", "FROM NOTHING TO LEGEND  v%s" % C.GAME_VERSION)
    console.print("  Start from nothing. Earn the fights.", style="dim")
    if persistence.AUTO.exists():
        console.print("  Autosave: %s" % persistence._slot_label(persistence.AUTO), style="dim")
    console.section("PLAY")
    console.menu_table([
        ("1", "", "New Career", ""),
        ("2", "", "Load Career", ""),
        ("3", "", "Quick Play", ""),
    ])
    console.section("SYSTEM")
    console.menu_table([
        ("4", "", "How to Play", ""),
        ("5", "", "Options", ""),
        ("6", "", "System Check", ""),
        ("7", "", "Quit", ""),
    ])
    validation = data.validate_data()
    if validation:
        console.warn("Data audit: %s issue(s)." % len(validation))
    return console.ask("\n  Choose > ").strip().upper()

def quick_tutorial(console: GameConsole) -> None:
    """Short linear tutorial: controls first, then career, then fights."""
    pages = [
        ("1 OF 3  THE WEEK", [
            "You choose one main action each week.",
            "A Train, B Rest, D Amateur, N Nutrition, T Team, E Life.",
            "C Fight appears when you are booked or after you turn professional.",
            "H Fighter, I Rankings, L Calendar, O Inbox, Z Timeline, J Save, P Settings.",
            "Only completed activities advance the week. Opening or leaving a menu does not.",
        ]),
        ("2 OF 3  BUILD THE CAREER", [
            "Start amateur. Train, fight locally, enter championships and build a real résumé.",
            "Your amateur and professional records stay separate.",
            "Turn pro when ready. Pro careers use promotions, contracts, rankings, cards and titles.",
            "If something is locked, the game should tell you the requirement instead of silently hiding it.",
        ]),
        ("3 OF 3  FIGHT PREP", [
            "Amateur fights are booked inside D Amateur. C is for booked fight prep/fight night and the pro fight route.",
            "Nutrition controls real walking weight. Water cutting only happens when you are actually over a class limit.",
            "On fight night choose a gameplan, then watch Instant, Live Sim or Play-by-play.",
            "Use ? from the weekly screen whenever you forget a control.",
        ]),
    ]
    for i, (title, lines) in enumerate(pages):
        console.header("HOW TO PLAY", "%s · v%s" % (title, C.GAME_VERSION))
        for line in lines:
            console.print("  " + line)
        if i < len(pages) - 1:
            getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(.2))("Press Enter for next page")
        else:
            getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(.2))("Press Enter to return")

def show_highlights(console: GameConsole, fighter: Fighter) -> None:
    console.print("Career Highlights:", style="bold")
    if fighter.pro_record[0] >= 20:
        console.print("  🏆 Multiple championship wins")
    if fighter.amateur_titles:
        console.print(f"  🏅 Amateur titles: {', '.join(fighter.amateur_titles)}")
    if fighter.legacy_score >= 50:
        console.print("  ⭐ Hall of Fame worthy")
    if fighter.rival:
        console.print(f"  🔥 Notable rival: {fighter.rival}")
    if fighter.pro_record[0] > 0:
        console.print(f"  ✅ {fighter.pro_record[0]} pro wins")
    if fighter.followers > 100:
        console.print(f"  📱 Over {fighter.followers}k followers")
    if fighter.national_team:
        console.print("  %s National Team member" % (fighter.country_flag or "🌍"))
    if fighter.technique_levels:
        top_tech = max(fighter.technique_levels.items(), key=lambda x: x[1])
        console.print(f"  💪 Best Technique: {top_tech[0]} (Level {top_tech[1]})")


def game_over(console: GameConsole, fighter: Fighter) -> None:
    console.header("CAREER OVER")
    console.warn(f"{fighter.name}'s career has ended.")
    why = fighter.end_reason() or "unknown"
    console.print("Reason: %s" % why)

    total = fighter.get_total_record()
    console.print(f"\nFinal Record (Total): {total[0]}-{total[1]}-{total[2]}")
    console.print(f"Amateur: {fighter.amateur_record[0]}-{fighter.amateur_record[1]}-{fighter.amateur_record[2]}")
    console.print(f"Pro: {fighter.pro_record[0]}-{fighter.pro_record[1]}-{fighter.pro_record[2]}")
    console.print(f"Age: {fighter.age} | Money: ${fighter.money} | Fame: {fighter.fame} | Legacy: {fighter.legacy_score}")

    if fighter.legacy_score >= 50:
        rank = "🏆 LEGEND"
    elif fighter.legacy_score >= 30:
        rank = "⭐ GREAT"
    elif fighter.legacy_score >= 15:
        rank = "👍 SOLID"
    else:
        rank = "👤 JOURNEYMAN"
    console.gold(f"\nHall of Fame Rank: {rank}")

    show_highlights(console, fighter)
    console.print("\nAmateur Titles:" if fighter.amateur_titles else "\nNo amateur titles.")
    for title in fighter.amateur_titles:
        console.print(f"  - {title}")
    if fighter.rival:
        console.print(f"\nRival: {fighter.rival}")
    if fighter.teammate:
        console.print(f"Teammate: {fighter.teammate}")
    console.auto_pause("Game Over")


_ACTIONS = [
    ("A", "", "Train", ""),
    ("B", "", "Rest", ""),
    ("C", "🥊", "Fight", ""),
    ("D", "", "Amateur", ""),
    ("N", "", "Nutrition", ""),
    ("T", "", "Team", ""),
    ("E", "", "Life", ""),
    ("H", "", "Fighter", ""),
    ("I", "", "Rankings", ""),
    ("L", "", "Calendar", ""),
    ("O", "", "Inbox", ""),
    ("Z", "", "Timeline", ""),
    ("J", "", "Save", ""),
    ("P", "", "Settings", ""),
    ("K", "", "Retire", ""),
]



def _debug_boost(fighter, console) -> None:
    """Hidden tester key. Type * at the weekly prompt."""
    from . import constants as C
    for s in C.SKILLS:
        setattr(fighter, s, min(95, getattr(fighter, s) + 8))
    fighter.money += 8000
    from .notoriety import add_fame
    add_fame(fighter, 12, "debug boost")
    fighter.energy = 100
    fighter.health = 100
    fighter.pro_debut = True
    fighter.pro_record = [max(fighter.pro_record[0], 6), fighter.pro_record[1], fighter.pro_record[2]]
    from . import booking
    if booking.current_room(fighter) in ("local", ""):
        booking.set_room(fighter, "mid")
    fighter.sync_techniques()
    console.gold("DEBUG: mid-org pro. C Fight is the booker.")


def _actions_for(fighter):
    rows = []
    booked = getattr(fighter, "booked_fight", None)
    date_ok = isinstance(booked, dict) and booked.get("date_week")
    fight_week = bool(date_ok and fighter.week >= int(booked.get("date_week") or 0))
    for key, icon, name, desc in _ACTIONS:
        if key == "D" and getattr(fighter, "pro_debut", False):
            continue
        if key == "I" and not getattr(fighter, "pro_debut", False) and getattr(fighter, "fame", 0) < 8:
            continue
        # Amateur fight booking belongs inside the Amateur menu.  The main
        # Fight key only appears for an already-booked amateur bout or once pro.
        if key == "C" and not getattr(fighter, "pro_debut", False) and not date_ok:
            continue
        if key == "C":
            if fight_week:
                name = "Fight Night"
            elif date_ok:
                name = "Fight Prep"
            else:
                name = "Fight"
        rows.append((key, icon, name, ""))
    try:
        from . import v08
        if (str(getattr(fighter, "active_amateur_sport", "MMA") or "MMA") == "MMA"
                and v08.turn_pro_ready(fighter) and not v08.turn_pro_on_cooldown(fighter)
                and not getattr(fighter, "pro_debut", False)):
            rows.insert(7, ("G", "", "Turn Pro", ""))
    except (TypeError, ValueError, AttributeError, ImportError):
        pass
    return rows

def _amateur_hub(console: GameConsole, fighter: Fighter, pool: FighterPool) -> None:
    from . import amateur_sports
    amateur_sports.ensure(fighter)
    sport = fighter.active_amateur_sport
    key = amateur_sports.key_for(sport)
    rec = fighter.sport_records[key]
    console.header("AMATEUR", "%s competition career" % sport)
    status_strip(console, fighter)
    console.print("  Focus: %s · %s-%s-%s" % (sport, rec[0], rec[1], rec[2]))
    focus_key = amateur_sports.key_for(fighter.active_amateur_sport)
    if fighter.sport_national_teams.get(focus_key):
        console.gold("  National team: %s" % fighter.active_amateur_sport)
    if sport == "MMA":
        console.print("  A) Book local MMA fight")
        console.print("  B) Local MMA tournament")
        console.print("  C) MMA championships")
    else:
        console.print("  A) Local %s match" % sport)
        console.print("  B) %s championships" % sport)
        recent = amateur_sports.recent_fights(fighter, sport, limit=2)
        for row in recent:
            console.info("  Last: %s" % row)
    console.print("  S) Change active sport")
    from . import v08
    if sport == "MMA" and v08.turn_pro_ready(fighter):
        console.print("  G) Turn professional")
        if v08.turn_pro_on_cooldown(fighter):
            console.info("Turn-pro on cooldown.")
    if hasattr(console, "nav_footer"):
        console.nav_footer(home=True)
    else:
        console.print("  X Back   0 Home")
    if sport == "MMA" and not v08.continental_eligible(fighter):
        try:
            from . import amateur_sports
            label = amateur_sports.continental_name(getattr(fighter, "country", ""))
        except Exception:
            label = "Continental championship"
        console.info("%s locked: NT + National silver/gold." % label)
    c = console.ask("\n  Choice > ").strip().upper()
    if c in ("X", "0", ""):
        return
    if c == "A":
        if sport == "MMA":
            fights.find_fight(console, fighter, pool)
        else:
            amateur_sports.compete(console, fighter, pool)
    elif c == "B":
        if sport == "MMA":
            fights.enter_tournament(console, fighter, pool)
        else:
            amateur_sports.championship(console, fighter, pool)
    elif c == "C" and sport == "MMA":
        fights.competition_menu(console, fighter, pool)
    elif c == "S":
        amateur_sports.choose_sport(console, fighter)
    elif c == "G" and sport == "MMA" and v08.turn_pro_ready(fighter) and not v08.turn_pro_on_cooldown(fighter):
        fights.turn_pro(console, fighter)


def _career_hub(console: GameConsole, fighter: Fighter, pool: FighterPool) -> None:
    """Career information hub. Browsing never spends a week."""
    from . import ux
    while True:
        console.header("CAREER", "Where you are, what is next, and why")
        status_strip(console, fighter)
        console.print("  A) Overview / next objective")
        console.print("  B) Fighter sheet")
        console.print("  C) Calendar")
        console.print("  D) Timeline / fight history")
        console.print("  E) Rankings / titles")
        if not getattr(fighter, "pro_debut", False):
            console.print("  F) Amateur career / championships")
        console.print("  G) Nutrition / weight")
        try:
            from . import notify
            n = len(notify.unread(fighter))
        except Exception:
            n = 0
        console.print("  H) Alerts / inbox%s" % (" (%s NEW)" % n if n else ""))
        console.print("  I) Finances")
        console.print("  P) Interface preferences")
        if hasattr(console, "nav_footer"):
            console.nav_footer(home=True)
        else:
            console.print("  X Back   0 Home")
        ch = console.ask("Career > ").strip().upper()
        if ch in ("X", "0", ""):
            return
        if ch == "A":
            ux.career_overview(console, fighter, pool)
            getattr(console, "continue_prompt", lambda *_a, **_k: None)("Press Enter to return")
        elif ch == "B":
            ux.fighter_sheet(console, fighter)
        elif ch == "C":
            ux.calendar_view(console, fighter, pool)
        elif ch == "D":
            from . import timeline
            timeline.render(console, fighter)
        elif ch == "E":
            career.view_rankings(console, pool, fighter)
        elif ch == "F" and not getattr(fighter, "pro_debut", False):
            _amateur_hub(console, fighter, pool)
        elif ch == "G":
            before = repr(fighter.to_dict())
            career.nutrition_menu(console, fighter)
            if repr(fighter.to_dict()) != before:
                fighter.week_kind = "full"
                return
        elif ch == "H":
            from . import notify
            notify.inbox_menu(console, fighter)
        elif ch == "I":
            from . import economy
            economy.render(console, fighter)
            getattr(console, "continue_prompt", lambda *_a, **_k: None)("Press Enter to return")
        elif ch == "P":
            _career_preferences(console, fighter)
        else:
            console.warn("Invalid.")

def _career_preferences(console: GameConsole, fighter: Fighter) -> None:
    while True:
        console.header("INTERFACE", "Saved with this career")
        console.print("  A) Compact dashboard: %s" % ("ON" if getattr(fighter, "ui_compact", False) else "OFF"))
        console.print("  B) Week report: %s" % ("ON" if getattr(fighter, "ui_week_report", True) else "OFF"))
        console.print("  C) Fight view: %s" % (getattr(fighter, "fight_details", "Sim") or "Sim"))
        console.print("  D) Color: %s" % ("ON" if console.color else "OFF"))
        if hasattr(console, "nav_footer"):
            console.nav_footer(home=True)
        else:
            console.print("  X Back   0 Home")
        ch=(console.ask("Choice > ") or "X").strip().upper()
        if ch in ("X","0",""): return
        if ch == "A": fighter.ui_compact = not bool(getattr(fighter, "ui_compact", False))
        elif ch == "B": fighter.ui_week_report = not bool(getattr(fighter, "ui_week_report", True))
        elif ch == "C": _set_fight_detail(console, fighter)
        elif ch == "D":
            if not bool(getattr(console, "color_forced_off", False)):
                console.color = not bool(console.color)
                fighter.ui_color = bool(console.color)
            else:
                console.warn("Color is disabled by --no-color.")
        else: console.warn("Invalid.")


def _coach_hub(console: GameConsole, fighter: Fighter) -> None:
    if career.coach_talk_menu(console, fighter):
        fighter.week_kind = "full"



def _set_fight_detail(console: GameConsole, fighter: Fighter) -> None:
    console.print(f"Current: {getattr(fighter, 'fight_details', 'Sim')}")
    console.print("  A) Instant — result/card only")
    console.print("  B) Live Sim — automatic fight + corner summaries")
    console.print("  C) Play-by-play — interactive moments")
    d = console.ask("Choice (A-C): ").strip().upper()
    fighter.fight_details = {"A": "Instant", "B": "Sim", "C": "Full"}.get(d, fighter.fight_details or "Sim")
    console.good(f"Fight view set to {fighter.fight_details}")
    console.pause(0.3)


def _week_snapshot(fighter) -> dict:
    snap = {
        "money": int(getattr(fighter, "money", 0) or 0), "energy": int(getattr(fighter, "energy", 0) or 0),
        "health": int(getattr(fighter, "health", 0) or 0), "nutrition": int(getattr(fighter, "nutrition", 0) or 0),
        "fame": int(getattr(fighter, "fame", 0) or 0), "weight": round(float(getattr(fighter, "walking_weight", 0) or 0), 2),
    }
    for stat in C.SKILLS:
        snap[stat] = int(getattr(fighter, stat, 0) or 0)
    return snap


def _render_week_report(console: GameConsole, fighter, before: dict) -> None:
    after = _week_snapshot(fighter)
    changes = []
    labels = {"money": "$", "energy": "Energy", "health": "Health", "nutrition": "Nutrition", "fame": "Fame"}
    for key in ("money", "energy", "health", "nutrition", "fame"):
        d = after[key] - before[key]
        if d:
            if key == "money": changes.append("Money %s$%s" % ("+" if d > 0 else "-", abs(d)))
            else: changes.append("%s %+d" % (labels[key], d))
    wd = round(after["weight"] - before["weight"], 2)
    if abs(wd) >= 0.05:
        changes.append("Weight %+.2fkg" % wd)
    for stat in C.SKILLS:
        d = after[stat] - before[stat]
        if d:
            changes.append("%s %+d" % (C.SKILL_LABELS.get(stat, stat), d))
    if not changes:
        changes = [str(getattr(fighter, "last_week_note", "Week completed") or "Week completed")]
    fighter.last_week_report = changes[:10]
    console.section("WEEK REPORT")
    for line in changes[:8]:
        console.print("  • " + line)
    if len(changes) > 8:
        console.print("  • +%s more changes" % (len(changes) - 8), style="dim")


def game_loop(console: GameConsole, fighter: Fighter, pool: FighterPool) -> None:
    if not bool(getattr(console, "color_forced_off", False)) and getattr(fighter, "ui_color", None) is not None:
        console.color = bool(fighter.ui_color)
    if int(getattr(fighter, "week", 1) or 1) <= 1 and not (getattr(fighter, "fight_history", None) or []):
        console.header("CAREER START")
        console.print("  Welcome, %s." % fighter.name)
        console.print("  ? opens the controls at any weekly screen.", style="dim")
        console.pause(0.3)

    presented_week = None
    while True:
        booked = getattr(fighter, "booked_fight", None)
        if isinstance(booked, dict) and booked.get("date_week") and fighter.week >= int(booked.get("date_week") or 0):
            from .systems15 import can_compete
            why = can_compete(fighter)
            if why:
                console.warn("Fight week pulled: %s" % why)
                fighter.booked_fight = None
                console.pause(0.8)
            else:
                console.gold("FIGHT WEEK.")
                fights.booker_night(console, fighter, pool)

        if fighter.health < 12:
            console.warn("Health is low. Rest before you book a fight.")

        if fighter.is_game_over():
            game_over(console, fighter)
            return

        y = ((max(1, fighter.week) - 1) // 52) + 1
        w = ((max(1, fighter.week) - 1) % 52) + 1
        console.header(f"Year {y} · Week {w}", f"Career week {fighter.week} · v{C.GAME_VERSION}")
        render_dashboard(console, fighter)
        # Weekly notifications and manager logic run once per calendar week, not
        # every time the player backs out of a browse-only submenu.
        if presented_week != int(getattr(fighter, "week", 0) or 0):
            story.show_weekly_news(console, pool, fighter)
            try:
                from . import ai
                note = ai.tick_manager(fighter)
                if note and (fighter.manager_id or fighter.manager):
                    console.info(note)
            except Exception:
                pass
            presented_week = int(getattr(fighter, "week", 0) or 0)

        if fighter.fight_cooldown > 0:
            console.warn(f"  ⏳ FIGHT RECOVERY — {fighter.fight_cooldown} week(s) remaining")
        if getattr(fighter, "suspension_weeks", 0) > 0:
            console.warn(f"  🚫 SUSPENSION — {fighter.suspension_weeks} week(s) remaining")

        try:
            from . import ux
            ux.tutorial_hint(console, fighter)
        except Exception:
            pass
        rows = _actions_for(fighter)
        week_rows = [r for r in rows if r[0] in ("A", "B", "C", "D", "N", "T", "E", "G")]
        info_rows = [r for r in rows if r[0] in ("H", "I", "L", "O", "Z", "J", "P")]
        console.section("ACTIONS")
        console.menu_table(week_rows)
        console.section("CAREER")
        console.menu_table(info_rows)
        console.print("  ? Help   K Retire", style="dim")
        choice = console.ask("\n  Action > ").strip().upper()
        if choice in ("?", "HELP"):
            from . import ux
            ux.contextual_help(console, fighter)
            continue
        if choice in ("*", "DEBUG"):
            raw = console.ask("debug (* boost / B balance / D diag) > ").strip().upper()
            if raw in ("B", "BALANCE"):
                from . import balance
                console.print(balance.report(180))
                console.pause(1.0)
            elif raw in ("D", "DIAG"):
                from . import diagnostics
                diagnostics.self_check()
            else:
                _debug_boost(fighter, console)
            continue
        if choice == "Z":
            from . import timeline
            timeline.render(console, fighter)
            continue

        # A submenu must explicitly prove that it changed career state before
        # a week is spent.  This prevents Back, Save, Stats and invalid input
        # from rolling events repeatedly in the same calendar week.
        before_week = _week_snapshot(fighter)
        fighter.week_kind = "none"
        if _dispatch_action(console, fighter, pool, choice):
            return  # player chose to retire

        kind = getattr(fighter, "week_kind", "none") or "none"
        acted = kind in ("half", "full")
        try:
            from . import ux
            ux.observe_tutorial_choice(fighter, choice, acted=acted)
        except Exception:
            pass
        if kind == "half":
            _half_week_followup(console, fighter)
            fighter.week_kind = "full"
        if acted:
            completed_week = int(getattr(fighter, "week", 0) or 0)
            fighter.advance_week(console)
            fighter.week_kind = "full"
            story.tick_relationships(fighter)
            fights.check_competition_week(console, fighter, pool)
            if hasattr(pool, "attach_player"):
                pool.attach_player(fighter)
            pool.simulate_week()
            try:
                persistence.autosave(fighter, pool)
            except Exception as e:
                diagnostics.log_error("autosave", e)
            if not fighter.is_game_over():
                # Weekly content belongs to the week that was actually spent.
                story.ensure_story_fields(fighter)
                had_story = story.weekly_story(console, fighter, pool)
                if not had_story:
                    event = events.generate_random_event(fighter)
                    if event:
                        events.handle_event(console, fighter, event)
            # One deliberate boundary between weeks. Summarize material state
            # changes before the player crosses into the next decision screen.
            if not fighter.is_game_over():
                if bool(getattr(fighter, "ui_week_report", True)):
                    _render_week_report(console, fighter, before_week)
                getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(0.1))(
                    "Week %s complete — press Enter to begin Week %s" % (completed_week, fighter.week))


def _half_week_followup(console: GameConsole, fighter: Fighter) -> None:
    console.print("Half week left: A light train  B rest  U school  X done")
    ch = console.ask("Extra > ").strip().upper()
    if ch == "A":
        fighter.energy = max(0, fighter.energy - 8)
        fighter.striking = min(100, fighter.striking + 1)
        console.good("Light pads.")
    elif ch == "B":
        fighter.energy = min(100, fighter.energy + 16)
        fighter.health = min(100, fighter.health + 4)
        console.good("Extra rest.")
    elif ch == "U":
        try:
            from .education import ensure
            ensure(fighter)
            if fighter.education_stage == "secondary":
                fighter.school_grade = min(100, fighter.school_grade + 2)
                fighter.school_attendance = min(100, fighter.school_attendance + 1)
                fighter.energy = max(0, fighter.energy - 4)
                console.good("Crammed.")
            elif fighter.education_stage == "university":
                fighter.university_average = min(100, fighter.university_average + 2)
                fighter.energy = max(0, fighter.energy - 4)
                console.good("Crammed.")
        except Exception:
            pass
    fighter.week_kind = "full"


def _dispatch_action(console: GameConsole, fighter: Fighter, pool: FighterPool, choice: str) -> bool:
    """Runs the chosen action. Returns True if the player retired (career over)."""
    if choice == "A":
        if fighter.energy < 25:
            console.warn("Energy is low. Heavy train will hurt.")
            if console.ask("Still train? A yes / B rest instead: ").strip().upper() != "A":
                career.rest_week(console, fighter)
                fighter.week_kind = "full"
                return False
        if career.do_training(console, fighter):
            fighter.week_kind = "full"
    elif choice == "B":
        career.rest_week(console, fighter)
        fighter.week_kind = "full"
    elif choice == "C":
        # One route to booking. The suspension / cooldown / booked / amateur
        # vs pro branching all lives in matchroom.book() now, so it cannot
        # drift between this screen and the manager menu.
        from . import matchroom
        from . import amateur_sports
        amateur_sports.ensure(fighter)
        before = repr(fighter.to_dict())
        if not fighter.pro_debut and not matchroom.booked_status(fighter):
            console.info("Open Amateur to book or enter amateur fights.")
        elif fighter.pro_debut and not matchroom.booked_status(fighter):
            ok, why = matchroom.gate(fighter)
            if not ok:
                console.warn(why)
                console.pause(1)
            else:
                career.manager_menu(console, fighter, pool)
        else:
            matchroom.book(console, fighter, pool)
        if repr(fighter.to_dict()) != before:
            fighter.week_kind = "full"
    elif choice == "D":
        if not fighter.pro_debut:
            before_hist = len(getattr(fighter, "fight_history", None) or [])
            was_pro = bool(getattr(fighter, "pro_debut", False))
            _amateur_hub(console, fighter, pool)
            # Only an actually contested bout or the turn-pro action spends time.
            if len(getattr(fighter, "fight_history", None) or []) > before_hist or bool(fighter.pro_debut) != was_pro:
                fighter.week_kind = "full"
    elif choice == "T":
        _coach_hub(console, fighter)
    elif choice == "M":
        # legacy key — same as amateur hub competitions
        if not fighter.pro_debut:
            before = repr(fighter.to_dict())
            from . import amateur_sports
            amateur_sports.ensure(fighter)
            if fighter.active_amateur_sport == "MMA":
                fights.competition_menu(console, fighter, pool)
            else:
                amateur_sports.championship(console, fighter, pool)
            if repr(fighter.to_dict()) != before:
                fighter.week_kind = "full"
    elif choice == "E":
        career.lifestyle_menu(console, fighter, pool)
    elif choice == "R":
        if story.relationship_menu(console, fighter):
            fighter.week_kind = "half"
    elif choice == "G":
        from . import v08
        was_pro = bool(fighter.pro_debut)
        if v08.turn_pro_ready(fighter) and not fighter.pro_debut:
            if int(getattr(fighter, "suspension_weeks", 0) or 0) > 0:
                console.warn("Cannot turn pro while suspended.")
            elif v08.turn_pro_on_cooldown(fighter):
                console.warn("Turn-pro on a short cooldown.")
            else:
                fights.turn_pro(console, fighter)
                if fighter.pro_debut != was_pro:
                    fighter.week_kind = "full"
    elif choice == "H":
        career.view_career_stats(console, fighter)
    elif choice == "I":
        career.view_rankings(console, pool, fighter)
    elif choice == "L":
        from . import ux
        ux.calendar_view(console, fighter, pool)
    elif choice == "O":
        from . import notify
        notify.inbox_menu(console, fighter)
    elif choice == "J":
        persistence.save_menu(console, fighter, pool)
    elif choice == "P":
        _career_preferences(console, fighter)
    elif choice == "N":
        before = repr(fighter.to_dict())
        career.nutrition_menu(console, fighter)
        if repr(fighter.to_dict()) != before:
            fighter.week_kind = "full"
    elif choice == "K":
        if console.ask("Retire? A yes / B no > ").strip().upper() == "A":
            game_over(console, fighter)
            return True
    else:
        console.warn("Invalid.")
        console.pause(1)
    return False


def _options_menu(console: GameConsole) -> None:
    console.header("OPTIONS", "Startup / accessibility")
    console.print("  A) Fast text")
    console.print("  B) Slower read pauses")
    console.print("  C) Toggle color (currently %s)" % ("ON" if console.color else "OFF"))
    console.print("  X) Back")
    ch = console.ask("Choice > ").strip().upper()
    if ch == "B":
        console.fast = False
        console.good("Slower pauses on.")
    elif ch == "C":
        console.color = not console.color
        console.good("Color %s." % ("on" if console.color else "off"))
    elif ch == "A":
        console.fast = True
        console.good("Fast text on.")
    console.pause(0.4)


def main() -> None:

    parser = argparse.ArgumentParser(description="From Nothing to Legend — MMA career sim")
    parser.add_argument("--width", type=int, default=50, help="console width")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
    parser.add_argument("--selfcheck", action="store_true", help="run system self-check and exit")
    args = parser.parse_args()

    if args.selfcheck:
        ok = diagnostics.self_check(verbose=True)
        raise SystemExit(0 if ok else 1)

    console = GameConsole(width=args.width, fast=True, color=(False if args.no_color else None))
    console.color_forced_off = bool(args.no_color)
    while True:
        choice = main_menu(console)
        if choice in ("1", "3"):
            if choice == "3":
                fighter = create_quick_fighter(console)
                pool = FighterPool()
                pool.generate_world(560, 360)
                pool.week = int(getattr(fighter, "week", 1) or 1)
                pool.events = []
                from . import promotion_events
                promotion_events.maintain(pool)
            else:
                fighter = create_fighter(console)
                pool = FighterPool()
                pool.generate_world(840, 560)
                # The old flow was cleaner: no forced onboarding question. Help is always one key away.
                fighter.ui_tutorial_active = False
                fighter.ui_tutorial_step = 0
                fighter.ui_tutorial_complete = True
                fighter.ui_color = bool(console.color)
                console.info("Career ready. Press ? on any weekly screen for controls.")
            try:
                game_loop(console, fighter, pool)
            except (KeyboardInterrupt, EOFError):
                raise
            except Exception as e:
                diagnostics.log_crash("game_loop", e, fighter)
                console.warn("Something went wrong. Details were saved to debug_log.txt.")
                try:
                    persistence.autosave(fighter, pool)
                    console.info("An autosave was attempted before returning to the menu.")
                except Exception:
                    pass
                console.pause(2)
        elif choice == "2":
            result = persistence.load_menu(console)
            if result:
                fighter, pool = result
                try:
                    game_loop(console, fighter, pool)
                except (KeyboardInterrupt, EOFError):
                    raise
                except Exception as e:
                    diagnostics.log_crash("game_loop (loaded career)", e, fighter)
                    console.warn("Something went wrong. Details were saved to debug_log.txt.")
                    try:
                        persistence.autosave(fighter, pool)
                    except Exception:
                        pass
                    console.pause(2)
        elif choice == "4":
            quick_tutorial(console)
        elif choice == "5":
            _options_menu(console)
        elif choice == "6":
            console.header("SYSTEM CHECK")
            results = diagnostics.run_checks()
            fails = warns = 0
            for label, status, detail in results:
                line = "%s: %s" % (label, detail)
                if status == "pass":
                    console.good(line)
                elif status == "warn":
                    warns += 1; console.info(line)
                else:
                    fails += 1; console.warn(line)
            console.print()
            if fails:
                console.warn("%d fail, %d warn" % (fails, warns))
            elif warns:
                console.info("Playable. %d warning(s), no blockers." % warns)
            else:
                console.good("ALL SYSTEMS OK")
            console.continue_prompt("Press Enter to return")
        elif choice in ("7", "X", "0"):
            console.header("GOODBYE")
            console.print("  Train hard. Fight smart.")
            break
        else:
            console.warn("Invalid.")
            console.pause(0.4)


if __name__ == "__main__":
    main()
