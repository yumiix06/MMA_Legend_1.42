"""0.8.8 booker: rooms, offers, dates. UFC picker stays locked until org is UFC."""
from __future__ import annotations

import random

ROOMS = {
    "local": {"label": "Local Fight Nights", "tier": 4, "win": (250, 400), "weeks": (5, 7)},
    "regional": {"label": "Regional FC", "tier": 5, "win": (550, 750), "weeks": (6, 8)},
    "national": {"label": "National MMA", "tier": 6, "win": (1100, 1400), "weeks": (7, 9)},
    "mid": {"label": "Regional Major (Bellator/PFL-style)", "tier": 8, "win": (1800, 2800), "weeks": (7, 9)},
    "dwcs": {"label": "Contender Series (DWCS-style)", "tier": 9, "win": (2200, 2800), "weeks": (5, 7)},
    "ufc": {"label": "UFC", "tier": 12, "win": (8000, 14000), "weeks": (8, 10)},
    "showcase": {"label": "Contender night (DWCS-style)", "tier": 9, "win": (2200, 2800), "weeks": (5, 7)},
}

HABITS = ("walker", "shooter", "body hunter", "spreader", "clinch pest", "guard puller")

MAJOR = {"Bellator", "ONE Championship", "ONE", "PFL", "Rizin FF", "UFC", "UFC Championship"}


def current_room(fighter) -> str:
    r = getattr(fighter, "room", None)
    if r in ROOMS:
        return r
    org = getattr(fighter, "organization", None) or ""
    if org == "UFC" or "UFC" in org:
        return "ufc"
    if "Contender" in org or "DWCS" in org:
        return "dwcs"
    if org in MAJOR or "Bellator" in org or "PFL" in org or "ONE" in org:
        return "mid"
    return "local"


def set_room(fighter, room: str) -> None:
    """Change the matchmaking band only. Named org is owned by identity/orgs."""
    from . import identity
    identity.set_band(fighter, room)


def last4_losses(fighter) -> int:
    rec = list(getattr(fighter, "recent_results", None) or [])[-4:]
    return sum(1 for x in rec if str(x).lower().startswith("l"))


def can_use_ranked_picker(fighter) -> bool:
    return (getattr(fighter, "organization", "") or "") == "UFC"


def purse_for(fighter, room: str, org_id: str | None = None) -> tuple[int, int]:
    from . import identity
    org_id = org_id or identity.canonical_org(fighter)
    spec_range = identity.purse_range(org_id)
    if spec_range:
        lo, hi = spec_range
    else:
        spec = ROOMS.get(room, ROOMS["local"])
        lo, hi = spec["win"]
    win = random.randint(int(lo), int(hi))
    if getattr(fighter, "national_team", False) or (
        (getattr(fighter, "medals", {}) or {}).get("national", {}).get("gold", 0)
    ):
        win = int(win * 1.15)
    try:
        from .education import degree_benefit
        win = int(round(win * float(degree_benefit(fighter, "contract_mult", 1.0))))
    except Exception:
        pass
    show = max(40, int(win * 0.20))
    return win, show


def style_kit(style: str) -> list[str]:
    s = (style or "").lower()
    if "box" in s:
        return ["Jab", "Cross", "Hook", "Rear Slip"]
    if "wrest" in s:
        return ["Jab", "Cross", "Double Leg", "Single Leg", "Sprawl", "Clinch Entry"]
    if "muay" in s or "kick" in s:
        return ["Jab", "Teep", "Low Kick", "Long Guard"]
    if "sambo" in s:
        return ["Jab", "Cross", "Ouchi Gari", "Low Kick", "Straight Ankle Lock"]
    if "bjj" in s or "jiu" in s:
        return ["Knee Slice Pass", "Scissor Sweep", "Rear Naked Choke", "Elbow-Knee Escape"]
    return ["Jab", "Cross", "Sprawl", "Low Kick"]


def apply_kit(opp, style: str) -> None:
    kit = style_kit(style or getattr(opp, "style", "") or getattr(opp, "amateur_discipline", ""))
    opp.techniques = list(kit)
    opp.technique_levels = {t: random.randint(1, 3) for t in kit}
    if not getattr(opp, "habit", None):
        opp.habit = random.choice(HABITS)


def tune_record(opp, room: str, same_country: str | None) -> None:
    if room == "local":
        w, l = random.randint(2, 8), random.randint(1, 4)
        if random.random() < 0.20:
            w, l = random.randint(1, 3), random.randint(1, 3)
    elif room == "regional":
        w, l = random.randint(4, 12), random.randint(1, 5)
    elif room == "showcase":
        w, l = random.randint(10, 18), random.randint(1, 4)
    else:
        w, l = random.randint(8, 16), random.randint(2, 6)
    opp.pro_record = [w, l, random.randint(0, 1)]
    opp.pro_debut = True
    if same_country and random.random() < 0.70:
        opp.country = same_country


def booker_cold(fighter) -> int:
    last = int(getattr(fighter, "booker_decline_week", 0) or 0)
    if last <= 0:
        return 0
    left = 4 - (fighter.week - last)
    return max(0, left)


def maybe_drop_room(fighter) -> None:
    if last4_losses(fighter) >= 2:
        cur = current_room(fighter)
        if cur == "national":
            set_room(fighter, "regional")
        elif cur == "regional":
            set_room(fighter, "local")


def maybe_promote(fighter) -> str | None:
    wins = int((fighter.pro_record or [0])[0])
    room = current_room(fighter)
    if last4_losses(fighter) >= 2:
        return None
    fame = int(getattr(fighter, "fame", 0) or 0)
    if room == "local" and wins >= 3:
        set_room(fighter, "regional")
        return "regional"
    if room == "regional" and wins >= 5:
        set_room(fighter, "national")
        return "national"
    if room == "national" and wins >= 8 and fame >= 12:
        set_room(fighter, "mid")
        return "mid"
    if room == "mid" and wins >= 10 and fame >= 16:
        return "mid"
    # Contender Series is an invitation, not a room you get promoted into
    # after three regional wins. That path was signing 3-0 kids to the UFC.
    return None


ROOM_ORG = {
    "local": "LFA",
    "regional": "Cage Warriors",
    "national": "KSW",
    "mid": "Bellator",
    "dwcs": "LFA",
    "ufc": "UFC",
    "showcase": "LFA",
}


def org_for_room(fighter, room: str | None = None) -> str:
    org = getattr(fighter, "organization", None) or ""
    if org and org not in ("Free Agent",):
        return org
    return ROOM_ORG.get(room or current_room(fighter), "LFA")


def _skill_avg(f) -> float:
    from . import constants as C
    skills = list(C.SKILLS)
    return sum(getattr(f, s, 40) for s in skills) / max(1, len(skills))


def opponent_fits(fighter, cand) -> bool:
    """Amateur fights amateurs in the same record band. Pros do not meet 18-2 vets on debut."""
    if cand is None or cand is fighter or getattr(cand, "is_player", False):
        return False
    if not getattr(cand, "active", True):
        return False
    # Never match across divisions. Several older paths called opponent_fits()
    # directly and could bypass the caller's weight-class filter.
    fw = getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", None)
    cw = getattr(cand, "fight_weight_class", None) or getattr(cand, "weight_class", None)
    if fw and cw and fw != cw:
        return False
    if getattr(fighter, "pro_debut", False):
        if not getattr(cand, "pro_debut", False):
            return False
        prec = list(fighter.pro_record or [0, 0, 0])
        orec = list(cand.pro_record or [0, 0, 0])
        pw = int(prec[0] or 0); pb = sum(int(x or 0) for x in prec[:3])
        ow = int(orec[0] or 0); ob = sum(int(x or 0) for x in orec[:3])
        # Early pro matchmaking must protect *experience bands*, not merely
        # reject 8+ win veterans.  In the 1.23 playtest a 0-1 prospect was
        # paired with a 5-0/6-0 contracted fighter from another promotion.
        if pb <= 2 and (ow > pw + 3 or ob > pb + 4):
            return False
        if pb <= 5 and ow > pw + 4:
            return False
        if ow > pw + 5 and ow >= 8:
            return False
        try:
            from . import constants as _C
            skills = list(_C.SKILLS)
            pa = sum(getattr(fighter, s, 40) for s in skills) / max(1, len(skills))
            oa = sum(getattr(cand, s, 40) for s in skills) / max(1, len(skills))
            if oa > pa + 12:
                return False
        except (TypeError, ValueError, AttributeError):
            pass
        try:
            from . import rating
            if rating.power(cand) > rating.power(fighter) + rating.window(fighter) + 2:
                return False
        except (TypeError, ValueError, AttributeError, ImportError):
            pass
        return True
    if getattr(cand, "pro_debut", False):
        return False
    if int((cand.pro_record or [0, 0, 0])[0]) >= 3:
        return False
    aw = int((fighter.amateur_record or [0, 0, 0])[0])
    ow = int((cand.amateur_record or [0, 0, 0])[0])
    if ow > aw + 4:
        return False
    try:
        from . import constants as _C
        skills = list(_C.SKILLS)
        pa = sum(getattr(fighter, s, 40) for s in skills) / max(1, len(skills))
        oa = sum(getattr(cand, s, 40) for s in skills) / max(1, len(skills))
        if oa > pa + 10:
            return False
    except (TypeError, ValueError, AttributeError):
        pass
    try:
        from . import rating
        if rating.power(cand) > rating.power(fighter) + rating.window(fighter) + 12:
            return False
    except (TypeError, ValueError, AttributeError, ImportError):
        pass
    return True


def pick_pool_opponent(fighter, pool, room: str, org_id: str | None = None):
    """Live roster first. Emergency fill is registered onto the pool."""
    from .fights import generate_random_opponent
    from . import people
    opp = None
    last_ids = list(getattr(fighter, "recent_opponent_ids", None) or [])[-12:]
    if pool is not None:
        roster = list(getattr(pool, "fighters", []) or [])
        wc = getattr(fighter, "weight_class", None)
        org_id = org_id or org_for_room(fighter, room)
        same_org, free_agents = [], []
        for f in roster:
            if f is fighter or getattr(f, "is_player", False):
                continue
            if not getattr(f, "active", True):
                continue
            if wc and getattr(f, "weight_class", None) != wc:
                continue
            if getattr(f, "fid", None) in last_ids:
                continue
            if not opponent_fits(fighter, f):
                continue
            f_org = getattr(f, "organization", None) or ""
            if org_id:
                # Named promotions do not silently borrow fighters under an
                # exclusive deal with a rival org.  Free agents are valid
                # emergency opposition; otherwise generate/register a roster
                # fighter for this promotion.
                if f_org == org_id:
                    same_org.append(f)
                elif not f_org or f_org == "Free Agent":
                    free_agents.append(f)
            else:
                free_agents.append(f)
        cands = same_org or free_agents
        if cands:
            pa = _skill_avg(fighter)
            window = [f for f in cands if abs(_skill_avg(f) - pa) <= 14]
            bag = window or cands
            if room in ("local", "regional") and getattr(fighter, "country", None):
                home = [f for f in bag if getattr(f, "country", None) == fighter.country]
                if home and random.random() < 0.90:
                    bag = home
            rival_id = getattr(fighter, "rival_id", None)
            mm = people.matchmaker_for(org_id)
            if mm and mm.quirk == "wants_rematches" and rival_id:
                hit = next((f for f in bag if getattr(f, "fid", None) == rival_id), None)
                if hit:
                    return hit
            if mm and mm.quirk == "style_avoid":
                my_style = (getattr(fighter, "style", "") or getattr(fighter, "amateur_discipline", "") or "").lower()
                filtered = [f for f in bag if (getattr(f, "style", "") or "").lower() != my_style]
                if filtered:
                    bag = filtered
            try:
                from . import living_careers
                bag.sort(key=lambda f: living_careers.opponent_score(
                    fighter, f, org_id, abs(_skill_avg(f) - pa)))
            except Exception:
                bag.sort(key=lambda f: abs(_skill_avg(f) - pa))
            pick_roll = random.random()
            opp = bag[0] if pick_roll < 0.55 else random.choice(bag[: min(5, len(bag))])
            try:
                from . import telemetry
                telemetry.decision(
                    "matchmaker_pick",
                    choice=getattr(opp, "fid", None) or getattr(opp, "name", None),
                    reason="same_org" if same_org else "free_agent",
                    room=room, org=org_id, player_record=list(getattr(fighter, "pro_record", []) or []),
                    pick_roll=round(pick_roll, 4), same_org_candidates=len(same_org),
                    free_agent_candidates=len(free_agents),
                    candidates=[{
                        "id": getattr(x, "fid", None), "name": getattr(x, "name", ""),
                        "org": getattr(x, "organization", None), "record": list(getattr(x, "pro_record", []) or []),
                        "skill_avg": round(_skill_avg(x), 1),
                    } for x in bag[:5]],
                )
            except Exception:
                pass
    if opp is None:
        bias = fighter.country if room == "local" else None
        opp = generate_random_opponent(fighter, country_bias=bias)
        apply_kit(opp, getattr(opp, "style", "") or "MMA")
        tune_record(opp, room, fighter.country if room == "local" else None)
        if org_id:
            opp.organization = org_id
            try:
                from . import identity as _id
                opp.promotion_tier = int(getattr(_id, "tier_for", lambda _x: 0)(org_id) or getattr(fighter, "promotion_tier", 0) or 0)
                opp.room = _id.band_for(org_id, room)
            except Exception:
                opp.room = room
        if pool is not None:
            if not getattr(opp, "fid", None):
                opp.fid = "npc_%s" % getattr(pool, "next_id", 9000)
                pool.next_id = int(getattr(pool, "next_id", 9000)) + 1
            pool.fighters.append(opp)
        try:
            from . import telemetry
            telemetry.decision(
                "matchmaker_pick", choice=getattr(opp, "fid", None) or getattr(opp, "name", None),
                reason="generated_roster_fill", room=room, org=org_id,
                player_record=list(getattr(fighter, "pro_record", []) or []),
                opponent_record=list(getattr(opp, "pro_record", []) or []),
                opponent_org=getattr(opp, "organization", None), skill_avg=round(_skill_avg(opp), 1))
        except Exception:
            pass
    return opp


def set_booked(fighter, offer: dict) -> dict:
    """Single writer for fighter.booked_fight."""
    offer = dict(offer or {})
    opp = offer.get("opponent")
    if opp is not None and not offer.get("opponent_id"):
        offer["opponent_id"] = getattr(opp, "fid", None)
    if opp is not None and not offer.get("opponent_snap"):
        from .models import _pack_booked
        packed = _pack_booked({"opponent": opp, **{k: v for k, v in offer.items() if k != "opponent"}})
        if packed and packed.get("opponent_snap"):
            offer["opponent_snap"] = packed["opponent_snap"]
    cur = int(getattr(fighter, "week", 1) or 1)
    delay = 4 if getattr(fighter, "pro_debut", False) and int((getattr(fighter, "pro_record") or [0])[0]) == 0 else 2
    dw = int(offer.get("date_week") or (cur + delay))
    if dw <= cur:
        dw = cur + delay
    offer["date_week"] = dw
    fighter.booked_fight = offer
    if offer.get("weight_class"):
        fighter.fight_weight_class = str(offer.get("weight_class"))
    fighter._show_purse = int(offer.get("purse_show") or 40)
    fighter.camp_for_bout = max(int(getattr(fighter, "camp_for_bout", 0) or 0), dw - cur)
    try:
        from . import cut
        cut.ensure_weight_campaign(fighter, reset=True)
    except Exception:
        pass
    return offer


def build_offer(fighter, pool=None, org_id=None):
    from . import people
    room = current_room(fighter)
    maybe_drop_room(fighter)
    room = current_room(fighter)
    org_id = org_id or org_for_room(fighter, room)
    opp = pick_pool_opponent(fighter, pool, room, org_id)
    apply_kit(opp, getattr(opp, "style", "") or "MMA")
    win, show = purse_for(fighter, room, org_id=org_id)
    win = int(win * people.manager_purse_multiplier(fighter))
    win = int(win * people.promoter_purse_multiplier(fighter, org_id))
    show = max(40, int(win * 0.20))
    delay = random.randint(*ROOMS[room]["weeks"])
    tag = pick_tag(fighter, opp, room)
    trap_bias = people.promoter_trap_bias(fighter, org_id)
    mm = people.matchmaker_for(org_id)
    mm_rel = people.rapport(fighter, mm.id) if mm else 50
    if trap_bias > 0.12 and random.random() < trap_bias:
        tag = "trap"
    if mm_rel < 35 and random.random() < 0.35:
        tag = "trap"
    if tag == "short notice":
        delay = 2
        win = int(win * 1.25)
        show = max(40, int(win * 0.20))
    if tag == "trap":
        for s in ("striking", "grappling", "cardio", "fight_iq", "durability"):
            if hasattr(opp, s):
                setattr(opp, s, min(96, getattr(opp, s) + 8))
    why = {
        "trap": "protect the prospect",
        "tune-up": "keep you busy",
        "short notice": "short notice",
        "catchweight": "catchweight fill",
    }.get(tag, "even")
    if getattr(fighter, "rival_id", None) and getattr(opp, "fid", None) == fighter.rival_id:
        why = "rematch"
        tag = "rematch"
    card = build_card(fighter, opp, room)
    return {
        "room": room,
        "org": org_id if org_id else ROOMS[room]["label"],
        "opponent": opp,
        "opponent_id": getattr(opp, "fid", None),
        "date_week": fighter.week + delay,
        "purse_win": win,
        "purse_show": show,
        "tag": tag,
        "card": card,
        "matchmaker_id": mm.id if mm else None,
        "promoter_id": (people.promoter_for(org_id).id if people.promoter_for(org_id) else None),
        "why": why,
        "superfight": False,
    }


def pick_tag(fighter, opp, room: str) -> str:
    from . import constants as C
    skills = list(C.SKILLS)
    pa = sum(getattr(fighter, s, 40) for s in skills) / len(skills)
    oa = sum(getattr(opp, s, 40) for s in skills) / len(skills)
    if room == "local" and oa + 4 < pa and random.random() < 0.22:
        return "tune-up"
    if oa > pa + 8:
        return "trap"
    if random.random() < 0.12:
        return "short notice"
    if random.random() < 0.08:
        return "catchweight"
    return "even"


def _rec(f) -> str:
    r = f.pro_record if getattr(f, "pro_debut", False) else f.amateur_record
    try:
        return "%s-%s-%s" % (r[0], r[1], r[2])
    except Exception:
        return "0-0-0"


def build_card(fighter, main_opp, room: str) -> list:
    """Poster lines. Other bouts are names + a simmed result string."""
    n = 3 if room == "local" else (5 if room in ("regional", "national") else 6)
    lines = []
    firsts = ["Martinez", "Petrov", "Silva", "Okonkwo", "Byrne", "Kade", "Vuk", "Nair", "Feld", "Mori"]
    lasts = ["Cruz", "Hale", "Ito", "Berg", "Diaz", "Cole", "Ramos", "Wahl", "Singh", "Novak"]
    for i in range(max(0, n - 1)):
        a = random.choice(firsts) + " " + random.choice(lasts)
        b = random.choice(firsts) + " " + random.choice(lasts)
        aw, al = random.randint(2, 12), random.randint(0, 6)
        bw, bl = random.randint(2, 12), random.randint(0, 6)
        method = random.choice(["DEC", "KO", "SUB", "DEC"])
        winner = a if random.random() < 0.5 else b
        slot = "Prelim" if i < n - 2 else "Co-main"
        lines.append("%s  %s %s-%s  vs  %s %s-%s  → %s %s" % (
            slot, a, aw, al, b, bw, bl, winner.split()[-1], method))
    hab = getattr(main_opp, "habit", "") or ""
    lines.append("MAIN  YOU vs %s (%s) %s" % (main_opp.name, _rec(main_opp), hab))
    return lines


def scout_one_liner(opp) -> str:
    age = getattr(opp, "age", 24) or 24
    st = getattr(opp, "style", "MMA") or "MMA"
    hab = getattr(opp, "habit", "") or ""
    phy = getattr(opp, "physique_type", "") or ""
    bits = ["%s" % age, _rec(opp), str(st)]
    if hab:
        bits.append(hab)
    if phy:
        bits.append(phy)
    return ", ".join(bits)


def try_direct_ufc(fighter) -> bool:
    from . import orgs
    if last4_losses(fighter) >= 2:
        return False
    return random.random() < orgs.direct_ufc_chance(fighter)


def after_dwcs_win(fighter) -> None:
    """Legacy hook. Signing is owned by dwcs.resolve so a grind cannot sneak a contract."""
    return
