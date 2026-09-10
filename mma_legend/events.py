"""v0.6 event brain: eligibility, context, weights, cooldowns."""
from __future__ import annotations

import random
import re
from typing import Optional

from . import data
from .ui import GameConsole, wrap_text

MEDIA_WORDS = (
    "podcast", "interview", "press", "media", "tv ", "radio", "youtube",
    "influencer", "documentary",
)
SPONSOR_WORDS = ("sponsor", "endorsement", "brand deal", "nike", "reebok")
PARTY_WORDS = ("party", "club", "nightlife", "hangover")
EARLY_BAN = (
    "podcast", "interview", "press", "media", "tv", "radio", "youtube",
    "crowd chant", "crowd favorite", "fan club", "fan letter", "fight night",
    "fight day", "fight week", "fight month", "charity", "tv appearance",
    "documentary", "weigh-in scrum", "rival trash", "fan meeting",
    "nightclub", "club night", "bottle service", "fight offer",
    "national team invitation", "national team invite",
)
INSTANT_CAREER_BAN = (
    "fight offer", "a) win", "b) lose",
)



def _is_cutting(fighter) -> bool:
    if not getattr(fighter, "booked_fight", None):
        return False
    try:
        from .cut import meaningful_cut
        return meaningful_cut(fighter)
    except Exception:
        return False

def context_pack(fighter) -> dict:
    rec = fighter.get_total_record()
    last = ""
    if getattr(fighter, "recent_results", None):
        last = str(fighter.recent_results[-1])
    active_sport = str(getattr(fighter, "active_amateur_sport", "MMA") or "MMA")
    try:
        from .amateur_sports import key_for
        sport_nt = bool((getattr(fighter, "sport_national_teams", None) or {}).get(key_for(active_sport)))
    except Exception:
        sport_nt = False
    return {
        "wins": rec[0],
        "losses": rec[1],
        "draws": rec[2],
        "am_wins": fighter.amateur_record[0],
        "pro_wins": fighter.pro_record[0],
        "pro": bool(fighter.pro_debut),
        "week": fighter.week,
        "fame": fighter.fame,
        "rep": fighter.reputation,
        "money": fighter.money,
        "energy": fighter.energy,
        "health": fighter.health,
        "nutrition": fighter.nutrition,
        "nt": bool(fighter.national_team) if active_sport == "MMA" else sport_nt,
        "org": fighter.organization or "",
        "camp": bool(getattr(fighter, "camp_active", False) or getattr(fighter, "intl_camp", None)),
        "intl_camp": bool(getattr(fighter, "intl_camp", None)),
        "booked": bool(getattr(fighter, "booked_fight", None)),
        "cutting": _is_cutting(fighter),
        "streak": int(getattr(fighter, "current_streak", 0) or 0),
        "followers": int(getattr(fighter, "followers", 0) or 0),
        "debt": int(getattr(fighter, "debt", 0) or 0),
        "teammate": bool(getattr(fighter, "teammate", None)),
        "teammate_name": str(getattr(fighter, "teammate", None) or "your teammate"),
        "manager": bool(getattr(fighter, "manager_id", None) or getattr(fighter, "manager", None)),
        "gym": bool(getattr(fighter, "specialty_gym", None)),
        "gym_type": str(getattr(fighter, "specialty_gym_type", "") or "").lower(),
        "gym_name": str(getattr(fighter, "specialty_gym", "") or "your gym"),
        "gym_weeks": int(getattr(fighter, "specialty_gym_weeks", 0) or 0),
        "education_stage": str(getattr(fighter, "education_stage", "") or ""),
        "degree": str(getattr(fighter, "university_degree", "") or ""),
        "sponsors": len(getattr(fighter, "sponsors", None) or []),
        "rels": dict(getattr(fighter, "relationships", None) or {}),
        "last": last,
        "name": fighter.name,
        "country": fighter.country,
        "tags": list(getattr(fighter, "narrative_tags", None) or []),
        "active_sport": active_sport,
    }


def can_media(fighter) -> bool:
    return fighter.pro_debut or fighter.get_total_record()[0] >= 3 or fighter.fame >= 8


def can_sponsor(fighter) -> bool:
    return fighter.get_total_record()[0] >= 2 or fighter.fame >= 6 or fighter.pro_debut


def can_ranked_fight(fighter) -> bool:
    return fighter.pro_debut and fighter.promotion_tier >= 8


def _text(event: dict) -> str:
    return (event.get("title", "") + " " + event.get("description", "")).lower()


def eligible(fighter, event: dict, ctx: dict) -> bool:
    req = event.get("require") or {}
    trig = event.get("trigger") or {}
    title = _text(event)

    min_age = req.get("min_age", event.get("min_age", 0))
    max_age = req.get("max_age", event.get("max_age"))
    if fighter.age < int(min_age or 0):
        return False
    if max_age is not None and fighter.age > int(max_age):
        return False
    if int(getattr(fighter, "suspension_weeks", 0) or 0) > 0:
        if any(w in title for w in ("fight", "ready", "weigh-in", "weigh in", "bout", "card", "camp for")):
            return False
    if "european" in title:
        from .systems15 import europe_ok
        if not europe_ok(fighter):
            return False
    if event.get("category") == "camp" and not (getattr(fighter, "intl_camp", None) or getattr(fighter, "camp_active", False)):
        return False
    if req.get("cutting") is True and not ctx.get("cutting"):
        return False
    # Weight-cut story text is contextual even in legacy packs that forgot a
    # requirement. Never tell a natural heavyweight they are obsessing over a cut.
    if any(w in title for w in ("scale obsession", "weight bully", "water cut", "make weight", "weight-cut")) and not ctx.get("cutting"):
        return False

    # Legacy event packs predate several stateful career systems. These narrow
    # text guards suppress contradictions without blocking introduction events.
    rels = ctx.get("rels") or {}
    if any(w in title for w in ("your girlfriend", "your boyfriend", "your partner", "date night with your")) and int(rels.get("partner", 0) or 0) <= 0:
        return False
    if any(w in title for w in ("contract renewal", "renew your contract", "your deal expires")) and not getattr(fighter, "org_contract", None):
        return False
    if any(w in title for w in ("defend your belt", "title defense", "champion obligations")):
        flags = getattr(fighter, "story_flags", None) or {}
        if not (flags.get("org_belt") or (flags.get("career_title_stats") or {}).get("championships")):
            return False
    if any(w in title for w in ("international camp", "camp abroad", "overseas camp room")) and not ctx.get("intl_camp"):
        return False

    # Tone gates even if JSON forgot require
    if any(w in title for w in MEDIA_WORDS) and not can_media(fighter):
        return False
    if ctx["wins"] < 2 and any(w in title for w in EARLY_BAN):
        return False
    if ctx["wins"] == 0 and ctx["losses"] == 0 and any(w in title for w in EARLY_BAN):
        return False
    if any(w in title for w in INSTANT_CAREER_BAN) and "federation letter" not in title:
        if "fight offer" in title:
            return False
        if event.get("choices") and any("win" == (c.get("label") or "").lower().strip("a) ") for c in event.get("choices") or []):
            return False
    # Quarantine base events.json career-template cards that pay a fight without a bout
    eid = str(event.get("id", ""))
    if eid.isdigit() and int(eid) <= 176:
        if "fight offer" in title or title.strip().startswith("fight offer"):
            return False
        if event.get("category") == "national_team" and not ctx["nt"] and not (event.get("require") or {}).get("flag"):
            if "invitation" in title:
                return False
    if "fight week" in title and fighter.fight_cooldown > 0:
        return False
    if "fight night" in title and ctx["wins"] + ctx["losses"] < 1:
        return False
    if re.search(r"\brent\b", title) or "gym dues" in title or "dues" in title:
        from .cut import parents_help
        if parents_help(fighter):
            return False
    if any(w in title for w in SPONSOR_WORDS) and not can_sponsor(fighter):
        return False
    if "national team" in title and "invitation" in title and fighter.national_team:
        return False
    if "national team" in title and not fighter.national_team and ctx["wins"] < 5:
        return False

    min_wins = req.get("min_wins", trig.get("wins", 0) if trig.get("type") == "record" else 0)
    max_wins = req.get("max_wins")
    if ctx["wins"] < int(min_wins or 0):
        return False
    if max_wins is not None and ctx["wins"] > int(max_wins):
        return False
    if req.get("pro") and not ctx["pro"]:
        return False
    if req.get("amateur") and ctx["pro"]:
        return False
    if req.get("min_fame") and ctx["fame"] < int(req["min_fame"]):
        return False
    if req.get("min_losses") and ctx["losses"] < int(req["min_losses"]):
        return False
    if req.get("max_losses") is not None and ctx["losses"] > int(req["max_losses"]):
        return False
    if req.get("min_rep") and ctx["rep"] < int(req["min_rep"]):
        return False
    if req.get("max_rep") is not None and ctx["rep"] > int(req["max_rep"]):
        return False
    if req.get("min_energy") is not None and ctx["energy"] < int(req["min_energy"]):
        return False
    if req.get("max_energy") is not None and ctx["energy"] > int(req["max_energy"]):
        return False
    if req.get("min_health") is not None and ctx["health"] < int(req["min_health"]):
        return False
    if req.get("max_health") is not None and ctx["health"] > int(req["max_health"]):
        return False
    if req.get("national_team") and not ctx["nt"]:
        return False
    if req.get("nt") and not ctx["nt"]:
        return False
    if req.get("injured") is not None:
        injured = bool((getattr(fighter, "injury", None) or {}).get("weeks"))
        if injured != bool(req.get("injured")):
            return False
    if req.get("min_damage") is not None:
        total_damage = int((getattr(fighter, "damage", None) or {}).get("total", 0) or 0)
        if total_damage < int(req["min_damage"]):
            return False
    if req.get("last"):
        allowed = req["last"] if isinstance(req["last"], list) else [req["last"]]
        if str(ctx["last"]).upper() not in {str(x).upper() for x in allowed}:
            return False
    flags = getattr(fighter, "story_flags", None) or {}
    if req.get("flag") and not flags.get(req["flag"]):
        return False
    if str(event.get("id", "")) == "v8c_05" and (getattr(fighter, "bjj_belt", None) == "blue" or flags.get("done_event_v8c_05")):
        return False
    if req.get("min_pro_wins") and ctx["pro_wins"] < int(req["min_pro_wins"]):
        return False
    if req.get("max_am") is not None:
        from .v08 import am_bouts
        if am_bouts(fighter) > int(req["max_am"]):
            return False
    if req.get("min_rel_coach") and int((getattr(fighter, "relationships", {}) or {}).get("coach", 0)) < int(req["min_rel_coach"]):
        return False
    if event.get("conditional") and (event.get("trigger") or {}).get("type") == "conditional":
        # only when require already matched (flag/nt/pro etc)
        pass
    if req.get("min_money") is not None and ctx["money"] < int(req["min_money"]):
        return False
    if req.get("max_money") is not None and ctx["money"] > int(req["max_money"]):
        return False
    if req.get("min_week") and ctx["week"] < int(req["min_week"]):
        return False
    if req.get("max_week") is not None and ctx["week"] > int(req["max_week"]):
        return False

    # Phase-3 context gates. These use state that already existed on Fighter;
    # no save-schema fields are introduced. Boolean requirements are explicit
    # (`is not None`) so `False` can deliberately mean "only when absent".
    for key in ("camp", "intl_camp", "booked", "teammate", "manager", "gym"):
        if req.get(key) is not None and bool(ctx.get(key)) != bool(req.get(key)):
            return False
    if req.get("gym_type") is not None:
        wanted = req.get("gym_type")
        allowed = wanted if isinstance(wanted, list) else [wanted]
        if str(ctx.get("gym_type") or "").lower() not in {str(x).lower() for x in allowed}:
            return False
    if req.get("min_gym_weeks") is not None and int(ctx.get("gym_weeks", 0) or 0) < int(req.get("min_gym_weeks") or 0):
        return False
    if req.get("max_gym_weeks") is not None and int(ctx.get("gym_weeks", 0) or 0) > int(req.get("max_gym_weeks") or 0):
        return False
    if req.get("education_stage") is not None:
        wanted = req.get("education_stage")
        allowed = wanted if isinstance(wanted, list) else [wanted]
        if str(ctx.get("education_stage") or "") not in {str(x) for x in allowed}:
            return False
    if req.get("degree") is not None:
        wanted = req.get("degree")
        allowed = wanted if isinstance(wanted, list) else [wanted]
        if str(ctx.get("degree") or "") not in {str(x) for x in allowed}:
            return False
    if req.get("org") is not None:
        want = req.get("org")
        if isinstance(want, bool):
            if bool(ctx.get("org")) != want:
                return False
        else:
            allowed_orgs = want if isinstance(want, list) else [want]
            if str(ctx.get("org") or "") not in {str(x) for x in allowed_orgs}:
                return False
    if req.get("active_sport") is not None:
        wanted = req.get("active_sport")
        allowed_sports = wanted if isinstance(wanted, list) else [wanted]
        if str(ctx.get("active_sport")) not in {str(x) for x in allowed_sports}:
            return False
    if req.get("min_streak") is not None and ctx["streak"] < int(req["min_streak"]):
        return False
    if req.get("max_streak") is not None and ctx["streak"] > int(req["max_streak"]):
        return False
    if req.get("min_followers") is not None and ctx["followers"] < int(req["min_followers"]):
        return False
    if req.get("max_followers") is not None and ctx["followers"] > int(req["max_followers"]):
        return False
    if req.get("min_debt") is not None and ctx["debt"] < int(req["min_debt"]):
        return False
    if req.get("max_debt") is not None and ctx["debt"] > int(req["max_debt"]):
        return False
    if req.get("min_sponsors") is not None and ctx["sponsors"] < int(req["min_sponsors"]):
        return False
    if req.get("max_sponsors") is not None and ctx["sponsors"] > int(req["max_sponsors"]):
        return False
    for rel in ("family", "friends", "coach", "partner", "rival"):
        val = int((ctx.get("rels") or {}).get(rel, 0) or 0)
        lo = req.get("min_rel_" + rel)
        hi = req.get("max_rel_" + rel)
        if lo is not None and val < int(lo):
            return False
        if hi is not None and val > int(hi):
            return False

    # Cooldown / one-shot
    flags = getattr(fighter, "story_flags", None) or {}
    eid = str(event.get("id", event.get("title", "")))
    if flags.get("done_event_" + eid) and req.get("once"):
        return False
    last = int(flags.get("cd_event_" + eid, -999))
    cd = int(req.get("cooldown", 12 if any(w in title for w in MEDIA_WORDS) else 6))
    if fighter.week - last < cd and last > 0:
        return False

    cat = (event.get("category") or "").lower()
    try:
        from .education import is_enrolled
        school_on = is_enrolled(fighter)
    except Exception:
        school_on = getattr(fighter, "school_status", "none") in ("school", "uni")
    if cat == "school" and not school_on:
        return False
    # Match school terms as words. The old substring check treated words such
    # as "upgrades" as containing "grades", silently quarantining unrelated
    # adult events.
    if re.search(r"\b(?:exam|school|grades|teacher|classmates|homework)\b", title):
        if not school_on or int(getattr(fighter, "age", 20) or 20) > 19:
            return False
    if cat in ("fame",) and ctx["wins"] < 3:
        return False
    kind = trig.get("type")
    if kind == "nutrition":
        n = ctx["nutrition"]
        if not (n < 35 or n > 85):
            return False
        lo, hi = trig.get("min", 0), trig.get("max", 100)
        if not (lo <= n <= hi):
            return False
    if kind == "doping":
        if fighter.doping_risk < 25:
            return False
    if kind == "national_team":
        # Invitation cards fire only when you are NOT already on the team.
        if "invitation" in title:
            if ctx["nt"]:
                return False
        elif not ctx["nt"]:
            return False
        last_nt = int(flags.get("cd_nt_pack", -999))
        if fighter.week - last_nt < 14 and last_nt > 0:
            return False
    if kind == "fame" and ctx["fame"] < trig.get("min", 8):
        return False

    # Story contradiction
    chains = getattr(fighter, "active_chains", None) or []
    if chains:
        cid = str(chains[0].get("id", ""))
        if cid == "injury_fork" and any(w in title for w in PARTY_WORDS):
            return False
    if getattr(fighter, "hangover_weeks", 0) > 0 and "training breakthrough" in title:
        return False
    return True


_PRIORITY = {
    "story": 3.0, "career": 2.2, "competition": 2.2, "coach": 1.8,
    "fight": 1.6, "health": 1.5, "sponsor": 1.3, "life": 1.0, "training": 1.1,
}


def _weight(event: dict, ctx: dict) -> float:
    w = float((event.get("trigger") or {}).get("chance", 0.08))
    req = event.get("require") or {}
    if req.get("min_wins"):
        w += 0.04
    if event.get("choices"):
        w += 0.02
    if ctx["pro"] and (event.get("require") or {}).get("pro"):
        w += 0.05
    cat = (event.get("category") or event.get("priority") or "life").lower()
    w *= _PRIORITY.get(cat, 1.0)
    if event.get("conditional"):
        w *= 3.5
    return max(0.01, w)


def validate_event_pack() -> list:
    """Validate IDs plus the event DSL used by every JSON pack.

    Phase 3 makes this a release gate rather than a duplicate-ID-only check:
    malformed requirements/effects can otherwise create cards that silently
    never fire or choices that do nothing.
    """
    from .models import Fighter

    seen = {}
    issues = []
    packs = data.event_packs()
    known_req = {
        "min_age", "max_age", "min_wins", "max_wins", "pro", "amateur",
        "min_fame", "min_losses", "max_losses", "min_rep", "max_rep",
        "min_energy", "max_energy", "min_health", "max_health",
        "national_team", "nt", "injured", "min_damage", "last", "flag",
        "min_pro_wins", "max_am", "min_rel_coach", "min_money", "max_money",
        "min_week", "max_week", "cooldown", "once",
        # Phase-3 contextual requirements
        "camp", "intl_camp", "booked", "cutting", "teammate", "manager", "gym", "org",
        "gym_type", "min_gym_weeks", "max_gym_weeks", "education_stage", "degree",
        "min_streak", "max_streak", "min_followers", "max_followers", "active_sport",
        "min_debt", "max_debt", "min_sponsors", "max_sponsors",
        "min_rel_family", "max_rel_family", "max_rel_coach",
        "min_rel_friends", "max_rel_friends", "min_rel_partner",
        "max_rel_partner", "min_rel_rival", "max_rel_rival",
    }
    direct_effects = set(Fighter.__dataclass_fields__)
    special_effects = {
        "money_scale", "national_team", "hangover", "bjj_belt", "team",
        "family", "friends", "coach", "partner", "rival",
    }
    numeric_pairs = (
        ("min_age", "max_age"), ("min_wins", "max_wins"),
        ("min_losses", "max_losses"), ("min_rep", "max_rep"),
        ("min_energy", "max_energy"), ("min_health", "max_health"),
        ("min_money", "max_money"), ("min_week", "max_week"),
        ("min_streak", "max_streak"), ("min_followers", "max_followers"),
        ("min_debt", "max_debt"), ("min_sponsors", "max_sponsors"),
        ("min_gym_weeks", "max_gym_weeks"),
        ("min_rel_family", "max_rel_family"),
        ("min_rel_friends", "max_rel_friends"),
        ("min_rel_coach", "max_rel_coach"),
        ("min_rel_partner", "max_rel_partner"),
        ("min_rel_rival", "max_rel_rival"),
    )

    def check_effects(label, eid, effects):
        if not isinstance(effects or {}, dict):
            issues.append("%s %s effects are not an object" % (label, eid))
            return
        for key in (effects or {}):
            if key.startswith("relationships."):
                if key.split(".", 1)[1] not in {"partner", "family", "friends", "coach", "rival"}:
                    issues.append("%s %s unknown relationship effect %s" % (label, eid, key))
            elif key not in direct_effects and key not in special_effects:
                issues.append("%s %s unknown effect %s" % (label, eid, key))

    for label, pack in packs:
        for e in pack:
            eid = str(e.get("id", ""))
            if not eid:
                issues.append("%s missing id: %s" % (label, e.get("title")))
                continue
            if eid in seen:
                issues.append("duplicate id %s (%s and %s)" % (eid, seen[eid], label))
            else:
                seen[eid] = label
            if not str(e.get("title", "")).strip():
                issues.append("%s %s missing title" % (label, eid))
            req = e.get("require") or {}
            for key in req:
                if key not in known_req:
                    issues.append("%s %s unknown requirement %s" % (label, eid, key))
            if req.get("pro") and req.get("amateur"):
                issues.append("%s %s requires both pro and amateur" % (label, eid))
            for lo, hi in numeric_pairs:
                if req.get(lo) is not None and req.get(hi) is not None:
                    try:
                        if float(req[lo]) > float(req[hi]):
                            issues.append("%s %s contradictory %s/%s" % (label, eid, lo, hi))
                    except (TypeError, ValueError):
                        issues.append("%s %s nonnumeric %s/%s" % (label, eid, lo, hi))
            trig = e.get("trigger") or {}
            if "chance" in trig:
                try:
                    chance = float(trig["chance"])
                    if not 0 <= chance <= 1:
                        issues.append("%s %s chance outside 0..1" % (label, eid))
                except (TypeError, ValueError):
                    issues.append("%s %s invalid chance" % (label, eid))
            check_effects(label, eid, e.get("effects") or {})
            keys = set()
            for idx, choice in enumerate(e.get("choices") or []):
                if not str(choice.get("label", "")).strip():
                    issues.append("%s %s choice %s missing label" % (label, eid, idx))
                key = str(choice.get("key", "") or "").strip().upper()
                if key:
                    if key in keys:
                        issues.append("%s %s duplicate choice key %s" % (label, eid, key))
                    keys.add(key)
                check_effects(label, eid, choice.get("effects") or {})
    return issues


def generate_random_event(fighter) -> Optional[dict]:
    try:
        from . import ai
        return ai.pick_event(fighter)
    except Exception:
        pass
    ctx = context_pack(fighter)
    pool = []
    packs = data.all_events(newest_first=True)
    for evt in packs:
        if eligible(fighter, evt, ctx):
            pool.append(evt)
    if not pool:
        return None
    if random.random() > 0.24:
        return None
    weights = [_weight(e, ctx) for e in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def apply_effects(fighter, effects: dict, ctx: Optional[dict] = None) -> None:
    ctx = ctx or context_pack(fighter)
    for key, value in (effects or {}).items():
        if key == "money_scale":
            # fraction of current money or flat scaled by wins
            fighter.money = int(fighter.money) + int(value) + ctx["wins"] * 15
            if int(getattr(fighter, "age", 16) or 16) < 18:
                fighter.money = max(0, int(fighter.money))
                fighter.debt = 0
            continue
        if key.startswith("relationships."):
            rk = key.split(".", 1)[1]
            fighter.relationships[rk] = max(0, min(100, int(fighter.relationships.get(rk, 50)) + int(value)))
            continue
        if key == "money":
            fighter.money = int(fighter.money) + int(value)
            if int(getattr(fighter, "age", 16) or 16) < 18:
                fighter.money = max(0, int(fighter.money))
                fighter.debt = 0
        elif key == "debt":
            # v1.40: minors cannot enter formal debt through event effects.
            if int(getattr(fighter, "age", 16) or 16) < 18:
                fighter.debt = 0
            else:
                fighter.debt = max(0, int(getattr(fighter, "debt", 0) or 0) + int(value))
        elif key == "bodyfat":
            try:
                from .cut import physique_floor
                floor = physique_floor(getattr(fighter, "physique_type", "Athletic"),
                                       bool(getattr(fighter, "camp_active", False)))
            except Exception:
                floor = 6.0
            fighter.bodyfat = max(floor, min(35.0, float(getattr(fighter, "bodyfat", 12.0) or 12.0) + float(value)))
        elif key == "walking_weight":
            fighter.walking_weight = max(52.0, min(130.0, float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight) + float(value)))
        elif key == "fame":
            from .notoriety import add_fame
            add_fame(fighter, int(value), "life event")
        elif key == "followers":
            from .notoriety import add_followers
            add_followers(fighter, int(value))
        elif key in ("reputation", "legacy_score", "press_hype", "opponent_read", "school_grade"):
            target_key = key
            if key == "school_grade" and str(getattr(fighter, "education_stage", "") or "") == "university":
                target_key = "university_average"
            nv = max(0, int(getattr(fighter, target_key, 0) or 0) + int(value))
            if key in ("reputation", "press_hype", "opponent_read", "school_grade"):
                nv = min(100, nv)
            setattr(fighter, target_key, nv)
        elif key in fighter.relationships:
            fighter.relationships[key] = max(0, min(100, fighter.relationships[key] + int(value)))
        elif key == "national_team":
            fighter.national_team = bool(value)
        elif key == "hangover":
            fighter.hangover_weeks = max(getattr(fighter, "hangover_weeks", 0), int(value))
        elif key == "bjj_belt":
            fighter.bjj_belt = value
            fighter.story_flags = fighter.story_flags or {}
            fighter.story_flags["belt_ready"] = False
            fighter.story_flags["done_event_v8c_05"] = True
        elif key == "team":
            fighter.team = str(value)
        elif key in ("bjj_grade_points", "judo_grade_points", "specialty_gym_tech_xp"):
            setattr(fighter, key, max(0, int(getattr(fighter, key, 0) or 0) + int(value)))
            if key == "bjj_grade_points":
                try:
                    from .amateur_sports import _sync_stripes
                    _sync_stripes(fighter)
                except Exception:
                    pass
        elif hasattr(fighter, key):
            cur = getattr(fighter, key)
            if isinstance(cur, (int, float)):
                if key in ("money", "followers", "fame", "reputation", "legacy_score"):
                    setattr(fighter, key, max(0, cur + int(value)))
                else:
                    try:
                        from . import constants as _C
                        from .physiology import gain_stat
                        if key in _C.SKILLS:
                            gain_stat(fighter, key, int(value))
                        else:
                            setattr(fighter, key, max(0, min(100, cur + int(value))))
                    except Exception:
                        setattr(fighter, key, max(0, min(100, cur + int(value))))


def _format_effects(effects: dict) -> str:
    parts = []
    for k, v in (effects or {}).items():
        try:
            parts.append("%s %+d" % (k, int(v)))
        except (TypeError, ValueError):
            parts.append("%s: %s" % (k, v))
    return ", ".join(parts)


def _fill(text: str, ctx: dict) -> str:
    if not text:
        return ""
    return (
        text.replace("{name}", str(ctx.get("name", "")))
        .replace("{wins}", str(ctx.get("wins", 0)))
        .replace("{country}", str(ctx.get("country", "")))
        .replace("{money}", str(ctx.get("money", 0)))
        .replace("{teammate}", str(ctx.get("teammate_name", "your teammate")))
        .replace("{org}", str(ctx.get("org", "")))
        .replace("{gym}", str(ctx.get("gym_name", "your gym")))
        .replace("{degree}", str(ctx.get("degree", "")))
        .replace("{streak}", str(ctx.get("streak", 0)))
    )



def balanced_event_effects(fighter, effects: dict) -> dict:
    """Return player-facing event effects with stage-aware guardrails.

    Historical event packs intentionally contain some large cinematic rewards.
    Those were authored before the economy/fame scales stabilised and can now
    overwhelm several weeks of normal play.  Keep the flavour, but cap one
    random card so events complement the career loop rather than replace it.
    Direct ``apply_effects`` remains unchanged for scripted systems/tests.
    """
    src = dict(effects or {})
    if not src:
        return src
    pro = bool(getattr(fighter, "pro_debut", False))
    tier = int(getattr(fighter, "promotion_tier", 0) or 0)
    if not pro:
        money_cap, fame_cap, rep_cap, followers_cap = 750, 6, 8, 35
    elif tier >= 10 or str(getattr(fighter, "organization", "") or "") == "UFC":
        money_cap, fame_cap, rep_cap, followers_cap = 6000, 10, 10, 220
    elif tier >= 7:
        money_cap, fame_cap, rep_cap, followers_cap = 3500, 9, 10, 140
    else:
        money_cap, fame_cap, rep_cap, followers_cap = 1800, 7, 9, 90

    stat_keys = {
        "striking", "kicks", "grappling", "submissions", "takedown_def",
        "ground_control", "ko_power", "cardio", "strength", "speed",
        "durability", "fight_iq", "confidence", "discipline", "happiness",
        "mental_toughness", "natural_talent", "work_ethic", "charisma",
        "adaptability", "energy", "health", "nutrition", "weight_cut_health",
    }
    out = {}
    for key, value in src.items():
        if not isinstance(value, (int, float)):
            out[key] = value
            continue
        cap = None
        if key in ("money", "money_scale"):
            cap = money_cap
        elif key == "debt":
            cap = 600 if pro else 250
        elif key == "fame":
            cap = fame_cap
        elif key == "reputation":
            cap = rep_cap
        elif key == "followers":
            cap = followers_cap
        elif key in stat_keys:
            cap = 4 if key not in ("energy", "health", "happiness", "nutrition", "weight_cut_health") else 18
        elif key == "bodyfat":
            cap = 0.8
        elif key == "walking_weight":
            cap = 1.0
        elif key.startswith("relationships.") or key in {"family", "friends", "coach", "partner", "rival"}:
            cap = 10
        if cap is None:
            out[key] = value
        else:
            out[key] = max(-cap, min(cap, value))
            if isinstance(value, int) and isinstance(out[key], float):
                out[key] = int(out[key])
    return out

def handle_event(console: GameConsole, fighter, event: dict) -> None:
    ctx = context_pack(fighter)
    title = _fill(event.get("title", "Event"), ctx)
    desc = _fill(event.get("description", ""), ctx)
    console.header("EVENT")
    for line in wrap_text(title, min(42, int(getattr(console, "width", 44) or 44))):
        console.print(line)
    for line in wrap_text(desc, min(42, int(getattr(console, "width", 44) or 44))):
        console.print(line)
    for line in wrap_text("Why: %s wins · fame %s · %s" % (
            ctx["wins"], ctx["fame"], "PRO" if ctx["pro"] else "AMATEUR"), min(42, int(getattr(console, "width", 44) or 44))):
        console.print(line)

    effects = balanced_event_effects(fighter, event.get("effects") or {})
    if effects:
        for line in wrap_text("Effects: " + _format_effects(effects), min(42, int(getattr(console, "width", 44) or 44))):
            console.print(line)
        apply_effects(fighter, effects, ctx)

    choices = event.get("choices")
    if choices:
        console.print("How do you respond?")
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        def choice_key(c, idx):
            explicit = str(c.get("key", "") or "").strip().upper()
            if explicit:
                return explicit
            label = str(c.get("label", "") or "").strip()
            m = re.match(r"^([A-Z0-9])\s*[\)\.\-:]\s*", label, re.I)
            if m:
                return m.group(1).upper()
            return letters[idx] if idx < len(letters) else str(idx + 1)

        keyed = []
        for i, c in enumerate(choices):
            label = _fill(c.get("label", ""), ctx)
            key = choice_key(c, i)
            keyed.append((key, c, label))
            # Legacy packs often embedded "A)" in the label; newer packs
            # store key/label separately. Show one clean key in both cases.
            shown = ("  " + label) if re.match(r"^[A-Z0-9]\s*[\)\.\-:]\s*", label, re.I) else ("  %s) %s" % (key, label))
            for j, line in enumerate(wrap_text(shown, min(42, int(getattr(console, "width", 44) or 44)))):
                console.print(line if j == 0 else "    " + line)
        raw = console.ask("\n  Choice > ").strip().upper()
        selected = None
        if raw:
            selected = next((c for key, c, label in keyed
                             if key == raw or str(label).upper() == raw), None)
        if selected:
            selected_effects = balanced_event_effects(fighter, selected.get("effects") or {})
            apply_effects(fighter, selected_effects, ctx)
            console.info("You chose: " + _fill(selected.get("label", ""), ctx))
            if selected_effects:
                for line in wrap_text("  -> " + _format_effects(selected_effects), min(42, int(getattr(console, "width", 44) or 44))):
                    console.print(line)
        else:
            console.warn("Invalid choice — no extra effect.")
    else:
        getattr(console, "continue_prompt", lambda *_a, **_k: console.read_pause(title + " " + desc, extra=0.2))("Press Enter to continue")
        _mark_seen(fighter, event)
        return
    # A choice is itself the acknowledgement. Do not make the player press
    # Enter again immediately after selecting an option.
    _mark_seen(fighter, event)


def _mark_seen(fighter, event) -> None:
    if not hasattr(fighter, "story_flags") or fighter.story_flags is None:
        fighter.story_flags = {}
    eid = str(event.get("id", event.get("title", "")))
    fighter.story_flags["cd_event_" + eid] = fighter.week
    cat = str(event.get("category") or "life").lower()
    previous = str(fighter.story_flags.get("last_event_category") or "").lower()
    fighter.story_flags["event_category_streak"] = int(fighter.story_flags.get("event_category_streak", 0) or 0) + 1 if previous == cat else 1
    fighter.story_flags["last_event_category"] = cat
    if (event.get("require") or {}).get("once"):
        fighter.story_flags["done_event_" + eid] = True
    if (event.get("trigger") or {}).get("type") == "national_team" or "national team" in _text(event):
        fighter.story_flags["cd_nt_pack"] = fighter.week
