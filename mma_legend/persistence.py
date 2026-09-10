"""Versioned JSON save/load for the v0.4.0 career and world state."""
from __future__ import annotations
import json
import zipfile
from pathlib import Path
from typing import Optional
from . import constants as C, data
from .models import Fighter
from .ui import GameConsole
from .world import FighterPool
DEFAULT_SAVE=Path.cwd()/"save.json"
SAVE_VERSION=20

def _pack_belts(pool) -> dict:
    out = {}
    for k, v in (getattr(pool, "belts", None) or {}).items():
        if isinstance(v, dict):
            out[str(k)] = {key: v.get(key) for key in (
                "name", "fid", "org", "wc", "won_week", "defenses", "last_defense_week")
                if v.get(key) is not None}
    return out

def _json_safe(value):
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "as_dict"):
        return _json_safe(value.as_dict())
    if hasattr(value, "__dict__"):
        return _json_safe({k: v for k, v in vars(value).items() if not str(k).startswith("_")})
    return str(value)

def debug_snapshot(fighter, pool) -> dict:
    """Small career dump at the top of a save so we can debug without the pool."""
    flags = getattr(fighter, "story_flags", None) or {}
    fh = list(getattr(fighter, "fight_history", None) or [])
    wins = sum(1 for h in fh if str(h.get("result") or "").lower().startswith("w"))
    losses = sum(1 for h in fh if str(h.get("result") or "").lower().startswith("l"))
    org = getattr(fighter, "organization", None)
    wc = getattr(fighter, "weight_class", None)
    same = 0
    for f in getattr(pool, "fighters", []) or []:
        if getattr(f, "organization", None) == org and getattr(f, "weight_class", None) == wc:
            same += 1
    try:
        from . import contracts as _contracts
        live_contract = _contracts.active(fighter)
    except Exception:
        live_contract = getattr(fighter, "org_contract", None)
    rank_value = flags.get("ufc_rank") if str(org or "") == "UFC" else flags.get("org_rank")
    belt_value = flags.get("org_belt") if flags.get("org_belt") == org else None
    return {
        "week": getattr(fighter, "week", 0),
        "name": getattr(fighter, "name", ""),
        "fid": getattr(fighter, "fid", None),
        "org": org,
        "room": getattr(fighter, "room", None),
        "contract": live_contract,
        "rank": rank_value,
        "board": flags.get("org_board"),
        "belt": belt_value,
        "pro_record": list(getattr(fighter, "pro_record", None) or []),
        "amateur_record": list(getattr(fighter, "amateur_record", None) or []),
        "history_n": len(fh),
        "history_wl": [wins, losses],
        "pro_fights_done": flags.get("pro_fights_done"),
        "pending_renewal": flags.get("pending_renewal"),
        "title_offer_week": flags.get("title_offer_week"),
        "last_release": flags.get("last_release"),
        "last_note": getattr(fighter, "last_week_note", ""),
        "pool_n": len(getattr(pool, "fighters", []) or []),
        "world_pool_n": len(getattr(pool, "fighters", []) or []),
        "same_org_class": same,
        "booked": bool(getattr(fighter, "booked_fight", None)),
    }


def _pool_blob(fighter, pool, fighters):
    return {
        "fighters": [_json_safe(f.to_dict()) for f in fighters if f is not fighter],
        "news": pool.news,
        "champions": {wc: {"name": champ.name, "fid": getattr(champ, "fid", None)}
                      for wc, champ in pool.champions.items()},
        "next_id": getattr(pool, "next_id", 1000),
        "belts": _pack_belts(pool),
        "events": _json_safe(getattr(pool, "events", []) or []),
        "event_history": _json_safe(getattr(pool, "event_history", []) or []),
        "title_history": _json_safe(getattr(pool, "title_history", []) or []),
        "hall_of_fame": _json_safe(getattr(pool, "hall_of_fame", []) or []),
        "matchup_history": _json_safe(getattr(pool, "matchup_history", {}) or {}),
        "matchup_lifetime": _json_safe(getattr(pool, "matchup_lifetime", {}) or {}),
        "next_event_id": int(getattr(pool, "next_event_id", 1) or 1),
        "event_counters": _json_safe(getattr(pool, "event_counters", {}) or {}),
        "week": int(getattr(pool, "week", 0) or 0),
    }


def _payload(fighter, pool, fighters, *, path="", phase="") -> dict:
    fighters = list(fighters or [])
    dbg = debug_snapshot(fighter, pool)
    dbg["saved_pool_n"] = len([f for f in fighters if f is not fighter])
    try:
        from . import telemetry
        telemetry.save_marker(path, fighter, pool, phase=phase)
        playtest = telemetry.snapshot(
            fighter, pool, saved_pool_n=dbg["saved_pool_n"], path=str(path), phase=phase)
    except Exception:
        playtest = {}
    return {
        "save_version": SAVE_VERSION,
        "game_version": C.GAME_VERSION,
        "debug": dbg,
        "player": _json_safe(fighter.to_dict()),
        "pool": _pool_blob(fighter, pool, fighters),
        "playtest": playtest,
    }


def save_game(console:GameConsole,fighter:Fighter,pool:FighterPool,path:Path=DEFAULT_SAVE)->bool:
    payload=_payload(fighter, pool, pool.fighters, path=path, phase="manual")
    tmp=Path(str(path)+".tmp")
    try:
        tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"); tmp.replace(path)
        console.good(f"✅ Game saved to {path}"); console.pause(.6); return True
    except (OSError,TypeError) as e:
        console.warn(f"❌ Save failed: {e}"); console.pause(1); return False

def _upgrade_player(d:dict)->dict:
    d=dict(d)
    had_active_sport = "active_amateur_sport" in d
    old_flags = d.get("story_flags") if isinstance(d.get("story_flags"), dict) else {}
    legacy_active_sport = old_flags.get("compete_in")
    defaults=Fighter.new_npc("_template",data.country_by_name("USA")).to_dict()
    # New fields are added lazily, preserving old saves.
    for k,v in defaults.items(): d.setdefault(k,v)
    d.setdefault("damage",{"cuts":0,"nose":0,"eyes":0,"body":0,"legs":0,"total":0})
    d.setdefault("natural_weight", float(d.get("weight",70))); d.setdefault("walking_weight", float(d.get("weight",70)))
    d.setdefault("fight_history", []); d.setdefault("recent_results", []); d.setdefault("current_streak", 0)
    d.setdefault("last_fight_stats", {}); d.setdefault("performance_rating", 0.0); d.setdefault("retired", False); d.setdefault("age_weeks", 0)
    d.setdefault("suspension_weeks",0); d.setdefault("doping_fines_paid",0)
    d.setdefault("narrative_tags",[]); d.setdefault("active_chains",[]); d.setdefault("story_flags",{}); d.setdefault("rivalries",[])
    d.setdefault("camp_active",False); d.setdefault("camp_focus",None); d.setdefault("camp_opponent_style",None); d.setdefault("camp_weeks_remaining",0); d.setdefault("camp_bonus",0); d.setdefault("camp_technique_xp",0); d.setdefault("opponent_read",0)
    d.setdefault("fid",None); d.setdefault("rival_id",None)
    d.setdefault("career_knockdowns",0); d.setdefault("career_times_down",0); d.setdefault("archetype",None)
    d.setdefault("debt",0); d.setdefault("org_contract",None); d.setdefault("intl_camp",None); d.setdefault("intl_camp_weeks",0); d.setdefault("connections",[]); d.setdefault("side_job",None)
    if int(d.get("age", 16) or 16) < 18:
        d["debt"] = 0
        if int(d.get("money", 0) or 0) < 0:
            d["money"] = 0
    d.setdefault("job_shifts",{}); d.setdefault("job_reputation",0); d.setdefault("job_history",[])
    d.setdefault("timeline",[]); d.setdefault("notes",[]); d.setdefault("last_ledger",{}); d.setdefault("injury_history",[]); d.setdefault("mileage",0); d.setdefault("rng_seed",0)
    d.setdefault("last_training_focus", "N"); d.setdefault("last_training_intensity", "B"); d.setdefault("last_week_report", []); d.setdefault("ui_seen_help", [])
    d.setdefault("ui_compact", False); d.setdefault("ui_week_report", True); d.setdefault("ui_color", None); d.setdefault("ui_tutorial_active", False); d.setdefault("ui_tutorial_step", 0); d.setdefault("ui_tutorial_complete", False)
    d.setdefault("preferred_gameplan", "Balanced"); d.setdefault("last_gameplan", {})
    d.setdefault("medals",{"national":{"gold":0,"silver":0,"bronze":0},"european":{"gold":0,"silver":0,"bronze":0},"world":{"gold":0,"silver":0,"bronze":0}})
    d.setdefault("bjj_belt",None); d.setdefault("bjj_stripes",0); d.setdefault("bjj_grade_points",0); d.setdefault("bjj_weeks",0)
    d.setdefault("judo_belt",None); d.setdefault("judo_grade_points",0); d.setdefault("judo_weeks",0)
    d.setdefault("tkd_belt",None); d.setdefault("tkd_grade_points",0); d.setdefault("tkd_weeks",0); d.setdefault("specialty_gym",None)
    d.setdefault("specialty_gym_type",None); d.setdefault("specialty_coach",None); d.setdefault("specialty_pool",[]); d.setdefault("specialty_gym_dues",0)
    d.setdefault("specialty_gym_weeks",0); d.setdefault("specialty_gym_tech_xp",0); d.setdefault("specialty_gym_last_learn_week",0)
    d.setdefault("specialty_gym_event_history",[]); d.setdefault("specialty_gym_auto",True)
    d.setdefault("sport_records", {}); d.setdefault("sport_medals", {}); d.setdefault("sport_experience", {})
    d.setdefault("sport_championships", {}); d.setdefault("sport_national_teams", {})
    d.setdefault("competition_sport", "MMA")
    d.setdefault("competition_level", None)
    d.setdefault("competition_due_week", 0)
    if d.get("competition_signup") and not d.get("competition_sport"):
        d["competition_sport"] = "MMA"
    if not d["sport_records"].get("mma"):
        d["sport_records"]["mma"] = list(d.get("amateur_record") or [0, 0, 0])
    d.setdefault("active_amateur_sport", "MMA")
    if not had_active_sport and legacy_active_sport:
        d["active_amateur_sport"] = legacy_active_sport
    d["sport_national_teams"].setdefault("mma", bool(d.get("national_team", False)))
    d.setdefault("nickname", None); d.setdefault("nickname_choices", [])
    d.setdefault("manager_id", None); d.setdefault("people_rel", {})
    d.setdefault("organization", None); d.setdefault("room", "local")
    d.setdefault("perks", []); d.setdefault("recent_opponent_ids", [])
    d.setdefault("cut_fatigue", 0)
    # v12: reach plus real defensive/tactical attributes. Old values are
    # inferred once; new careers store them directly.
    d.setdefault("reach", max(150, min(218, int(d.get("height", 175) or 175) + 1)))
    d.setdefault("stance", "Orthodox")
    d.setdefault("striking_def", int((int(d.get("striking", 25) or 25) + int(d.get("speed", 25) or 25)) / 2))
    d.setdefault("submission_def", int((int(d.get("submissions", 20) or 20) + int(d.get("grappling", 25) or 25)) / 2))
    d.setdefault("distance_management", int((int(d.get("fight_iq", 25) or 25) + int(d.get("speed", 25) or 25)) / 2))
    # v13 terminology migration. Historical technique names remain intact;
    # only identity/category fields are canonicalized.
    if d.get("amateur_discipline") == "Sambo":
        d["amateur_discipline"] = "Combat Sambo"
    if d.get("style") == "Sambo":
        d["style"] = "Combat Sambo"
    flags = d.get("story_flags") if isinstance(d.get("story_flags"), dict) else {}
    if str(flags.get("compete_in") or "").lower() == "sambo":
        flags["compete_in"] = "Combat Sambo"
    d["story_flags"] = flags
    from . import identity as _id
    return _id.repair_save(d)


def _trim_pool_for_autosave(fighter, pool, cap: int = 520) -> list:
    """Keep champions/top-ranked/the player's rival no matter what, then
    fill the remaining slots. Previously this just sliced the list, which
    could silently drop the rival or a champion and orphan the rivalry."""
    others = [f for f in pool.fighters if f is not fighter]
    if len(others) <= cap:
        return others
    protected_ids = pool.protected_ids(player=fighter)
    protected = [f for f in others if getattr(f, "fid", None) in protected_ids]
    rest = [f for f in others if getattr(f, "fid", None) not in protected_ids]
    # Fill remaining slots favoring fame/relevance so the pool stays interesting.
    rest.sort(key=lambda f: (getattr(f, "fame", 0), getattr(f, "pro_debut", False)), reverse=True)
    slots_left = max(0, cap - len(protected))
    return protected + rest[:slots_left]

def load_game(console:GameConsole,path:Path=DEFAULT_SAVE)->Optional[tuple]:
    try: payload=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError: console.warn("No save file found."); console.pause(1); return None
    except (json.JSONDecodeError,OSError) as e: console.warn(f"❌ Load failed: {e}"); console.pause(1); return None
    try:
        try:
            from . import telemetry
            telemetry.restore(payload.get("playtest"))
        except Exception:
            pass
        player_data=_upgrade_player(payload["player"]); player_data["is_player"]=True
        fighter=Fighter.from_dict(player_data)
        try:
            fighter.sync_techniques()
        except Exception:
            pass
        try:
            from . import identity as _id
            _id.sync(fighter)
        except Exception:
            pass
        try:
            from . import amateur_sports as _sports
            _sports.ensure(fighter)
        except Exception:
            pass
        pool=FighterPool()
        pdata=payload.get("pool",{})
        for fd in pdata.get("fighters",[]):
            fd=_upgrade_player(fd); country_data=data.country_by_name(fd.get("country","USA")); npc=Fighter.new_npc(fd.get("name","Unknown"),country_data)
            for key,value in fd.items():
                if hasattr(npc,key): setattr(npc,key,value)
            try:
                npc.sync_techniques()
            except Exception:
                pass
            try:
                from . import amateur_sports as _sports
                _sports.ensure(npc)
            except Exception:
                pass
            pool.fighters.append(npc)
        pool.news=pdata.get("news",[]); pool.next_id=int(pdata.get("next_id",1000))
        if hasattr(pool, "attach_player"):
            pool.attach_player(fighter)
        if len(pool.fighters) < 600:
            if hasattr(pool, "seed_missing"):
                pool.seed_missing(840, 560)
        pool.update_rankings()
        try:
            from . import contracts as _co
            flags = getattr(fighter, "story_flags", None) or {}
            rel = flags.get("last_release") if isinstance(flags.get("last_release"), dict) else {}
            if getattr(fighter, "pro_debut", False) and not _co.active(fighter):
                if rel.get("org") == fighter.organization or flags.get("org_belt") == fighter.organization:
                    _co.queue_renewal(fighter)
        except Exception:
            pass
        # Backfill stable ids for saves made before v9 (or any NPC that
        # slipped through without one), so rivals/champions stay trackable.
        for npc in pool.fighters:
            if not getattr(npc, "fid", None):
                npc.fid = "npc_%s" % pool.next_id
                pool.next_id += 1
        if fighter.rival and not getattr(fighter, "rival_id", None):
            match = next((f for f in pool.fighters if f.name == fighter.rival), None)
            if match:
                fighter.rival_id = match.fid
        for wc, info in pdata.get("champions", {}).items():
            if isinstance(info, dict):
                fid, name = info.get("fid"), info.get("name")
            else:
                fid, name = None, info
            target = pool.get_by_id(fid) if fid else None
            if target is None and name:
                target = fighter if fighter.name == name else next((f for f in pool.fighters if f.name == name), None)
            if target:
                pool.champions[wc] = target
        pool.belts = pdata.get("belts") or {}
        pool.events = list(pdata.get("events") or [])
        pool.event_history = list(pdata.get("event_history") or [])
        pool.title_history = list(pdata.get("title_history") or [])
        pool.hall_of_fame = list(pdata.get("hall_of_fame") or [])
        pool.matchup_history = dict(pdata.get("matchup_history") or {})
        pool.matchup_lifetime = dict(pdata.get("matchup_lifetime") or {})
        pool.next_event_id = int(pdata.get("next_event_id", 1) or 1)
        pool.event_counters = dict(pdata.get("event_counters") or {})
        pool.week = int(pdata.get("week", getattr(fighter, "week", 1)) or getattr(fighter, "week", 1))
    except (KeyError,TypeError,ValueError) as e:
        console.warn(f"❌ Save is invalid or from an incompatible version: {e}"); console.pause(1); return None
    console.good(f"✅ Game loaded from {path} (save v{payload.get('save_version',1)})"); console.pause(.6); return fighter,pool


SLOT_A = Path.cwd()/"save_a.json"
SLOT_B = Path.cwd()/"save_b.json"
AUTO = Path.cwd()/"save_auto.json"

def autosave(fighter, pool, path=AUTO, phase: str = "autosave"):
    # 1.24: autosaves are canonical world snapshots.  The old 520-NPC trim
    # made a loaded autosave a *different universe* from a manual save: in a
    # 907-fighter playtest 387 fighters vanished, changing rankings, belts and
    # future matchmaking.  Compact JSON keeps the full world around ~3 MB.
    fighters = list(getattr(pool, "fighters", []) or [])
    payload=_payload(fighter, pool, fighters, path=path, phase=phase)
    tmp=Path(str(path)+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(",", ":")),encoding="utf-8")
    tmp.replace(path)


def export_playtest_bundle(console, fighter, pool, path: Path | None = None) -> bool:
    """Write one uploadable forensic bundle for a human playtest.

    It includes a fresh canonical full-world snapshot plus the exact rendered
    UI/inputs and structured trace written by telemetry.  Old save slots are
    intentionally excluded: a bundle describes *this* live state only.
    """
    path = path or (Path.cwd() / "MMA_Legend_playtest_bundle.zip")
    snapshot_path = Path.cwd() / "playtest_snapshot.json"
    summary_path = Path.cwd() / "playtest_summary.json"
    try:
        fighters = list(getattr(pool, "fighters", []) or [])
        payload = _payload(fighter, pool, fighters, path=snapshot_path, phase="playtest_export")
        snapshot_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        try:
            from . import diagnostics
            audit = diagnostics.audit_playtest_state(fighter, pool)
        except Exception as e:
            audit = [{"code": "audit_crash", "severity": "warn", "message": str(e)}]
        summary = {
            "game_version": C.GAME_VERSION,
            "save_version": SAVE_VERSION,
            "debug": debug_snapshot(fighter, pool),
            "audit": audit,
            "playtest": payload.get("playtest") or {},
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        candidates = [snapshot_path, summary_path, Path.cwd()/"playtest_trace.jsonl", Path.cwd()/"playtest_trace.previous.jsonl", Path.cwd()/"debug_log.txt"]
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for src in candidates:
                if src.exists() and src.is_file():
                    zf.write(src, arcname=src.name)
        console.good("✅ Playtest bundle exported: %s" % path.name)
        console.print("Upload this ZIP with your bug notes; it includes the recent screen/input trace.")
        console.pause(.6)
        return True
    except (OSError, TypeError, ValueError, zipfile.BadZipFile) as e:
        console.warn("❌ Playtest export failed: %s" % e)
        console.pause(1)
        return False

def save_menu(console, fighter, pool):
    console.header("SAVE / PLAYTEST")
    console.print("  A) Slot A")
    console.print("  B) Slot B")
    console.print("  P) Export playtest bundle")
    console.print("     Save + recent screen/input/AI trace")
    console.print("  X) Cancel")
    ch = console.ask("Slot > ").strip().upper()
    if ch == "P":
        return export_playtest_bundle(console, fighter, pool)
    path = {"A": SLOT_A, "B": SLOT_B}.get(ch)
    if not path:
        return False
    return save_game(console, fighter, pool, path)

def _slot_label(path: Path) -> str:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        p = raw.get("player") or {}
        rec = p.get("pro_record") or [0, 0, 0]
        am = p.get("amateur_record") or [0, 0, 0]
        week = p.get("week", 1)
        name = p.get("name", "?")
        return "%s  w%s  pro %s-%s-%s  am %s-%s-%s" % (name, week, rec[0], rec[1], rec[2], am[0], am[1], am[2])
    except Exception:
        return "(empty)"


def load_menu(console):
    console.header("LOAD")
    console.print("  A) Slot A  " + _slot_label(SLOT_A))
    console.print("  B) Slot B  " + _slot_label(SLOT_B))
    console.print("  C) Autosave  " + _slot_label(AUTO))
    console.print("  D) save.json  " + _slot_label(DEFAULT_SAVE))
    ch = console.ask("Slot > ").strip().upper()
    path = {"A": SLOT_A, "B": SLOT_B, "C": AUTO, "D": DEFAULT_SAVE}.get(ch)
    if not path:
        return None
    return load_game(console, path)
