"""Separate amateur sport careers and belt progression (v1.27).

These bouts build sport-specific records and experience. They never touch the
official amateur-MMA or professional ledgers unless the selected sport is MMA.
"""
from __future__ import annotations

import random

from .engine import (
    BoxingRuleset, KickboxingRuleset, TaekwondoRuleset, WrestlingRuleset, GrapplingRuleset,
    JudoRuleset, CombatSamboRuleset, simulate_fight,
)
from .systems17 import CATEGORIES, normalize_category, set_category


SPORT_KEYS = {
    "MMA": "mma", "BJJ / No-Gi": "bjj", "Boxing": "boxing",
    "Kickboxing": "kickboxing", "Taekwondo": "taekwondo", "Wrestling": "wrestling", "Judo": "judo",
    "Combat Sambo": "combat_sambo",
}

SPORT_INFO = {
    "BJJ / No-Gi": ("submissions", "ground_control"),
    "Boxing": ("striking", "striking_def"),
    "Kickboxing": ("kicks", "distance_management"),
    "Taekwondo": ("kicks", "speed"),
    "Wrestling": ("grappling", "takedown_def"),
    "Judo": ("grappling", "ground_control"),
    "Combat Sambo": ("grappling", "striking"),
}

SPORT_LIMITS = {
    "Boxing": (52, 57, 60, 63, 67, 71, 75, 80, 86, 92),
    "Kickboxing": (51, 54, 57, 60, 63, 67, 71, 75, 81, 86, 91),
    # WT senior World Championship men: -54/-58/-63/-68/-74/-80/-87/+87.
    "Taekwondo": (54, 58, 63, 68, 74, 80, 87),
    "Wrestling": (57, 61, 65, 70, 74, 79, 86, 92, 97, 125),
    "BJJ / No-Gi": (56, 62, 69, 77, 85, 94, 120),
    # IJF men: -60/-66/-73/-81/-90/-100/+100. FIAS 2026 Combat SAMBO
    # men: -58/-64/-71/-79/-88/-98/+98. The final item is the open-class
    # threshold; weight_label() renders athletes above it as +class.
    "Judo": (60, 66, 73, 81, 90, 100),
    "Combat Sambo": (58, 64, 71, 79, 88, 98),
}

BJJ_BELTS = ("white", "blue", "purple", "brown", "black")
BJJ_REQUIREMENTS = {
    # Faster than 1.30, but still requires sustained mat time plus grading.
    "white": (0, 0), "blue": (60, 14), "purple": (165, 38),
    "brown": (300, 68), "black": (500, 110),
}
JUDO_BELTS = ("white", "yellow", "orange", "green", "blue", "brown", "black")
TKD_BELTS = ("white", "yellow", "green", "blue", "red", "black")
JUDO_REQUIREMENTS = {
    "white": (0, 0), "yellow": (24, 5), "orange": (55, 11),
    "green": (100, 20), "blue": (165, 32), "brown": (265, 52),
    "black": (430, 82),
}
TKD_REQUIREMENTS = {
    "white": (0, 0), "yellow": (22, 5), "green": (55, 11),
    "blue": (105, 20), "red": (180, 34), "black": (300, 58),
}

CHAMPIONSHIP_WEEKS = {
    "regional": (6, 34),
    "national": (12, 38),
    "continental": (22,),
    "world": (30,),
    "olympic": (40,),
}
CHAMPIONSHIP_XP = {"regional": 0, "national": 60, "continental": 140,
                   "world": 260, "olympic": 360}
OLYMPIC_SPORTS = {"Boxing", "Taekwondo", "Wrestling", "Judo"}

# Large/deep federation countries can sustain genuine sub-national qualifiers.
# Smaller countries go straight to Nationals instead of inventing a fake
# "Regional Open" inside a tiny domestic scene.
REGIONAL_COUNTRIES = {
    "USA", "Canada", "Mexico", "Brazil", "Argentina", "Russia", "China",
    "India", "Kazakhstan", "Indonesia", "Australia", "South Africa",
    "Nigeria", "UK", "France", "Germany", "Spain", "Italy", "Turkey",
}

CONTINENTAL_NAMES = {
    "Europe": "European Championships",
    "North America": "Pan-American Championships",
    "South America": "Pan-American Championships",
    "Asia": "Asian Championships",
    "Africa": "African Championships",
    "Oceania": "Oceania Championships",
}

LEVEL_NAMES = {
    "regional": "Regional Open", "national": "National Championships",
    "world": "World Championships", "olympic": "Olympic Games",
}

def continental_name(country: str) -> str:
    from .systems15 import continent
    return CONTINENTAL_NAMES.get(continent(str(country or "")), "Continental Championships")

def has_regionals(country: str) -> bool:
    return str(country or "") in REGIONAL_COUNTRIES

def level_name(fighter, level: str) -> str:
    if level == "continental":
        return continental_name(getattr(fighter, "country", ""))
    return LEVEL_NAMES.get(level, str(level).replace("_", " ").title())

def _medal_table() -> dict:
    return {level: {"gold": 0, "silver": 0, "bronze": 0}
            for level in ("regional", "national", "continental", "world", "olympic")}


def key_for(name: str) -> str:
    return SPORT_KEYS[normalize_category(name)]


def ensure(fighter) -> None:
    fighter.sport_records = dict(getattr(fighter, "sport_records", None) or {})
    fighter.sport_medals = dict(getattr(fighter, "sport_medals", None) or {})
    fighter.sport_championships = dict(getattr(fighter, "sport_championships", None) or {})
    fighter.sport_national_teams = dict(getattr(fighter, "sport_national_teams", None) or {})
    fighter.sport_experience = dict(getattr(fighter, "sport_experience", None) or {})
    if "mma" not in fighter.sport_records:
        fighter.sport_records["mma"] = list(getattr(fighter, "amateur_record", None) or [0, 0, 0])
    for key in SPORT_KEYS.values():
        fighter.sport_records.setdefault(key, [0, 0, 0])
        fighter.sport_medals.setdefault(key, {"gold": 0, "silver": 0, "bronze": 0})
        levels = fighter.sport_championships.setdefault(key, _medal_table())
        # v1.30: continental medals replace the Europe-only table. Migrate old
        # European medals only for genuinely European athletes.
        legacy_euro = levels.get("european") if isinstance(levels, dict) else None
        for level, medals in _medal_table().items():
            levels.setdefault(level, dict(medals))
            for colour in medals:
                levels[level].setdefault(colour, 0)
        if isinstance(legacy_euro, dict):
            try:
                from .systems15 import continent as _continent
                if _continent(getattr(fighter, "country", "")) == "Europe":
                    for colour in ("gold", "silver", "bronze"):
                        levels["continental"][colour] = max(
                            int(levels["continental"].get(colour, 0) or 0),
                            int(legacy_euro.get(colour, 0) or 0))
            except Exception:
                pass
            levels.pop("european", None)
        fighter.sport_national_teams.setdefault(key, False)
        # Legacy 1.27-1.30 saves could contain a National silver/gold without
        # the sport-specific team flag. Medal evidence is authoritative: it
        # means the federation already selected the athlete at Nationals.
        national = levels.get("national", {}) if isinstance(levels, dict) else {}
        if int(national.get("gold", 0) or 0) + int(national.get("silver", 0) or 0) > 0:
            fighter.sport_national_teams[key] = True
        fighter.sport_experience.setdefault(key, 0)
    # MMA's older single national-team flag remains the source used by its
    # mature tournament/calendar systems. The sport table mirrors it.
    fighter.sport_national_teams["mma"] = bool(getattr(fighter, "national_team", False))
    # 1.30 stored Combat Sambo results through the MMA judge-card label path.
    # Preserve W/L and opponent history, but repair the impossible method text.
    for row in list(getattr(fighter, "fight_history", None) or []):
        sport_key = str(row.get("sport") or row.get("ruleset") or "").lower()
        if sport_key == "combat_sambo" and "decision" in str(row.get("method") or "").lower():
            row["method"] = "Technical Points"
            row["method_migrated_v131"] = True
    active = normalize_category(getattr(fighter, "active_amateur_sport", None) or
                                (getattr(fighter, "story_flags", None) or {}).get("compete_in"))
    set_category(fighter, active)
    if fighter.bjj_belt:
        fighter.bjj_belt = str(fighter.bjj_belt).lower()
    if fighter.judo_belt:
        fighter.judo_belt = str(fighter.judo_belt).lower()


def rules_for(name: str):
    name = normalize_category(name)
    return {
        "BJJ / No-Gi": GrapplingRuleset,
        "Boxing": BoxingRuleset,
        "Kickboxing": KickboxingRuleset,
        "Taekwondo": TaekwondoRuleset,
        "Wrestling": WrestlingRuleset,
        "Judo": JudoRuleset,
        "Combat Sambo": CombatSamboRuleset,
    }.get(name, GrapplingRuleset)()


def weight_label(name: str, kg: float) -> str:
    name = normalize_category(name)
    limits = SPORT_LIMITS.get(name)
    if not limits:
        return "MMA class"
    for limit in limits:
        if float(kg) <= limit:
            return "-%skg" % limit
    if name in {"Judo", "Combat Sambo", "BJJ / No-Gi", "Taekwondo"}:
        return "+%skg" % limits[-1]
    return "-%skg" % limits[-1]


def recent_fights(fighter, sport: str | None = None, limit: int = 5) -> list[str]:
    """Player-facing, sport-filtered history; MMA and side ledgers never mix."""
    ensure(fighter)
    chosen = normalize_category(sport or fighter.active_amateur_sport)
    key = key_for(chosen)
    rows = []
    for item in reversed(list(getattr(fighter, "fight_history", None) or [])):
        if str(item.get("sport") or "mma") != key:
            continue
        rows.append("%s vs %s · %s" % (
            str(item.get("result") or "?")[:1].upper(),
            item.get("opponent") or "Opponent",
            item.get("event") or chosen,
        ))
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def _pick_fight_mode(console) -> str | None:
    console.print("  A) Play — choose the moments")
    console.print("  B) Live sim — compact automatic feed")
    console.print("  C) Instant — jump to the result")
    console.print("  X) Back / withdraw")
    raw = (console.ask("Fight mode > ") or "B").strip().upper()
    return {"A": "Full", "B": "Sim", "C": "Instant"}.get(raw)


def _clear_signup(fighter) -> None:
    fighter.competition_signup = None
    fighter.competition_week = 0
    fighter.competition_prep = False
    fighter.competition_sport = "MMA"
    fighter.competition_level = None
    fighter.competition_due_week = 0


def _qualified(fighter, sport: str, level: str) -> tuple[bool, str]:
    ensure(fighter)
    key = key_for(sport)
    xp = int(fighter.sport_experience.get(key, 0) or 0)
    tables = fighter.sport_championships[key]
    need = CHAMPIONSHIP_XP[level]
    if xp < need:
        return False, "%s XP needed; you have %s." % (need, xp)
    if level == "regional":
        if not has_regionals(getattr(fighter, "country", "")):
            return False, "Your federation has no regional stage; Nationals are the first championship level."
    if level == "continental":
        from .systems15 import continent
        region = continent(getattr(fighter, "country", "") or "")
        if region not in CONTINENTAL_NAMES:
            return False, "No continental federation route is configured for this country."
        if not fighter.sport_national_teams.get(key):
            return False, "Earn National silver or gold for this sport's team."
    if level == "world":
        if not fighter.sport_national_teams.get(key):
            return False, "National-team selection is required."
        if sum(tables["continental"].values()) < 1:
            return False, "A continental championship medal is required for Worlds."
    if level == "olympic":
        if sport not in OLYMPIC_SPORTS:
            return False, "%s has no Olympic tournament." % sport
        if not fighter.sport_national_teams.get(key):
            return False, "National-team selection is required."
        if sum(tables["world"].values()) < 1 and tables["continental"]["gold"] < 1:
            return False, "Qualify with a World medal or continental gold."
    return True, "eligible"


def calendar_entries(fighter, sport: str | None = None, years: int = 5) -> list[dict]:
    """Absolute future dates, including the next valid four-year Olympics."""
    ensure(fighter)
    chosen = normalize_category(sport or fighter.active_amateur_sport)
    now = max(1, int(getattr(fighter, "week", 1) or 1))
    current_year = ((now - 1) // 52) + 1
    entries = []
    for year in range(current_year, current_year + max(2, int(years))):
        for level, season_weeks in CHAMPIONSHIP_WEEKS.items():
            if level == "regional" and not has_regionals(getattr(fighter, "country", "")):
                continue
            if level == "olympic" and (chosen not in OLYMPIC_SPORTS or year % 4):
                continue
            for season_week in season_weeks:
                due = (year - 1) * 52 + season_week
                if due <= now:
                    continue
                ok, reason = _qualified(fighter, chosen, level)
                entries.append({
                    "sport": chosen, "level": level,
                    "name": "%s %s" % (chosen, level_name(fighter, level)),
                    "season_week": season_week, "career_year": year,
                    "due_week": due, "weeks_left": due - now,
                    "signup_open": 1 <= due - now <= 8,
                    "qualified": ok, "reason": reason,
                })
    entries.sort(key=lambda row: (row["due_week"], row["level"]))
    return entries


def _belt_index(value, belts) -> int:
    try:
        return belts.index(str(value or "white").lower())
    except ValueError:
        return 0


def _sync_stripes(fighter) -> None:
    belt = fighter.bjj_belt or "white"
    idx = _belt_index(belt, BJJ_BELTS)
    if idx >= len(BJJ_BELTS) - 1:
        fighter.bjj_stripes = 0
        return
    here = BJJ_REQUIREMENTS[belt][0]
    nxt = BJJ_REQUIREMENTS[BJJ_BELTS[idx + 1]][0]
    progress = max(0, int(getattr(fighter, "bjj_grade_points", 0) or 0) - here)
    fighter.bjj_stripes = min(4, int(progress * 5 / max(1, nxt - here)))


def train_belt(fighter, art: str, amount: int = 4) -> None:
    """Credit real mat time; promotion still requires a coach evaluation."""
    ensure(fighter)
    art = str(art or "").lower()
    if art == "bjj":
        fighter.bjj_belt = fighter.bjj_belt or "white"
        fighter.bjj_weeks = int(getattr(fighter, "bjj_weeks", 0) or 0) + 1
        fighter.bjj_grade_points = int(getattr(fighter, "bjj_grade_points", 0) or 0) + max(1, amount)
        _sync_stripes(fighter)
    elif art == "judo":
        fighter.judo_belt = fighter.judo_belt or "white"
        fighter.judo_weeks = int(getattr(fighter, "judo_weeks", 0) or 0) + 1
        fighter.judo_grade_points = int(getattr(fighter, "judo_grade_points", 0) or 0) + max(1, amount)
    elif art in ("tkd", "taekwondo"):
        fighter.tkd_belt = getattr(fighter, "tkd_belt", None) or "white"
        fighter.tkd_weeks = int(getattr(fighter, "tkd_weeks", 0) or 0) + 1
        fighter.tkd_grade_points = int(getattr(fighter, "tkd_grade_points", 0) or 0) + max(1, amount)


def _promotion_ready(fighter, art: str) -> tuple[bool, str]:
    ensure(fighter)
    raw = str(art or "").lower()
    if raw == "bjj":
        belts, req = BJJ_BELTS, BJJ_REQUIREMENTS
        current = fighter.bjj_belt or "white"; points=int(fighter.bjj_grade_points or 0); weeks=int(fighter.bjj_weeks or 0)
    elif raw.startswith("j"):
        belts, req = JUDO_BELTS, JUDO_REQUIREMENTS
        current = fighter.judo_belt or "white"; points=int(fighter.judo_grade_points or 0); weeks=int(fighter.judo_weeks or 0)
    else:
        belts, req = TKD_BELTS, TKD_REQUIREMENTS
        current = getattr(fighter, "tkd_belt", None) or "white"; points=int(getattr(fighter,"tkd_grade_points",0) or 0); weeks=int(getattr(fighter,"tkd_weeks",0) or 0)
    idx = _belt_index(current, belts)
    if idx >= len(belts)-1: return False, "Already at black belt."
    nxt=belts[idx+1]; need_points,need_weeks=req[nxt]
    if points < need_points or weeks < need_weeks:
        return False, "%s needs %s points and %s mat weeks (you: %s/%s)." % (nxt.title(),need_points,need_weeks,points,weeks)
    return True,nxt

def auto_promote_belt(fighter, art: str, console=None) -> str | None:
    """Promote automatically when sustained specialist mat time is enough.

    v1.41 makes belt progression part of belonging to a BJJ/Judo room. The
    player no longer has to remember to open a grading menu on exactly the
    right week. Requirements remain the same; only the ceremony is automatic.
    """
    raw = str(art or "").lower()
    art = "judo" if raw.startswith("j") else ("tkd" if raw in ("tkd","taekwondo") else "bjj")
    ok, value = _promotion_ready(fighter, art)
    if not ok:
        return None
    if art == "bjj":
        fighter.bjj_belt = value
        fighter.bjj_stripes = 0
    elif art == "judo":
        fighter.judo_belt = value
    else:
        fighter.tkd_belt = value
    fighter.reputation = min(100, int(getattr(fighter, "reputation", 0) or 0) + 1)
    flags = getattr(fighter, "story_flags", None) or {}
    flags["%s_%s_belt_week" % (art, value)] = int(getattr(fighter, "week", 0) or 0)
    fighter.story_flags = flags
    try:
        from .timeline import add
        add(fighter, "%s promotion: %s belt" % (art.upper(), value.title()))
    except Exception:
        pass
    if console:
        console.gold("%s promotion: %s belt." % (art.upper(), value.title()))
    return value


def evaluate_belt(console, fighter, art: str) -> bool:
    art = "judo" if str(art).lower().startswith("j") else "bjj"
    ok, value = _promotion_ready(fighter, art)
    if not ok:
        console.info(value)
        return False
    cost = 90 if art == "bjj" else 65
    if fighter.money < cost:
        console.warn("Grading fee is $%s." % cost)
        return False
    fighter.money -= cost
    if art == "bjj":
        fighter.bjj_belt = value
        fighter.bjj_stripes = 0
    else:
        fighter.judo_belt = value
    fighter.reputation = min(100, int(fighter.reputation) + 2)
    console.gold("%s promotion: %s belt." % (art.upper(), value.title()))
    return True


def belt_progress_line(fighter, art: str) -> str:
    ensure(fighter)
    raw=str(art or "").lower()
    if raw == "bjj":
        label="BJJ"; belts,req=BJJ_BELTS,BJJ_REQUIREMENTS; current=fighter.bjj_belt or "white"; points=int(fighter.bjj_grade_points); weeks=int(fighter.bjj_weeks)
    elif raw.startswith("j"):
        label="Judo"; belts,req=JUDO_BELTS,JUDO_REQUIREMENTS; current=fighter.judo_belt or "white"; points=int(fighter.judo_grade_points); weeks=int(fighter.judo_weeks)
    else:
        label="Taekwondo"; belts,req=TKD_BELTS,TKD_REQUIREMENTS; current=getattr(fighter,"tkd_belt",None) or "white"; points=int(getattr(fighter,"tkd_grade_points",0) or 0); weeks=int(getattr(fighter,"tkd_weeks",0) or 0)
    idx=_belt_index(current,belts)
    if idx >= len(belts)-1: return "%s: Black Belt" % label
    nxt=belts[idx+1]; need_points,need_weeks=req[nxt]
    pct=min(min(100,int(points*100/max(1,need_points))), min(100,int(weeks*100/max(1,need_weeks))))
    return "%s%% toward %s Belt" % (pct,nxt.title())

def belt_lines(fighter) -> list[str]:
    ensure(fighter)
    rows = []
    if fighter.bjj_belt:
        rows.append("BJJ %s belt · %s stripe%s · %s pts" % (
            fighter.bjj_belt.title(), fighter.bjj_stripes,
            "" if fighter.bjj_stripes == 1 else "s", fighter.bjj_grade_points))
    if fighter.judo_belt:
        rows.append("Judo %s belt · %s pts" % (fighter.judo_belt.title(), fighter.judo_grade_points))
    if getattr(fighter, "tkd_belt", None):
        rows.append("Taekwondo %s belt · %s pts" % (fighter.tkd_belt.title(), getattr(fighter,"tkd_grade_points",0)))
    return rows


def _opponent(fighter, pool, sport: str):
    fmass = float(getattr(fighter, "walking_weight", None) or getattr(fighter, "weight", 70) or 70)
    division = weight_label(sport, fmass)
    eligible = [x for x in getattr(pool, "fighters", [])
                if x is not fighter and getattr(x, "active", True)
                and not getattr(x, "pro_debut", False)
                and weight_label(sport, float(getattr(x, "walking_weight", None) or getattr(x, "weight", fmass) or fmass)) == division]
    specialists = [x for x in eligible
                   if normalize_category(getattr(x, "active_amateur_sport", "MMA")) == sport]
    candidates = specialists or eligible
    if not candidates:
        from .fights import generate_random_opponent
        return generate_random_opponent(fighter, country_bias=fighter.country)
    rating = sum(fighter.rating_vector()) / max(1, len(fighter.rating_vector()))
    candidates.sort(key=lambda x: abs(sum(x.rating_vector()) / max(1, len(x.rating_vector())) - rating))
    return random.choice(candidates[:min(8, len(candidates))])


def compete(console, fighter, pool, mode: str | None = None,
            event_name: str | None = None, competition_level: str | None = None) -> bool:
    """Run one side-sport bout. Returns True when the week was spent."""
    ensure(fighter)
    sport = normalize_category(fighter.active_amateur_sport)
    if sport == "MMA":
        console.info("MMA is selected. Use Local MMA bracket/fight; choose S first for another sport.")
        return False
    if fighter.energy < 24 or fighter.health < 30:
        console.warn("Need 24 energy and 30 health to compete.")
        return False
    if mode is None:
        console.header("FIGHT MODE", sport)
        mode = _pick_fight_mode(console)
        if mode is None:
            return False
    opp = _opponent(fighter, pool, sport)
    rules = rules_for(sport)
    console.header(sport.upper(), "%s · %s min · %s" % (
        weight_label(sport, float(getattr(fighter, "walking_weight", None) or fighter.weight)), rules.period_seconds // 60, rules.label_period(1)))
    console.print("%s vs %s" % (fighter.name, opp.name))
    old = fighter.fight_details
    fighter.fight_details = mode
    outcome = simulate_fight(fighter, opp, rules, console=console, interactive=True)
    fighter.fight_details = old
    result = "Win" if outcome.winner == "player" else "Loss" if outcome.winner == "opponent" else "Draw"
    method = outcome.method
    if sport == "Judo" and result != "Draw" and abs(outcome.f_stats.grappling_points - outcome.o_stats.grappling_points) >= 4:
        method = "Ippon"
    key = key_for(sport)
    row = fighter.sport_records[key]
    row[0 if result == "Win" else 1 if result == "Loss" else 2] += 1
    ensure(opp)
    opp_result = "Loss" if result == "Win" else "Win" if result == "Loss" else "Draw"
    opp_row = opp.sport_records[key]
    opp_row[0 if opp_result == "Win" else 1 if opp_result == "Loss" else 2] += 1
    xp = 10 + (6 if result == "Win" else 2)
    fighter.sport_experience[key] += xp
    fighter.energy = max(0, fighter.energy - 12)
    primary, secondary = SPORT_INFO[sport]
    if result == "Win":
        setattr(fighter, primary, min(100, int(getattr(fighter, primary)) + 1))
        fighter.reputation = min(100, int(fighter.reputation) + 2)
    elif random.random() < 0.35:
        setattr(fighter, secondary, min(100, int(getattr(fighter, secondary)) + 1))
    if sport == "BJJ / No-Gi":
        train_belt(fighter, "bjj", 9 if result == "Win" else 6)
    elif sport == "Judo":
        train_belt(fighter, "judo", 9 if result == "Win" else 6)
    elif sport == "Taekwondo":
        train_belt(fighter, "taekwondo", 9 if result == "Win" else 6)
    event = event_name or "Local %s" % sport
    fighter.fight_history.append({
        "opponent": opp.name, "result": result, "method": method,
        "opponent_id": getattr(opp, "fid", None),
        "round": int(outcome.end_period or 1), "event": event,
        "performance_rating": 0.0, "sport": key, "ruleset": rules.name,
        "sport_name": sport, "competition_level": competition_level,
        "week": int(getattr(fighter, "week", 0) or 0), "mode": mode,
        "pro": False, "stats": outcome.f_stats.as_dict(),
    })
    opp.fight_history.append({
        "opponent": fighter.name, "result": opp_result, "method": method,
        "opponent_id": getattr(fighter, "fid", None),
        "round": int(outcome.end_period or 1), "event": event,
        "performance_rating": 0.0, "sport": key, "ruleset": rules.name, "pro": False,
        "sport_name": sport, "competition_level": competition_level,
        "week": int(getattr(fighter, "week", 0) or 0), "mode": mode,
    })
    console.good("%s by %s · %s record %s-%s-%s" % (
        result.upper(), method, sport, row[0], row[1], row[2]))
    return True


def competition_calendar(console, fighter, pool) -> bool:
    """Register the active side sport for a real future event week."""
    ensure(fighter)
    sport = normalize_category(fighter.active_amateur_sport)
    if sport == "MMA":
        console.info("MMA has its own championship calendar.")
        return False
    key = key_for(sport)
    rec = fighter.sport_records[key]
    console.header("%s CALENDAR" % sport.upper(), "%s · %s-%s-%s" % (
        weight_label(sport, float(getattr(fighter, "walking_weight", None) or fighter.weight)), rec[0], rec[1], rec[2]))
    if fighter.sport_national_teams.get(key):
        console.gold("National team: selected")

    if fighter.competition_signup:
        bound = normalize_category(getattr(fighter, "competition_sport", "MMA") or "MMA")
        due = int(getattr(fighter, "competition_due_week", 0) or 0)
        left = max(0, due - int(fighter.week)) if due else 0
        console.gold("Registered: %s" % fighter.competition_signup)
        console.print("Sport: %s · event in %s week(s)" % (bound, left))
        console.print("  C) Cancel registration")
        console.print("  X) Back")
        if console.ask("Choice > ").strip().upper() == "C":
            _clear_signup(fighter)
            console.info("Registration cancelled.")
            return True
        return False

    upcoming = calendar_entries(fighter, sport)[:8]
    for i, event in enumerate(upcoming, 1):
        if event["signup_open"] and event["qualified"]:
            status = "OPEN"
        elif event["signup_open"]:
            status = "LOCKED"
        else:
            status = "opens in %sw" % max(0, event["weeks_left"] - 8)
        console.print("  %s) Y%s W%s · %s · %s" % (
            i, event["career_year"], event["season_week"],
            level_name(fighter, event["level"]), status))
    history = recent_fights(fighter, sport, 3)
    if history:
        console.section("Recent %s fights" % sport)
        for row in history:
            console.print("  " + row)
    console.print("  X) Back")
    raw = console.ask("Register > ").strip().upper()
    if raw == "X":
        return False
    try:
        event = upcoming[int(raw) - 1]
    except (ValueError, IndexError):
        console.warn("Choose a listed event.")
        return False
    if not event["signup_open"]:
        console.warn("Registration opens eight weeks before the event.")
        return False
    if not event["qualified"]:
        console.warn(event["reason"])
        return False
    fighter.competition_signup = event["name"]
    fighter.competition_week = event["season_week"]
    fighter.competition_prep = True
    fighter.competition_sport = sport
    fighter.competition_level = event["level"]
    fighter.competition_due_week = event["due_week"]
    console.good("Registered for %s in %s week(s)." % (
        event["name"], event["weeks_left"]))
    return True


def championship(console, fighter, pool, level_override: str | None = None,
                 mode: str | None = None, event_name: str | None = None) -> bool:
    """A separate domestic -> continental -> world amateur sport ladder."""
    ensure(fighter)
    sport = normalize_category(fighter.active_amateur_sport)
    if sport == "MMA":
        console.info("MMA is selected. Open the main Calendar for its two Nationals, Europe and Worlds.")
        return False
    if level_override is None:
        return competition_calendar(console, fighter, pool)
    key = key_for(sport)
    xp = int(fighter.sport_experience.get(key, 0) or 0)
    year_week = ((int(getattr(fighter, "week", 1) or 1) - 1) % 52) + 1

    def open_now(level: str) -> bool:
        if level == "regional":
            return True
        if level == "olympic":
            career_year = ((int(getattr(fighter, "week", 1) or 1) - 1) // 52) + 1
            return sport in OLYMPIC_SPORTS and career_year % 4 == 0 and abs(year_week - CHAMPIONSHIP_WEEKS["olympic"][0]) <= 1
        return any(abs(year_week - w) <= 1 for w in CHAMPIONSHIP_WEEKS[level])

    level = str(level_override).lower()
    if level not in CHAMPIONSHIP_WEEKS:
        return False
    if not open_now(level):
        console.warn("%s entries are closed this week." % level.title())
        return False
    eligible, reason = _qualified(fighter, sport, level)
    if not eligible:
        console.warn(reason)
        return False
    # _qualified() runs the migration guard, which may replace top-level
    # dictionaries. Capture the live references only after that call.
    teams = fighter.sport_national_teams
    tables = fighter.sport_championships[key]
    fee = {"regional": 25, "national": 80, "continental": 160,
           "world": 280, "olympic": 0}[level]
    energy_need = 60 if level == "olympic" else 48
    if fighter.money < fee or fighter.energy < energy_need:
        console.warn("Need $%s and %s energy." % (fee, energy_need))
        return False
    if mode is None:
        console.header("TOURNAMENT MODE", "%s · %s" % (sport, level_name(fighter, level)))
        mode = _pick_fight_mode(console)
        if mode is None:
            console.warn("Tournament withdrawn before the draw.")
            return False
    fighter.money -= fee
    start = list(fighter.sport_records[key])
    won = 0
    stages = ("Round of 16", "Quarterfinal", "Semifinal", "Final") if level == "olympic" else (
        "Quarterfinal", "Semifinal", "Final")
    for stage in stages:
        console.section(stage)
        before = list(fighter.sport_records[key])
        compete(console, fighter, pool, mode=mode,
                event_name=event_name or "%s %s" % (sport, level_name(fighter, level)),
                competition_level=level)
        after = fighter.sport_records[key]
        if after[0] > before[0]:
            won += 1
            continue
        break
    target_wins = len(stages)
    medal = ("gold" if won == target_wins else "silver" if won == target_wins - 1
             else "bronze" if won == target_wins - 2 else None)
    if medal:
        fighter.sport_medals[key][medal] += 1
        tables[level][medal] += 1
        bonus = {"gold": 20, "silver": 10, "bronze": 6}[medal] + {
            "regional": 0, "national": 8, "continental": 16, "world": 28,
            "olympic": 42}[level]
        fighter.sport_experience[key] += bonus
        fighter.legacy_score += {"gold": 3, "silver": 2, "bronze": 1}[medal] * {
            "regional": 1, "national": 2, "continental": 3, "world": 5,
            "olympic": 8}[level]
        if level == "national" and medal in ("gold", "silver") and not teams.get(key):
            teams[key] = True
            console.gold("Selected for the %s national team." % sport)
        if level in ("national", "continental", "world", "olympic") and medal == "gold":
            from .notoriety import add_fame
            add_fame(fighter, {"national": 3, "european": 5, "world": 8,
                               "olympic": 12}[level],
                     "%s %s gold" % (sport, level))
        console.gold("%s %s medal — %s." % (sport, level, medal.upper()))
    else:
        console.print("Out in the quarterfinal. Experience, no medal.")
    return fighter.sport_records[key] != start


def check_scheduled_competition(console, fighter, pool) -> bool:
    """Run a registered side-sport championship on its absolute event week."""
    if not getattr(fighter, "competition_signup", None):
        return False
    sport = normalize_category(getattr(fighter, "competition_sport", "MMA") or "MMA")
    if sport == "MMA":
        return False
    due = int(getattr(fighter, "competition_due_week", 0) or 0)
    if not due:
        season = int(getattr(fighter, "competition_week", 0) or 0)
        year = ((max(1, int(fighter.week)) - 1) // 52) + 1
        due = (year - 1) * 52 + season
        if due < int(fighter.week):
            due += 52
        fighter.competition_due_week = due
    if int(fighter.week) < due:
        if due - int(fighter.week) <= 2:
            console.info("%s in %s week(s)." % (fighter.competition_signup, due - int(fighter.week)))
        return False
    if fighter.pro_debut:
        console.warn("Professional status cancels the amateur registration.")
        _clear_signup(fighter)
        return False
    from .systems15 import can_compete
    why = can_compete(fighter)
    if why:
        console.warn("Missed %s: %s" % (fighter.competition_signup, why))
        _clear_signup(fighter)
        return False
    if normalize_category(fighter.active_amateur_sport) != sport:
        console.warn("Registration sport no longer matches your active focus.")
        _clear_signup(fighter)
        return False
    event_name = fighter.competition_signup
    level = str(getattr(fighter, "competition_level", None) or "regional")
    console.header(event_name.upper(), "Competition week")
    mode = _pick_fight_mode(console)
    if mode is None:
        console.warn("You withdrew from the tournament.")
        _clear_signup(fighter)
        return False
    try:
        return championship(console, fighter, pool, level_override=level,
                            mode=mode, event_name=event_name)
    finally:
        _clear_signup(fighter)


def choose_sport(console, fighter) -> bool:
    ensure(fighter)
    console.header("AMATEUR SPORTS", "One active competition focus")
    for i, name in enumerate(CATEGORIES, 1):
        mark = " *" if name == fighter.active_amateur_sport else ""
        key = key_for(name)
        rec = fighter.sport_records[key]
        console.print("  %s) %s%s  %s-%s-%s" % (i, name, mark, rec[0], rec[1], rec[2]))
    raw = console.ask("Sport number, letter or name > ").strip()
    try:
        if raw.upper() in "ABCDEFGH" and len(raw) == 1:
            name = CATEGORIES["ABCDEFGH".index(raw.upper())]
        elif raw.isdigit():
            name = CATEGORIES[int(raw) - 1]
        else:
            name = normalize_category(raw)
            if raw.lower() not in {x.lower() for x in CATEGORIES} and raw.lower() not in {
                    "sambo", "combat sambo", "grappling", "bjj", "no-gi", "tkd", "tae kwon do"}:
                raise ValueError
    except (ValueError, IndexError):
        console.warn("Choose 1-8, A-H, or type the sport name.")
        return False
    changed = name != fighter.active_amateur_sport
    if changed and getattr(fighter, "competition_signup", None):
        console.warn("Cancel the registered championship before changing sport.")
        return False
    set_category(fighter, name)
    if name == "BJJ / No-Gi" and not fighter.bjj_belt:
        fighter.bjj_belt = "white"
    if name == "Judo" and not fighter.judo_belt:
        fighter.judo_belt = "white"
    if name == "Taekwondo" and not getattr(fighter, "tkd_belt", None):
        fighter.tkd_belt = "white"
    console.good("Competition focus: %s." % name)
    return changed
