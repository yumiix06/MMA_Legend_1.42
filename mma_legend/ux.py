"""Player-facing career/navigation helpers for the v1.35 UI/QoL pass.

This module deliberately reads existing authoritative state instead of owning new
simulation rules.  Its job is to answer three questions quickly:
  * What matters right now?
  * Where do I go to act on it?
  * What changed / what comes next?
"""
from __future__ import annotations

from .ui import status_strip, render_fighter_stats


def _rec(values) -> str:
    r = list(values or [0, 0, 0])
    while len(r) < 3:
        r.append(0)
    return "%s-%s-%s" % (r[0], r[1], r[2])


def _opp_name(booked: dict) -> str:
    if not isinstance(booked, dict):
        return ""
    opp = booked.get("opponent")
    if opp is not None and not isinstance(opp, dict):
        return str(getattr(opp, "name", "") or "")
    snap = booked.get("opponent_snap") or booked.get("opponent_snapshot")
    if isinstance(snap, dict):
        return str(snap.get("name") or "")
    return str(booked.get("opponent_name") or "")


def next_objective(fighter) -> str:
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week"):
        left = max(0, int(booked.get("date_week") or 0) - int(getattr(fighter, "week", 0) or 0))
        who = _opp_name(booked) or str(booked.get("org") or "opponent")
        return "Fight %s in %s week%s" % (who, left, "" if left == 1 else "s")
    if getattr(fighter, "competition_signup", None):
        due = int(getattr(fighter, "competition_due_week", 0) or 0)
        left = max(0, due - int(getattr(fighter, "week", 0) or 0)) if due else 0
        return "%s%s" % (fighter.competition_signup, (" in %sw" % left) if due else "")
    if not bool(getattr(fighter, "pro_debut", False)):
        try:
            from . import v08
            if v08.turn_pro_ready(fighter):
                return "Choose whether to turn professional or keep building the amateur résumé"
        except Exception:
            pass
        return "Build the amateur résumé and qualify for championship events"
    if not getattr(fighter, "organization", None):
        return "Free agency — use Fight / Inbox or your manager to find a deal"
    return "Win, climb the %s rankings and improve your next contract" % getattr(fighter, "organization", "promotion")


def career_overview(console, fighter, pool=None) -> None:
    console.header("CAREER OVERVIEW", "One screen for where you are and what comes next")
    status_strip(console, fighter)
    phase = "PRO" if bool(getattr(fighter, "pro_debut", False)) else "AMATEUR"
    console.panel("NOW", [
        "%s · age %s · %s" % (getattr(fighter, "name", "Fighter"), getattr(fighter, "age", "?"), phase),
        "Pro %s · Amateur %s" % (_rec(getattr(fighter, "pro_record", None)), _rec(getattr(fighter, "amateur_record", None))),
        "Organization: %s" % (getattr(fighter, "organization", None) or ("Free Agent" if phase == "PRO" else "Amateur circuit")),
        "Objective: %s" % next_objective(fighter),
    ])
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week"):
        bits = [
            "%s · %s" % (booked.get("event_name") or booked.get("org") or "Fight", booked.get("weight_class") or getattr(fighter, "fight_weight_class", "")),
            "Opponent: %s" % (_opp_name(booked) or "TBA"),
            "Fight week %s · %sw away" % (booked.get("date_week"), max(0, int(booked.get("date_week")) - int(getattr(fighter, "week", 0) or 0))),
        ]
        if booked.get("title"): bits.append("Championship bout")
        console.panel("NEXT FIGHT", bits)
    try:
        from .education import ensure as _edu_ensure
        _edu_ensure(fighter)
        if getattr(fighter, "education_stage", "") == "university" and bool(getattr(fighter, "university_exam_due", False)):
            out.append((int(getattr(fighter, "university_exam_deadline", week) or week), "EDU", "%s semester exam deadline" % (getattr(fighter, "university_degree", "University") or "University")))
    except Exception:
        pass
    deal = getattr(fighter, "org_contract", None)
    if isinstance(deal, dict):
        console.panel("CONTRACT", [
            "%s · %s fight%s remaining" % (deal.get("org") or getattr(fighter, "organization", ""), int(deal.get("fights_left", 0) or 0), "" if int(deal.get("fights_left", 0) or 0) == 1 else "s"),
            "$%s show / $%s win" % (format(int(deal.get("purse_show", 0) or 0), ","), format(int(deal.get("purse_win", 0) or 0), ",")),
        ])
    recent = list(getattr(fighter, "fight_history", None) or [])[-3:]
    if recent:
        console.section("RECENT")
        for row in reversed(recent):
            console.print("  %s vs %s · %s" % (row.get("result", "?"), row.get("opponent", "Opponent"), row.get("method", "Decision")))


def fighter_sheet(console, fighter) -> None:
    """Tabbed fighter sheet. Browsing never advances time."""
    while True:
        console.header("FIGHTER", "Attributes, techniques, body and belts")
        status_strip(console, fighter)
        console.print("  A) Overview")
        console.print("  B) Fighting attributes")
        console.print("  C) Techniques")
        console.print("  D) Physical / condition")
        console.print("  E) Belts / grading")
        console.print("  X Back   0 Home")
        ch = (console.ask("Fighter > ") or "X").strip().upper()
        if ch in ("X", "0", ""):
            return
        if ch == "A":
            console.section("PROFILE")
            console.print("  %s · %s · %scm / %.1fkg" % (
                getattr(fighter, "country", ""), getattr(fighter, "stance", "Orthodox"),
                int(getattr(fighter, "height", 0) or 0), float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 0)) or 0)))
            console.print("  %s · natural %s" % (getattr(fighter, "weight_class", ""), getattr(fighter, "natural_weight_class", "")))
            console.print("  Fame %s · Reputation %s · Legacy %s" % (getattr(fighter, "fame", 0), getattr(fighter, "reputation", 0), getattr(fighter, "legacy_score", 0)))
        elif ch == "B":
            render_fighter_stats(console, fighter, detailed=False)
        elif ch == "C":
            fighter.sync_techniques()
            console.section("TECHNIQUES")
            rows = sorted((getattr(fighter, "technique_levels", None) or {}).items(), key=lambda x: (-x[1], x[0]))
            if not rows:
                console.print("  None learned yet.")
            for name, level in rows:
                console.print("  %-24s %s/5" % (name, level))
        elif ch == "D":
            console.section("BODY")
            console.print("  Energy %s · Health %s · Nutrition %s · Mood %s" % (fighter.energy, fighter.health, fighter.nutrition, getattr(fighter, "mood", 0)))
            console.print("  Walk %.1fkg · body fat %.1f%% · cut fatigue %s" % (
                float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight),
                float(getattr(fighter, "bodyfat", 0) or 0), int(getattr(fighter, "cut_fatigue", 0) or 0)))
            dmg = dict(getattr(fighter, "damage", None) or {})
            console.print("  Damage %s · cuts %s · mileage %.1f" % (dmg.get("total", 0), dmg.get("cuts", 0), float(getattr(fighter, "mileage", 0) or 0)))
        elif ch == "E":
            console.section("BELTS")
            bjj = getattr(fighter, "bjj_belt", None)
            if bjj:
                console.print("  BJJ: %s · %s stripe%s · %s grading pts" % (str(bjj).title(), int(getattr(fighter, "bjj_stripes", 0) or 0), "" if int(getattr(fighter, "bjj_stripes", 0) or 0) == 1 else "s", int(getattr(fighter, "bjj_grade_points", 0) or 0)))
            else:
                console.print("  BJJ: ungraded")
            judo = getattr(fighter, "judo_belt", None)
            console.print("  Judo: %s · %s grading pts" % ((str(judo).title() if judo else "ungraded"), int(getattr(fighter, "judo_grade_points", 0) or 0)))
        else:
            console.warn("Invalid.")
            continue
        getattr(console, "continue_prompt", lambda *_a, **_k: None)("Press Enter to return")


def calendar_entries(fighter, pool=None) -> list[tuple[int, str, str]]:
    """Return upcoming player-relevant dates without changing world state."""
    week = int(getattr(fighter, "week", 1) or 1)
    out: list[tuple[int, str, str]] = []
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and int(booked.get("date_week", 0) or 0) >= week:
        out.append((int(booked.get("date_week")), "FIGHT", "%s vs %s" % (booked.get("event_name") or booked.get("org") or "Fight", _opp_name(booked) or "TBA")))
    due = int(getattr(fighter, "competition_due_week", 0) or 0)
    if getattr(fighter, "competition_signup", None) and due >= week:
        out.append((due, "AMATEUR", str(fighter.competition_signup)))
    if int(getattr(fighter, "intl_camp_weeks", 0) or 0) > 0:
        out.append((week + int(fighter.intl_camp_weeks), "CAMP", "International camp ends"))
    elif int(getattr(fighter, "camp_weeks_remaining", 0) or 0) > 0:
        out.append((week + int(fighter.camp_weeks_remaining), "CAMP", "Fight camp completes"))
    try:
        from .education import ensure as _edu_ensure
        _edu_ensure(fighter)
        if getattr(fighter, "education_stage", "") == "university" and bool(getattr(fighter, "university_exam_due", False)):
            out.append((int(getattr(fighter, "university_exam_deadline", week) or week), "EDU", "%s semester exam deadline" % (getattr(fighter, "university_degree", "University") or "University")))
    except Exception:
        pass
    deal = getattr(fighter, "org_contract", None)
    if isinstance(deal, dict):
        wl = int(deal.get("weeks_left", 0) or 0)
        if wl > 0:
            out.append((week + wl, "CONTRACT", "%s deal reaches calendar expiry" % (deal.get("org") or getattr(fighter, "organization", "Promotion"))))
    # Current amateur sport's next championship dates.
    if not bool(getattr(fighter, "pro_debut", False)):
        try:
            from . import amateur_sports
            for row in amateur_sports.calendar_entries(fighter, getattr(fighter, "active_amateur_sport", "MMA"), years=2)[:6]:
                rw = int(row.get("due_week", 0) or 0)
                if rw >= week:
                    state = "OPEN" if row.get("signup_open") and row.get("qualified") else "eligible" if row.get("qualified") else "locked"
                    out.append((rw, "CHAMP", "%s · %s" % (row.get("name") or row.get("level") or "Championship", state)))
        except Exception:
            pass
    # Deduplicate identical labels/weeks, then sort.
    uniq = []
    seen = set()
    for row in sorted(out, key=lambda x: (x[0], x[1], x[2])):
        key = (row[0], row[2])
        if key not in seen:
            seen.add(key); uniq.append(row)
    return uniq


def calendar_view(console, fighter, pool=None) -> None:
    console.header("CALENDAR", "Upcoming dates that affect your career")
    status_strip(console, fighter)
    rows = calendar_entries(fighter, pool)
    if not rows:
        console.print("  No fixed dates on your calendar right now.")
        console.print("  Book a fight or enter a championship to create one.")
    else:
        now = int(getattr(fighter, "week", 1) or 1)
        for when, kind, label in rows[:12]:
            left = max(0, when - now)
            console.print("  W%-4s %-9s %s  (%sw)" % (when, kind, label, left))
    getattr(console, "continue_prompt", lambda *_a, **_k: None)("Press Enter to return")


def tutorial_hint(console, fighter) -> None:
    """Legacy guided-start compatibility, now reduced to a single unobtrusive line."""
    if not bool(getattr(fighter, "ui_tutorial_active", False)):
        return
    step = int(getattr(fighter, "ui_tutorial_step", 0) or 0)
    hints = {
        0: "Tip: A trains. Only completed actions advance the week.",
        1: "Tip: D opens the amateur career. H/I/Z are browse-only career info.",
        2: "Tip: T opens Team. Backing out never spends time.",
        3: "Tip: C is always the fight route: booking, prep, then fight night.",
    }
    if step in hints:
        console.print("  💡 " + hints[step], style="dim")

def observe_tutorial_choice(fighter, choice: str, acted: bool = False) -> None:
    if not bool(getattr(fighter, "ui_tutorial_active", False)):
        return
    step = int(getattr(fighter, "ui_tutorial_step", 0) or 0)
    ch = str(choice or "").upper()
    advance = (step == 0 and ch == "A" and acted) or (step == 1 and ch == "D") or (step == 2 and ch == "T") or (step == 3 and ch == "C")
    if advance:
        fighter.ui_tutorial_step = step + 1
        if fighter.ui_tutorial_step >= 4:
            fighter.ui_tutorial_active = False
            fighter.ui_tutorial_complete = True


def contextual_help(console, fighter=None) -> None:
    console.header("QUICK CONTROLS", "Only completed activities advance the week")
    console.section("ACTIONS")
    console.print("  A Train     B Rest     D Amateur")
    console.print("  N Nutrition   T Team   E Life")
    console.print("  C Fight appears when booked or professional")
    console.section("CAREER")
    console.print("  H Fighter   I Rankings")
    console.print("  L Calendar   O Inbox")
    console.print("  Z Timeline   J Save   P Settings")
    console.print("  X Back inside menus")
    if fighter is not None:
        console.section("NEXT")
        console.print("  " + next_objective(fighter))
    getattr(console, "continue_prompt", lambda *_a, **_k: None)("Press Enter to return")

