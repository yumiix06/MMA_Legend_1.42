"""System health checks, crash logging, and live in-playthrough validation.

Three jobs:
  1. self_check() / run_checks() — startup diagnostic.
  2. log() / log_error() / log_crash() — append-only debug_log.txt.
  3. check_outcome_live() — fight-log validator after real fights.

Nothing here changes game balance. It only watches and records.

CLI:
    python3 -m mma_legend.diagnostics
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

DEBUG = os.environ.get("FNTL_DEBUG") == "1"
LOG_PATH = Path.cwd() / "debug_log.txt"
_MAX_LOG_BYTES = 2_000_000

PASS, WARN, FAIL = "pass", "warn", "fail"


def _rotate_if_huge() -> None:
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > _MAX_LOG_BYTES:
            LOG_PATH.write_text(
                "[log rotated %s]\n" % time.strftime("%Y-%m-%d %H:%M:%S"),
                encoding="utf-8",
            )
    except Exception:
        pass


def log(msg: str) -> None:
    try:
        _rotate_if_huge()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def log_error(context: str, exc: BaseException) -> None:
    try:
        _rotate_if_huge()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write("[%s] ERROR in %s: %s\n" % (time.strftime("%H:%M:%S"), context, exc))
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass


def log_crash(context: str, exc: BaseException, fighter=None) -> None:
    state = ""
    if fighter is not None:
        try:
            state = " | week=%s name=%s record=%s energy=%s health=%s" % (
                getattr(fighter, "week", "?"),
                getattr(fighter, "name", "?"),
                getattr(fighter, "get_total_record", lambda: "?")(),
                getattr(fighter, "energy", "?"),
                getattr(fighter, "health", "?"),
            )
        except Exception:
            pass
    log_error("CRASH in %s%s" % (context, state), exc)


def check_outcome_live(outcome, console=None, context: str = "fight") -> list[str]:
    try:
        from .engine.validate import validate_fight_log
        issues = validate_fight_log(outcome)
    except Exception as e:
        log_error("%s validator crashed" % context, e)
        return []
    if issues:
        log("%s: %d fight-log issue(s): %s" % (context, len(issues), "; ".join(issues[:10])))
        if DEBUG and console is not None:
            try:
                console.warn("[debug] fight-log flagged %d issue(s) — see debug_log.txt" % len(issues))
            except Exception:
                pass
    return issues


def _check_launch() -> tuple[str, str]:
    try:
        pkg = Path(__file__).resolve().parent
        parent = pkg.parent
        has_main = (parent / "main.py").exists() or (parent / "START.py").exists()
        has_data = (pkg / "data" / "events_v08.json").exists()
        bits = [
            "package=%s" % pkg.name,
            "python %s.%s" % (sys.version_info.major, sys.version_info.minor),
            "log=%s" % LOG_PATH,
        ]
        if not has_data:
            return FAIL, "data folder missing next to diagnostics.py"
        if not has_main:
            return WARN, "ok, but main.py/START.py not next to package — tap those, not app.py. " + ", ".join(bits)
        return PASS, " | ".join(bits)
    except Exception as e:
        return FAIL, str(e)


def _check_data_files() -> tuple[str, str]:
    try:
        from . import data
        issues = data.validate_data()
        if issues:
            return FAIL, "%d content issue(s): %s" % (len(issues), "; ".join(issues[:6]))
        n_events = len(data.all_events())
        return PASS, "countries=%s opponents=%s moments=%s events=%s" % (
            len(data.COUNTRIES), len(data.OPPONENTS), len(data.COMBAT_MOMENTS), n_events,
        )
    except Exception as e:
        log_error("data check", e)
        return FAIL, "crashed: %s" % e


def _engine_is_stub() -> bool:
    try:
        from .engine import fight as _fight
        return "Playable" not in ((_fight.__doc__) or "")
    except Exception:
        return True


def _check_engine_smoke() -> tuple[str, str]:
    try:
        from .data import country_by_name
        from .models import Fighter
        from .engine import simulate_fight
        from .engine.rules import MMARuleset, GrapplingRuleset
        from .engine.validate import validate_fight_log

        c = country_by_name("USA")
        problems = []
        for ruleset, label in (
            (MMARuleset(amateur=True), "amateur mma"),
            (MMARuleset(amateur=False), "pro mma"),
            (GrapplingRuleset(), "no-gi"),
        ):
            f = Fighter.new_player("_diag_p", "B", c, "Boxing")
            o = Fighter.new_npc("_diag_o", c)
            f.energy = o.energy = 90
            out = simulate_fight(f, o, ruleset, gameplan="Balanced", console=None)
            if out.winner not in ("player", "opponent", "draw"):
                problems.append("%s: bad winner %r" % (label, out.winner))
            issues = validate_fight_log(out)
            if issues:
                problems.append("%s: %s" % (label, "; ".join(issues[:3])))
        stub = _engine_is_stub()
        if problems:
            return FAIL, "; ".join(problems)
        if stub:
            return WARN, "sims ran, but still on the old stub path"
        return PASS, "3 headless sims ran (amateur / pro / no-gi)"
    except Exception as e:
        log_error("engine smoke", e)
        return FAIL, "crashed: %s" % e


def _check_save_round_trip() -> tuple[str, str]:
    import tempfile
    try:
        from .data import country_by_name
        from .models import Fighter
        from .world import FighterPool
        from . import persistence

        class _Quiet:
            def good(self, *a, **k): pass
            def warn(self, *a, **k): pass
            def print(self, *a, **k): pass
            def pause(self, *a, **k): pass

        console = _Quiet()
        c = country_by_name("USA")
        fighter = Fighter.new_player("_diag_save", "B", c, "Boxing")
        fighter.week = 37
        pool = FighterPool()
        pool.generate_world(20, 10)

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "diag_save.json"
            ok = persistence.save_game(console, fighter, pool, path=path)
            if not ok:
                return FAIL, "save_game() returned False"
            result = persistence.load_game(console, path=path) if hasattr(persistence, "load_game") else None
            if result is None:
                return WARN, "saved ok; load_game() not directly callable"
            loaded_fighter, loaded_pool = result
            if loaded_fighter.week != 37:
                return FAIL, "round trip lost fighter.week (got %r)" % loaded_fighter.week
            if loaded_pool is None or not getattr(loaded_pool, "fighters", None):
                return WARN, "fighter loaded; pool empty after read-back"
        return PASS, "save -> load kept week + pool"
    except Exception as e:
        log_error("save round trip", e)
        return FAIL, "crashed: %s" % e


def _check_version_strings() -> tuple[str, str]:
    try:
        from . import constants as C
        from . import __version__ as pkg_version
        import inspect
        from . import app as _app
        src = inspect.getsource(_app.quick_tutorial)
        if C.GAME_VERSION not in src and "GAME_VERSION" not in src:
            return FAIL, "quick_tutorial() header doesn't reference C.GAME_VERSION"
        if pkg_version != C.GAME_VERSION:
            return FAIL, "package %s != constants %s" % (pkg_version, C.GAME_VERSION)
        return PASS, "v%s" % C.GAME_VERSION
    except Exception as e:
        log_error("version check", e)
        return FAIL, "crashed: %s" % e


def _check_people_system() -> tuple[str, str]:
    try:
        from .data import country_by_name
        from .models import Fighter
        from . import people, orgs

        f = Fighter.new_npc("_diag_people", country_by_name("USA"))
        f.pro_debut = True
        f.pro_record = [8, 1, 0]
        f.fame = 20

        cands = people.manager_candidates(f)
        if not cands:
            return FAIL, "manager_candidates() returned nothing"
        people.sign_manager(f, cands[0])
        if f.manager_id != cands[0].id or people.rapport(f, cands[0].id) != 55:
            return FAIL, "sign_manager() did not set manager_id/rapport"

        missing = [oid for oid in orgs.ORGS if not people.promoter_for(oid)]
        if missing:
            return FAIL, "no promoter for %s" % ", ".join(missing[:4])

        d = f.to_dict()
        f2 = Fighter.from_dict(d)
        if f2.manager_id != f.manager_id or f2.people_rel != f.people_rel:
            return FAIL, "manager_id/people_rel did not survive save round trip"
        return PASS, "managers + promoters + save ok"
    except Exception as e:
        log_error("people check", e)
        return FAIL, "crashed: %s" % e


def _check_booking_pipe() -> tuple[str, str]:
    try:
        from .data import country_by_name
        from .models import Fighter
        from .world import FighterPool
        from . import booking, orgs, people

        f = Fighter.new_player("_diag_book", "B", country_by_name("USA"), "Boxing")
        f.pro_debut = True
        f.pro_record = [3, 0, 0]
        f.room = "Regional"
        pool = FighterPool()
        pool.generate_world(30, 10)
        off = booking.build_offer(f, pool=pool)
        needed = ("opponent_id", "matchmaker_id", "org")
        missing = [k for k in needed if not off.get(k)]
        if missing:
            return FAIL, "offer missing %s" % ", ".join(missing)
        if orgs.eligible_orgs(f) and "ufc" in [x.lower() for x in orgs.eligible_orgs(f)] and f.room == "Local":
            return FAIL, "UFC leaked into local eligibility"
        mm = people.matchmaker_for(off.get("org") or "lfa")
        if mm is None:
            return WARN, "offer shape ok; matchmaker lookup returned None"
        return PASS, "offer org=%s opp=%s mm=%s" % (off.get("org"), off.get("opponent_id"), off.get("matchmaker_id"))
    except Exception as e:
        log_error("booking check", e)
        return FAIL, "crashed: %s" % e


CHECKS = [
    ("Launch / install", _check_launch),
    ("Data files", _check_data_files),
    ("Combat engine", _check_engine_smoke),
    ("Save / load", _check_save_round_trip),
    ("Version", _check_version_strings),
    ("People system", _check_people_system),
    ("Booking pipe", _check_booking_pipe),
]


def run_checks() -> list[tuple[str, str, str]]:
    """Returns [(label, status, detail), ...] status is pass/warn/fail."""
    results = []
    for label, fn in CHECKS:
        try:
            status, detail = fn()
        except Exception as e:
            status, detail = FAIL, "check itself crashed: %s" % e
        if status not in (PASS, WARN, FAIL):
            # old bool-style checkers
            status = PASS if status else FAIL
        results.append((label, status, detail))
        if status == FAIL:
            log("self_check FAIL: %s -- %s" % (label, detail))
        elif status == WARN:
            log("self_check WARN: %s -- %s" % (label, detail))
    return results


def playable(results=None) -> bool:
    """True if nothing is a hard fail — warnings still let you play."""
    if results is None:
        results = run_checks()
    return all(status != FAIL for _, status, _ in results)


def self_check(verbose: bool = True) -> bool:
    """Returns True iff there are no FAILs. Warnings still count as playable."""
    if verbose:
        print("=" * 50)
        print(" FROM NOTHING TO LEGEND — SYSTEM SELF-CHECK")
        print("=" * 50)
    results = run_checks()
    for label, status, detail in results:
        if verbose:
            mark = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}.get(status, status.upper())
            print("[%s] %s\n       %s" % (mark, label, detail))
    ok = playable(results)
    warns = sum(1 for _, s, _ in results if s == WARN)
    fails = sum(1 for _, s, _ in results if s == FAIL)
    if verbose:
        print("-" * 50)
        if ok and not warns:
            print("RESULT: ALL SYSTEMS OK")
        elif ok:
            print("RESULT: PLAYABLE — %d warning(s), no blockers" % warns)
        else:
            print("RESULT: %d FAIL, %d WARN — see debug_log.txt" % (fails, warns))
        print("Log file:", LOG_PATH)
        print("=" * 50)
    return ok


if __name__ == "__main__":
    ok = self_check(verbose=True)
    sys.exit(0 if ok else 1)


def audit_playtest_state(fighter, pool=None) -> list[dict]:
    """Return high-signal career contradictions for playtest exports.

    These are warnings, not migration rules.  Old saves remain diagnostic
    references only; the purpose is to make a bad live state obvious to the
    next developer without reading a multi-megabyte world dump.
    """
    issues = []
    def add(code, severity, message, **data):
        row = {"code": code, "severity": severity, "message": message}
        if data:
            row["data"] = data
        issues.append(row)

    flags = getattr(fighter, "story_flags", None) or {}
    pro = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    am = list(getattr(fighter, "amateur_record", None) or [0, 0, 0])
    pw, pl, pd = (int((pro + [0, 0, 0])[i] or 0) for i in range(3))
    pro_bouts = pw + pl + pd
    rank = flags.get("org_rank")
    tags = set(getattr(fighter, "narrative_tags", None) or [])

    if isinstance(rank, int) and rank <= 2 and pro_bouts <= 2 and pw == 0:
        add("rank_resume_mismatch", "warn",
            "Winless early pro is ranked at/near the top of the promotion.",
            pro_record=pro[:3], org_rank=rank, org=getattr(fighter, "organization", None))
    if "title_contender" in tags and pw < 3:
        add("title_tag_resume_mismatch", "warn",
            "title_contender tag exists before a three-win professional résumé.",
            pro_record=pro[:3], tags=sorted(tags))
    career_tags = tags.intersection({"prospect", "pro", "contender", "journeyman", "title_contender"})
    if len(career_tags) >= 3:
        add("career_tags_fragmented", "info",
            "Multiple mutually-confusing career identity tags are stored simultaneously.",
            tags=sorted(career_tags))

    c = getattr(fighter, "org_contract", None) or {}
    org = str(getattr(fighter, "organization", "") or "")
    if org and isinstance(c, dict) and not str(c.get("org") or "").strip():
        add("blank_contract_org", "high",
            "Visible promotion and exclusive contract disagree; booking may treat the fighter as a free agent.",
            organization=org, contract=c)
    if c and (int(c.get("purse_win", 0) or 0) <= 0 or int(c.get("purse_show", 0) or 0) <= 0):
        add("zero_contract_terms", "warn", "Exclusive contract has zero purse terms.", contract=c)
    old_belt = str(flags.get("org_belt") or "")
    if old_belt and org and old_belt != org:
        add("stale_promotion_belt", "warn",
            "A belt from a previous promotion is still marked as the active belt.",
            organization=org, belt=old_belt)
    if org == "UFC":
        ur = flags.get("ufc_rank")
        ufc_hist = [h for h in (getattr(fighter, "fight_history", None) or [])
                    if str(h.get("event") or "") == "UFC" and bool(h.get("pro", True))]
        if flags.get("title_offer_week") and (not isinstance(ur, int) or ur > 3 or len(ufc_hist) < 3):
            add("premature_ufc_title_offer", "high",
                "UFC title offer exists before the promotion-specific résumé/ranking gate.",
                ufc_rank=ur, ufc_bouts=len(ufc_hist), title_offer_week=flags.get("title_offer_week"))

    hist = list(getattr(fighter, "fight_history", None) or [])
    hw = sum(1 for h in hist if str(h.get("result") or "").lower().startswith("w"))
    hl = sum(1 for h in hist if str(h.get("result") or "").lower().startswith("l"))
    official_w = int((am + [0])[0] or 0) + pw
    official_l = int((am + [0, 0])[1] or 0) + pl
    if hist and (hw != official_w or hl != official_l):
        add("record_history_gap", "info",
            "Official record and detailed fight-history ledger do not reconcile; may be legacy/pre-ledger activity.",
            official=[official_w, official_l], history=[hw, hl], history_n=len(hist))

    opaque_stops = []
    for h in hist:
        method = str(h.get("method") or "").upper()
        if "KO" not in method and "TKO" not in method:
            continue
        st = h.get("stats") or {}
        if int(st.get("knockdowns", 0) or 0) == 0 and int(st.get("times_down", 0) or 0) == 0:
            opaque_stops.append({"opponent": h.get("opponent"), "result": h.get("result"), "method": h.get("method")})
    if opaque_stops:
        add("opaque_stoppage_stats", "info",
            "KO/TKO ledger entries exist with neither knockdown nor times-down evidence; event trace is needed to explain them.",
            count=len(opaque_stops), examples=opaque_stops[-3:])

    if pool is not None:
        n = len(getattr(pool, "fighters", []) or [])
        if n < 400:
            add("small_world_pool", "warn", "Loaded world pool is unusually small for the normal career world.", world_pool_n=n)
    return issues
