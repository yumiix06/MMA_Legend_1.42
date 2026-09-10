"""v1.40 education system: secondary school and university foundation."""
from __future__ import annotations

import random

DEGREES = {
    "Sports Science": {"tuition": 60, "benefit": "Training plans become slightly more efficient after graduation."},
    "Physiotherapy": {"tuition": 75, "benefit": "Better recovery knowledge and cheaper rehab after graduation."},
    "Business": {"tuition": 60, "benefit": "Improves sponsor/business income after graduation."},
    "Economics": {"tuition": 55, "benefit": "Improves work/financial efficiency after graduation."},
    "Law": {"tuition": 70, "benefit": "Improves contract leverage after graduation."},
    "Psychology": {"tuition": 60, "benefit": "Improves mental recovery after graduation."},
    "Nutrition": {"tuition": 60, "benefit": "Improves diet adherence and recovery after graduation."},
}

SPORT_SCHOLARSHIP_SPORTS = {"Wrestling", "Judo", "Boxing", "Combat Sambo", "Kickboxing", "MMA", "BJJ / No-Gi"}


def ensure(fighter) -> None:
    stage = str(getattr(fighter, "education_stage", "") or "")
    if stage not in ("secondary", "gap", "university", "degree", "none"):
        legacy = str(getattr(fighter, "school_status", "school") or "school")
        stage = "secondary" if legacy == "school" else ("university" if legacy == "uni" else ("degree" if legacy == "graduated" else "none"))
        fighter.education_stage = stage
    fighter.school_attendance = max(0, min(100, int(getattr(fighter, "school_attendance", 82) or 82)))
    fighter.school_grade = max(0, min(100, int(getattr(fighter, "school_grade", 72) or 72)))
    fighter.secondary_completed = bool(getattr(fighter, "secondary_completed", stage in ("gap", "university", "degree")))
    fighter.university_degree = getattr(fighter, "university_degree", None)
    fighter.university_semester = max(0, int(getattr(fighter, "university_semester", 0) or 0))
    fighter.university_semester_weeks = max(0, int(getattr(fighter, "university_semester_weeks", 0) or 0))
    fighter.university_credits = max(0, int(getattr(fighter, "university_credits", 0) or 0))
    fighter.university_average = max(0, min(100, int(getattr(fighter, "university_average", fighter.school_grade) or fighter.school_grade)))
    fighter.university_attendance = max(0, min(100, int(getattr(fighter, "university_attendance", 82) or 82)))
    fighter.university_scholarship = max(0, min(100, int(getattr(fighter, "university_scholarship", 0) or 0)))
    fighter.university_exam_due = bool(getattr(fighter, "university_exam_due", False))
    fighter.university_exam_deadline = max(0, int(getattr(fighter, "university_exam_deadline", 0) or 0))
    fighter.academic_probation = bool(getattr(fighter, "academic_probation", False))
    fighter.university_team = getattr(fighter, "university_team", None)
    if not isinstance(getattr(fighter, "education_history", None), list):
        fighter.education_history = []
    _sync_legacy(fighter)


def _sync_legacy(fighter) -> None:
    stage = str(getattr(fighter, "education_stage", "none") or "none")
    fighter.school_status = {"secondary": "school", "university": "uni", "degree": "graduated"}.get(stage, "none")
    fighter.story_flags = getattr(fighter, "story_flags", None) or {}
    fighter.story_flags["graduated"] = bool(getattr(fighter, "secondary_completed", False))


def _log(fighter, detail: str) -> None:
    ensure(fighter)
    fighter.education_history.append({"week": int(getattr(fighter, "week", 0) or 0), "detail": detail})
    fighter.education_history = fighter.education_history[-40:]


def is_enrolled(fighter) -> bool:
    ensure(fighter)
    return fighter.education_stage in ("secondary", "university")


def tuition_per_week(fighter) -> int:
    ensure(fighter)
    if fighter.education_stage != "university" or not fighter.university_degree:
        return 0
    base = int(DEGREES.get(fighter.university_degree, {}).get("tuition", 60) or 60)
    return max(0, int(round(base * (1.0 - fighter.university_scholarship / 100.0))))


def scholarship_offer(fighter) -> int:
    ensure(fighter)
    pct = 0
    grade = int(getattr(fighter, "school_grade", 70) or 70)
    if grade >= 90:
        pct = max(pct, 50)
    elif grade >= 82:
        pct = max(pct, 25)
    medals = getattr(fighter, "medals", None) or {}
    nat = medals.get("national", {}) if isinstance(medals, dict) else {}
    active = str(getattr(fighter, "active_amateur_sport", "MMA") or "MMA")
    athlete = bool(getattr(fighter, "national_team", False)) or int(nat.get("gold", 0) or 0) > 0 or int(nat.get("silver", 0) or 0) > 0
    if athlete and active in SPORT_SCHOLARSHIP_SPORTS:
        pct = max(pct, 50 if getattr(fighter, "national_team", False) else 35)
    return min(75, pct)


def can_apply(fighter) -> tuple[bool, str]:
    ensure(fighter)
    if int(getattr(fighter, "age", 16) or 16) < 18:
        return False, "University applications open at age 18."
    if not fighter.secondary_completed:
        return False, "Finish secondary school first."
    if fighter.education_stage == "university":
        return False, "Already enrolled."
    if fighter.education_stage == "degree":
        return False, "Degree already completed."
    return True, ""


def enroll(fighter, degree: str) -> str:
    ok, why = can_apply(fighter)
    if not ok:
        return why
    if degree not in DEGREES:
        return "Unknown degree."
    fighter.education_stage = "university"
    fighter.university_degree = degree
    fighter.university_semester = 1
    fighter.university_semester_weeks = 0
    fighter.university_credits = 0
    fighter.university_average = max(55, int(getattr(fighter, "school_grade", 72) or 72))
    fighter.university_attendance = 85
    fighter.university_scholarship = scholarship_offer(fighter)
    fighter.university_exam_due = False
    fighter.university_exam_deadline = 0
    fighter.academic_probation = False
    active = str(getattr(fighter, "active_amateur_sport", "MMA") or "MMA")
    if fighter.university_scholarship >= 35 and active in SPORT_SCHOLARSHIP_SPORTS:
        fighter.university_team = active
    _sync_legacy(fighter)
    _log(fighter, "Enrolled in %s (%s%% scholarship)" % (degree, fighter.university_scholarship))
    return "Enrolled in %s. Scholarship: %s%%." % (degree, fighter.university_scholarship)


def pause_university(fighter) -> str:
    ensure(fighter)
    if fighter.education_stage != "university":
        return "Not currently enrolled at university."
    fighter.education_stage = "gap"
    _sync_legacy(fighter)
    _log(fighter, "Paused university")
    return "University paused. Credits are preserved."


def resume_university(fighter) -> str:
    ensure(fighter)
    if fighter.education_stage != "gap" or not fighter.university_degree or fighter.university_credits <= 0:
        return "No paused university course to resume."
    fighter.education_stage = "university"
    _sync_legacy(fighter)
    _log(fighter, "Resumed university")
    return "University resumed."


def drop_out(fighter) -> str:
    ensure(fighter)
    if fighter.education_stage == "secondary":
        fighter.education_stage = "none"
        fighter.secondary_completed = False
        _sync_legacy(fighter)
        _log(fighter, "Left secondary school")
        return "You left secondary school. University remains locked unless you later finish it."
    if fighter.education_stage == "university":
        fighter.education_stage = "gap"
        fighter.university_degree = None
        fighter.university_credits = 0
        fighter.university_semester = 0
        fighter.university_team = None
        _sync_legacy(fighter)
        _log(fighter, "Dropped out of university")
        return "You dropped out. The degree progress is gone."
    return "No active course to leave."


def _graduate_secondary(fighter, console=None) -> bool:
    if int(getattr(fighter, "age", 16) or 16) < 18:
        return False
    if fighter.school_grade < 50 or fighter.school_attendance < 55:
        return False
    fighter.secondary_completed = True
    fighter.education_stage = "gap"
    _sync_legacy(fighter)
    _log(fighter, "Graduated secondary school")
    if console:
        console.good("Secondary school completed. University applications are now available.")
    return True


def take_exam(fighter, console=None) -> bool:
    ensure(fighter)
    if fighter.education_stage != "university" or not fighter.university_exam_due:
        return False
    preparation = fighter.university_average * 0.55 + fighter.university_attendance * 0.30 + int(getattr(fighter, "discipline", 50) or 50) * 0.15
    score = int(max(0, min(100, preparation + random.randint(-10, 10))))
    fighter.university_average = max(0, min(100, int(round((fighter.university_average * 2 + score) / 3))))
    fighter.university_exam_due = False
    fighter.university_exam_deadline = 0
    if score >= 50:
        gained = 30
        fighter.university_credits = min(240, fighter.university_credits + gained)
        fighter.academic_probation = False
        if fighter.university_credits >= 240:
            fighter.education_stage = "degree"
            fighter.university_semester = 8
            _sync_legacy(fighter)
            _log(fighter, "Graduated university: %s" % fighter.university_degree)
            if console:
                console.good("Degree completed: %s." % fighter.university_degree)
            return True
        fighter.university_semester = min(8, fighter.university_semester + 1)
        fighter.university_semester_weeks = 0
        _log(fighter, "Passed semester exam (%s)" % score)
        if console:
            console.good("Passed: %s. Credits %s/240." % (score, fighter.university_credits))
    else:
        fighter.academic_probation = True
        fighter.university_average = max(0, fighter.university_average - 4)
        fighter.university_semester_weeks = 18
        _log(fighter, "Failed semester exam (%s)" % score)
        if console:
            console.warn("Failed: %s. Academic probation." % score)
    return True


def tick(fighter, console=None) -> None:
    ensure(fighter)
    stage = fighter.education_stage
    if stage == "secondary":
        # School continues in the background. Camps/jobs can hurt attendance;
        # choosing Study/Attend in the menu can counteract it.
        busy = bool(getattr(fighter, "camp_active", False) or getattr(fighter, "intl_camp", None))
        if busy:
            fighter.school_attendance = max(0, fighter.school_attendance - 2)
            fighter.school_grade = max(0, fighter.school_grade - 1)
        else:
            fighter.school_attendance = min(100, fighter.school_attendance + random.choice([0, 1]))
            fighter.school_grade = max(0, min(100, fighter.school_grade + random.choice([-1, 0, 0, 1])))
        if fighter.week % 16 == 0:
            fighter.story_flags = getattr(fighter, "story_flags", None) or {}
            fighter.story_flags["exam_week"] = True
            if console:
                console.warn("School exam period is coming.")
        if int(getattr(fighter, "age", 16) or 16) >= 18:
            if not _graduate_secondary(fighter, console) and fighter.week % 8 == 0 and console:
                console.warn("Graduation delayed: need grade 50+ and attendance 55+.")
        return

    if stage != "university":
        return
    # Tuition is a real weekly cost, but minors can never be university students
    # in the clean v1.40 career flow.
    tuition = tuition_per_week(fighter)
    fighter.money = int(getattr(fighter, "money", 0) or 0) - tuition
    busy = bool(getattr(fighter, "camp_active", False) or getattr(fighter, "intl_camp", None))
    if busy:
        fighter.university_attendance = max(0, fighter.university_attendance - 2)
        fighter.university_average = max(0, fighter.university_average - 1)
    else:
        fighter.university_attendance = min(100, fighter.university_attendance + random.choice([0, 0, 1]))
        fighter.university_average = max(0, min(100, fighter.university_average + random.choice([-1, 0, 0, 1])))

    # Each semester spans roughly half a year of actual enrolled time. Pausing
    # freezes this counter, so a gap year never causes an instant exam on return.
    fighter.university_semester_weeks += 1
    if not fighter.university_exam_due and fighter.university_semester_weeks >= 26:
        fighter.university_exam_due = True
        fighter.university_exam_deadline = int(getattr(fighter, "week", 0) or 0) + 4
        if console:
            console.warn("University semester exam is available — 4 weeks to sit it.")
    if fighter.university_exam_due and int(getattr(fighter, "week", 0) or 0) > fighter.university_exam_deadline:
        fighter.university_exam_due = False
        fighter.academic_probation = True
        fighter.university_average = max(0, fighter.university_average - 8)
        fighter.university_attendance = max(0, fighter.university_attendance - 8)
        fighter.university_semester_weeks = 18
        _log(fighter, "Missed semester exam")
        if console:
            console.warn("Missed university exam. Academic probation; semester delayed.")


def degree_benefit(fighter, key: str, default=1.0):
    ensure(fighter)
    if fighter.education_stage != "degree":
        return default
    d = fighter.university_degree
    table = {
        ("Sports Science", "training_mult"): 1.05,
        ("Physiotherapy", "rehab_mult"): 0.85,
        ("Business", "sponsor_mult"): 1.10,
        ("Economics", "job_mult"): 1.08,
        ("Law", "contract_mult"): 1.05,
        ("Nutrition", "nutrition_bonus"): 2,
        ("Psychology", "mental_recovery"): 1,
    }
    return table.get((d, key), default)


def status_lines(fighter) -> list[str]:
    ensure(fighter)
    if fighter.education_stage == "secondary":
        return ["Secondary school · Grade %s · Attendance %s%%" % (fighter.school_grade, fighter.school_attendance)]
    if fighter.education_stage == "gap":
        if fighter.university_degree and fighter.university_credits:
            return ["Education paused · %s · %s/240 credits" % (fighter.university_degree, fighter.university_credits)]
        return ["Secondary complete · University available"] if fighter.secondary_completed else ["Not enrolled"]
    if fighter.education_stage == "university":
        year = min(4, (max(1, fighter.university_semester) + 1) // 2)
        row = "University · %s · Year %s · %s/240 credits" % (fighter.university_degree, year, fighter.university_credits)
        if fighter.university_scholarship:
            row += " · %s%% scholarship" % fighter.university_scholarship
        return [row, "Average %s · Attendance %s%% · Tuition $%s/w" % (fighter.university_average, fighter.university_attendance, tuition_per_week(fighter))]
    if fighter.education_stage == "degree":
        return ["Degree · %s" % (fighter.university_degree or "Completed")]
    return ["Not enrolled"]


def menu(console, fighter) -> bool:
    """Education menu. Returns True only when a half-week action is completed."""
    ensure(fighter)
    while True:
        console.header("EDUCATION")
        for line in status_lines(fighter):
            console.print("  " + line)
        stage = fighter.education_stage
        if stage == "secondary":
            console.print("  A) Study                 (HALF WEEK)")
            console.print("  B) Attend extra classes  (HALF WEEK)")
            console.print("  C) Skip for training     (HALF WEEK)")
            console.print("  D) Leave school")
            console.print("  X) Back")
            ch = (console.ask("Education > ") or "X").strip().upper()
            if ch in ("X", "0", ""):
                return False
            if ch == "A":
                fighter.school_grade = min(100, fighter.school_grade + 4)
                fighter.school_attendance = min(100, fighter.school_attendance + 1)
                fighter.energy = max(0, fighter.energy - 8)
                fighter.week_kind = "half"
                console.good("Study session complete.")
                return True
            if ch == "B":
                fighter.school_grade = min(100, fighter.school_grade + 2)
                fighter.school_attendance = min(100, fighter.school_attendance + 5)
                fighter.energy = max(0, fighter.energy - 6)
                fighter.week_kind = "half"
                console.good("Attendance improved.")
                return True
            if ch == "C":
                fighter.school_grade = max(0, fighter.school_grade - 3)
                fighter.school_attendance = max(0, fighter.school_attendance - 6)
                fighter.energy = min(100, fighter.energy + 4)
                fighter.week_kind = "half"
                console.warn("You skipped class for training time.")
                return True
            if ch == "D":
                if (console.ask("Leave secondary school? A yes / X cancel > ") or "X").strip().upper() == "A":
                    console.warn(drop_out(fighter))
                continue
            console.warn("Invalid.")
            continue

        if stage in ("gap", "none"):
            if fighter.university_degree and fighter.university_credits:
                console.print("  A) Resume university")
            elif fighter.secondary_completed:
                console.print("  A) Apply to university")
            else:
                console.print("  University locked — secondary school not completed.")
            console.print("  X) Back")
            ch = (console.ask("Education > ") or "X").strip().upper()
            if ch in ("X", "0", ""):
                return False
            if ch == "A" and fighter.university_degree and fighter.university_credits:
                console.good(resume_university(fighter))
                continue
            if ch == "A" and fighter.secondary_completed:
                ok, why = can_apply(fighter)
                if not ok:
                    console.warn(why)
                    continue
                console.header("UNIVERSITY", "Choose a degree")
                names = list(DEGREES)
                for i, name in enumerate(names, 1):
                    spec = DEGREES[name]
                    console.print("  %s) %-15s $%s/w" % (i, name, spec["tuition"]))
                    console.print("     " + spec["benefit"], style="dim")
                console.print("  X) Back")
                pick = (console.ask("Degree > ") or "X").strip().upper()
                if pick == "X":
                    continue
                try:
                    degree = names[int(pick) - 1]
                except (ValueError, IndexError):
                    console.warn("Invalid.")
                    continue
                console.good(enroll(fighter, degree))
                continue
            continue

        if stage == "university":
            if fighter.university_exam_due:
                console.print("  A) Sit semester exam      (HALF WEEK)")
            else:
                console.print("  A) Study                  (HALF WEEK)")
            console.print("  B) Attend classes         (HALF WEEK)")
            if fighter.university_team:
                console.print("  C) University team practice (HALF WEEK)")
            console.print("  P) Pause studies")
            console.print("  D) Drop out")
            console.print("  X) Back")
            ch = (console.ask("University > ") or "X").strip().upper()
            if ch in ("X", "0", ""):
                return False
            if ch == "A" and fighter.university_exam_due:
                fighter.energy = max(0, fighter.energy - 10)
                take_exam(fighter, console)
                fighter.week_kind = "half"
                return True
            if ch == "A":
                fighter.university_average = min(100, fighter.university_average + 4)
                fighter.energy = max(0, fighter.energy - 8)
                fighter.week_kind = "half"
                console.good("Studied.")
                return True
            if ch == "B":
                fighter.university_attendance = min(100, fighter.university_attendance + 5)
                fighter.university_average = min(100, fighter.university_average + 2)
                fighter.energy = max(0, fighter.energy - 6)
                fighter.week_kind = "half"
                console.good("Classes attended.")
                return True
            if ch == "C" and fighter.university_team:
                fighter.energy = max(0, fighter.energy - 10)
                try:
                    from .physiology import gain_stat
                    sport = fighter.university_team
                    stat = {"Wrestling": "grappling", "Judo": "grappling", "Boxing": "striking", "Kickboxing": "kicks", "Combat Sambo": "grappling", "MMA": "fight_iq", "BJJ / No-Gi": "submissions"}.get(sport, "cardio")
                    gain_stat(fighter, stat, 1)
                except Exception:
                    pass
                fighter.week_kind = "half"
                console.good("University team session complete.")
                return True
            if ch == "P":
                console.info(pause_university(fighter))
                continue
            if ch == "D":
                if (console.ask("Drop out and lose degree progress? A yes / X cancel > ") or "X").strip().upper() == "A":
                    console.warn(drop_out(fighter))
                continue
            console.warn("Invalid.")
            continue

        if stage == "degree":
            spec = DEGREES.get(fighter.university_degree, {})
            console.print("  %s" % spec.get("benefit", "Degree completed."))
            console.print("  X) Back")
            console.ask("Education > ")
            return False
