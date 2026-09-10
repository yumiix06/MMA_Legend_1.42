"""Career identity.

Named promotion is the source of truth. Room is a matchmaking band.
PROMOTION_TIERS is a leftover label list and must not drive gameplay.
"""
from __future__ import annotations

from . import orgs

# Matchmaking band for each real promotion. Not a display string.
ORG_ROOM = {
    "UFC": "ufc",
    "PFL": "mid",
    "Bellator": "mid",
    "ONE Championship": "mid",
    "ONE": "mid",
    "Rizin FF": "mid",
    "BRAVE CF": "national",
    "KSW": "national",
    "ACA": "national",
    "Cage Warriors": "regional",
    "Balkan Combat": "regional",
    "LFA": "local",
    "Road FC": "regional",
    "ARES FC": "regional",
    "EFC": "regional",
    "DWCS": "dwcs",
    "Dana White Contender Series": "dwcs",
}

# Old room labels that used to be written into fighter.organization.
ROOM_LABELS = {
    "Local Fight Nights": "local",
    "Regional FC": "regional",
    "National MMA": "national",
    "Regional Major (Bellator/PFL-style)": "mid",
    "Contender Series (DWCS-style)": "dwcs",
    "Contender night (DWCS-style)": "dwcs",
    "UFC Championship": "ufc",
    "Amateur (Local)": "local",
    "National Amateur": "local",
    "European Amateur": "local",
    "IMMAF World": "local",
    "Pro (Local)": "local",
    "European Championship": "national",
    "Bellator": "mid",
    "ONE": "mid",
    "PFL": "mid",
    "Rizin": "mid",
    "UFC": "ufc",
}

FAKE_ORGS = set(ROOM_LABELS) | {
    "Free Agent", "Regional", "Local", "Showcase", "", None,
}


def is_named(org) -> bool:
    return bool(org) and org in orgs.ORGS


def band_for(org: str | None, fallback: str = "local") -> str:
    if org in ORG_ROOM:
        return ORG_ROOM[org]
    if org in ROOM_LABELS:
        return ROOM_LABELS[org]
    return fallback if fallback in ("local", "regional", "national", "mid", "dwcs", "ufc") else "local"


def canonical_org(fighter) -> str:
    """The promotion this fighter actually belongs to."""
    deal = getattr(fighter, "org_contract", None)
    if isinstance(deal, dict) and is_named(deal.get("org")):
        if int(deal.get("fights_left", 1) or 0) > 0:
            return deal["org"]
    org = getattr(fighter, "organization", None)
    if is_named(org):
        return org
    return ""


def display_org(fighter) -> str:
    org = canonical_org(fighter)
    if org:
        return org
    if getattr(fighter, "pro_debut", False):
        return "Free Agent"
    return "Amateur"


def set_band(fighter, room: str) -> None:
    """Change the matchmaking band. Never rename the promotion."""
    from . import booking
    room = room if room in booking.ROOMS else "local"
    fighter.room = room
    fighter.promotion_tier = booking.ROOMS[room]["tier"]
    org = canonical_org(fighter)
    if org:
        fighter.organization = org
    elif getattr(fighter, "organization", None) in FAKE_ORGS or getattr(fighter, "organization", None) in ROOM_LABELS:
        fighter.organization = None


def sync(fighter) -> str:
    """Reconcile org / room / tier / contract. Safe to call every week."""
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}
        flags = fighter.story_flags
    # Fame is a bounded 0-100 career visibility scale. Older paths could
    # grow it indefinitely while sponsor data stopped at 95.
    try:
        fighter.fame = max(0, min(100, int(getattr(fighter, "fame", 0) or 0)))
    except Exception:
        fighter.fame = 0

    deal = getattr(fighter, "org_contract", None)
    if isinstance(deal, dict) and "org" in deal and deal.get("org") in FAKE_ORGS:
        deal["org"] = ""
    # A named organization plus an exclusive contract with a blank org is a
    # corrupt free-agent state. 1.24 DWCS playtest hit exactly this: the UI
    # showed UFC, while contracts.active() saw no promotion and offered ACA,
    # KSW, LFA and Cage Warriors. Heal the contract toward the named org.
    named = getattr(fighter, "organization", None)
    if (isinstance(deal, dict) and deal.get("exclusive") is True
            and is_named(named) and not is_named(deal.get("org"))):
        deal["org"] = named
        deal["room"] = ORG_ROOM.get(named, getattr(fighter, "room", "regional") or "regional")
        deal.setdefault("exclusive", True)
        deal.setdefault("fights_left", 1)
        deal.setdefault("fights_total", deal.get("fights_left", 1))
        deal.setdefault("weeks_left", 78)

    org = canonical_org(fighter)
    if org:
        fighter.organization = org
        wanted = ORG_ROOM.get(org)
        if wanted:
            fighter.room = wanted
        spec = orgs.ORGS.get(org) or {}
        if spec.get("tier") is not None:
            fighter.promotion_tier = int(spec["tier"])
        flags["ufc_signed"] = org == "UFC"
    else:
        raw = getattr(fighter, "organization", None)
        if raw in ROOM_LABELS:
            fighter.room = ROOM_LABELS[raw]
            fighter.organization = None
        if not getattr(fighter, "room", None):
            fighter.room = "local" if getattr(fighter, "pro_debut", False) else ""
        flags["ufc_signed"] = False
    return display_org(fighter)


def premature_ufc(d: dict) -> bool:
    """Detect only obviously corrupted pre-UFC stamps on load.

    A legitimate DWCS graduate may have zero or one UFC bouts, so the old
    ``<3 UFC bouts`` repair wrongly kicked real signees back to a regional
    promotion.  Existing UFC history or a successful DWCS result is proof of
    a legitimate path.
    """
    flags = d.get("story_flags") if isinstance(d.get("story_flags"), dict) else {}
    rec = list(d.get("pro_record") or [0, 0, 0])
    hist = list(d.get("fight_history") or [])
    ufc_bouts = sum(1 for h in hist if "UFC" in str(h.get("event") or "").upper())
    dwcs_win = any(
        "DWCS" in str(h.get("event") or "").upper()
        and str(h.get("result") or "").upper().startswith("W")
        for h in hist
    )
    org = d.get("organization")
    contract = d.get("org_contract") if isinstance(d.get("org_contract"), dict) else {}
    stamped = org == "UFC" or flags.get("ufc_signed") or contract.get("org") == "UFC"
    if not stamped:
        return False
    if dwcs_win or int(rec[0] or 0) >= 6:
        return False
    # A lone UFC-labelled history row is not sufficient proof: older broken
    # saves stamped regional prospects into the UFC and also wrote that bout.
    return True


def repair_save(d: dict) -> dict:
    """Mutate a raw player/NPC dict on load so identity is coherent."""
    flags = d.get("story_flags") if isinstance(d.get("story_flags"), dict) else {}
    d["story_flags"] = flags
    try:
        from . import record as _rec
        d = _rec.repair_dict(d)
    except Exception:
        pass
    rec = list(d.get("pro_record") or [0, 0, 0])
    try:
        d["fame"] = max(0, min(100, int(d.get("fame") or 0)))
    except Exception:
        d["fame"] = 0
    org = d.get("organization")
    contract = d.get("org_contract") if isinstance(d.get("org_contract"), dict) else None
    if (is_named(org) and isinstance(contract, dict)
            and contract.get("exclusive") is True
            and not is_named(contract.get("org"))):
        contract["org"] = org
        contract["room"] = ORG_ROOM.get(org, d.get("room") or "regional")
        contract.setdefault("exclusive", True)
        contract.setdefault("fights_left", 1)
        contract.setdefault("fights_total", contract.get("fights_left", 1))
        contract.setdefault("weeks_left", 78)
        d["org_contract"] = contract
    old_belt = flags.get("org_belt")
    if old_belt and is_named(org) and old_belt != org:
        former = list(flags.get("former_belts") or [])
        if old_belt not in former:
            former.append(old_belt)
        flags["former_belts"] = former[-8:]
        flags["org_belt"] = None

    if premature_ufc(d):
        home = orgs.home_org(d.get("country") or "")
        d["organization"] = home
        d["room"] = ORG_ROOM.get(home, "regional")
        d["promotion_tier"] = int((orgs.ORGS.get(home) or {}).get("tier", 5))
        flags["ufc_signed"] = False
        flags["early_ufc_walked_back"] = True
        contract = d.get("org_contract")
        if isinstance(contract, dict) and contract.get("org") == "UFC":
            contract["org"] = home
            contract["room"] = d["room"]
            d["org_contract"] = contract
    elif org in ROOM_LABELS and org not in orgs.ORGS:
        band = ROOM_LABELS[org]
        d["room"] = band
        if d.get("pro_debut") and int(rec[0] or 0) >= 2:
            d["organization"] = orgs.home_org(d.get("country") or "")
        else:
            d["organization"] = None
    elif is_named(org):
        d["room"] = ORG_ROOM.get(org, d.get("room") or "regional")
        d["promotion_tier"] = int((orgs.ORGS.get(org) or {}).get("tier", d.get("promotion_tier") or 4))

    if d.get("education_stage") is not None:
        flags["graduated"] = bool(d.get("secondary_completed", False))
    elif d.get("school_status") in (None, "", "none") and int(d.get("age") or 16) >= 18:
        # Legacy/reference saves only. Fresh v1.40 careers use education_stage.
        flags["graduated"] = True
        if d.get("school_status") in (None, ""):
            d["school_status"] = "none"

    # Body: 5% bodyfat as a lifestyle is a bug, not a physique.
    phy = str(d.get("physique_type") or "Athletic")
    floor = {"Lean": 7.5, "Athletic": 9.5, "Stocky": 12.0, "Tall": 9.5,
             "Heavy-built": 12.0, "Compact": 9.0}.get(phy, 9.5)
    camp = bool(d.get("camp_active") or int(d.get("camp_for_bout") or 0) > 0)
    try:
        bf = float(d.get("bodyfat") or 12.0)
    except (TypeError, ValueError):
        bf = 12.0
    try:
        walk = float(d.get("walking_weight") or d.get("weight") or 70)
    except (TypeError, ValueError):
        walk = 70.0
    try:
        natural = float(d.get("natural_weight") or d.get("weight") or walk)
    except (TypeError, ValueError):
        natural = walk
    if not camp:
        if bf < floor:
            d["bodyfat"] = floor
        if walk < natural - 3:
            # one-shot fill so a crashed save does not stay a weight-cut ghost
            d["walking_weight"] = min(natural, walk + (natural - walk) * 0.45)
    else:
        d["bodyfat"] = max(6.5 if phy == "Heavy-built" else 5.5, bf)
    return d


def rank_line(fighter) -> str:
    flags = getattr(fighter, "story_flags", None) or {}
    org = canonical_org(fighter)
    n = flags.get("org_rank")
    wc = getattr(fighter, "weight_class", "") or ""
    # A belt from a previous promotion is history, not a championship in the
    # fighter's new promotion. UFC also owns a dedicated top-15 ranking; do
    # not let generic org_rank overwrite it.
    if flags.get("org_belt") == org and org:
        return "C %s %s" % (org, wc)
    if org == "UFC":
        ufc_n = flags.get("ufc_rank")
        if isinstance(ufc_n, int) and 1 <= ufc_n <= 15:
            return "UFC #%s %s" % (ufc_n, wc)
        return "UFC roster · unranked %s" % wc
    if org and isinstance(n, int) and 1 <= n <= 15:
        return "#%s %s %s" % (n, org, wc)
    if flags.get("org_belt"):
        return "C %s %s" % (org or flags.get("org_belt"), wc)
    if org:
        return "%s %s" % (org, wc)
    return ""


LADDER = (
    "LFA", "Balkan Combat", "Road FC", "ARES FC", "EFC",
    "Cage Warriors", "KSW", "BRAVE CF", "ACA", "PFL", "Bellator",
)


def purse_range(org_id: str | None) -> tuple | None:
    spec = orgs.ORGS.get(org_id or "")
    if spec and spec.get("purse"):
        return tuple(spec["purse"])
    return None


def next_org(fighter) -> str | None:
    """Where an NPC on a run should land next. Never UFC."""
    org = canonical_org(fighter)
    rec = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    w, l = int(rec[0]), int(rec[1])
    fame = int(getattr(fighter, "fame", 0) or 0)
    if not org:
        return orgs.home_org(getattr(fighter, "country", "") or "")
    if org == "UFC":
        return None
    if w < 5 or l > w:
        return None
    try:
        idx = LADDER.index(org)
    except ValueError:
        return LADDER[0]
    hop = 2 if (w >= 10 and fame >= 14) else 1
    nxt = LADDER[min(len(LADDER) - 1, idx + hop)]
    if nxt == org:
        return None
    if nxt in ("PFL", "Bellator") and (w < 10 or fame < 14):
        return None
    return nxt


def belt_key(org: str, wc: str) -> str:
    return "%s|%s" % (org, wc)


def promotion_history(fighter, org: str) -> list:
    """Return pro bouts belonging to one promotion.

    UFC-branded card labels such as ``UFC Fight Night`` count as UFC. DWCS
    never does. Centralising this prevents rankings and title eligibility from
    silently applying different résumé rules.
    """
    target = str(org or "").strip().upper()
    if not target:
        return []
    out = []
    for bout in (getattr(fighter, "fight_history", None) or []):
        event = str(bout.get("event") or "").strip().upper()
        same = event == target or event.startswith(target + " ")
        if same and bool(bout.get("pro", True)):
            out.append(bout)
    return out


def title_shot(fighter, pool) -> dict | None:
    """Return a real title opportunity, not merely a high hidden ranking.

    1.24 allowed a DWCS winner's *first* UFC bout to become a five-round title
    fight because generic ``org_rank`` could be #1 while the UFC-specific
    ranking was #7. Title eligibility now requires promotion-specific ranking
    plus a résumé inside that promotion.
    """
    if pool is None or not getattr(fighter, "pro_debut", False):
        return None
    org = canonical_org(fighter)
    if not org:
        return None
    wc = getattr(fighter, "weight_class", "") or ""
    if not wc:
        return None
    flags = getattr(fighter, "story_flags", None) or {}
    last = int(flags.get("title_offer_week") or 0)
    week = int(getattr(fighter, "week", 1) or 1)
    if last and week - last < 8:
        return None

    board = list(pool.get_org_top(org, wc, 15) or []) if hasattr(pool, "get_org_top") else []
    champ = pool.belt_holder(org, wc) if hasattr(pool, "belt_holder") else None
    me_id = getattr(fighter, "fid", None)
    def _is_me(f):
        return f is fighter or bool(me_id and getattr(f, "fid", None) == me_id)

    # A real multi-division champion can owe a defense in either class.  The
    # belt ledger decides which defense is most overdue instead of the
    # fighter's current home-weight field silently vacating/ignoring a belt.
    held = []
    for key, info in (getattr(pool, "belts", None) or {}).items():
        if not isinstance(info, dict) or info.get("fid") != me_id or str(info.get("org") or "") != org:
            continue
        bwc = str(info.get("wc") or (str(key).split("|", 1)[1] if "|" in str(key) else ""))
        if not bwc:
            continue
        last_def = int(info.get("last_defense_week", info.get("won_week", 0)) or 0)
        held.append((week - last_def, bwc, info))
    threshold = 16 if org == "UFC" else 20
    if len(held) >= 2:
        gap, due_wc, due_info = max(held, key=lambda row: row[0])
        if gap >= threshold:
            due_board = list(pool.get_org_top(org, due_wc, 15) or []) if hasattr(pool, "get_org_top") else []
            due_others = [f for f in due_board if not _is_me(f) and getattr(f, "active", True)]
            if due_others:
                return {"role": "defense", "org": org, "wc": due_wc, "opponent": due_others[0],
                        "multi_division": True}

    holds = bool(champ is not None and _is_me(champ)) or bool(flags.get("org_belt") == org)
    if org == "UFC":
        rank = flags.get("ufc_rank")
    else:
        rank = flags.get("org_rank")
    if not isinstance(rank, int):
        rank = None
        for i, f in enumerate(board, start=1):
            if _is_me(f):
                rank = i
                break

    others = [f for f in board if not _is_me(f) and getattr(f, "active", True)]
    if not others:
        bag = []
        for f in list(getattr(pool, "fighters", []) or []):
            if _is_me(f) or not getattr(f, "active", True) or not getattr(f, "pro_debut", False):
                continue
            if getattr(f, "weight_class", None) != wc:
                continue
            if canonical_org(f) == org:
                bag.append(f)
        others = bag

    if holds:
        # Champions defend on a realistic cadence instead of receiving a title
        # offer every time the inbox cooldown expires.
        from . import constants as _C
        belt_info = (getattr(pool, "belts", None) or {}).get(belt_key(org, wc), {})
        last_def = int(belt_info.get("last_defense_week", belt_info.get("won_week", 0)) or 0)
        due = week - last_def >= threshold
        # Established UFC champions may chase an adjacent belt after proving
        # the reign, provided their home belt is not already overdue.
        if not due and org == "UFC" and int(belt_info.get("defenses", 0) or 0) >= 2 and int(getattr(fighter, "fame", 0) or 0) >= 50:
            last_super = int(flags.get("last_superfight_week", 0) or 0)
            if not last_super or week - last_super >= 26:
                try:
                    idx = _C.WEIGHT_CLASSES.index(wc)
                except ValueError:
                    idx = -1
                targets = []
                if idx >= 0:
                    if idx + 1 < len(_C.WEIGHT_CLASSES): targets.append(_C.WEIGHT_CLASSES[idx + 1])
                    if idx - 1 >= 0: targets.append(_C.WEIGHT_CLASSES[idx - 1])
                for target_wc in targets:
                    target_champ = pool.belt_holder(org, target_wc) if hasattr(pool, "belt_holder") else None
                    if target_champ is not None and not _is_me(target_champ):
                        flags["last_superfight_week"] = week
                        return {"role": "double_champ", "org": org, "wc": target_wc,
                                "opponent": target_champ, "superfight": True}
        if not due:
            return None
        opp = others[0] if others else None
        if opp is None and pool is not None:
            try:
                from . import booking
                opp = booking.pick_pool_opponent(fighter, pool, band_for(org, getattr(fighter, "room", "regional")), org)
            except Exception:
                opp = None
        return {"role": "defense", "org": org, "wc": wc, "opponent": opp} if opp else None

    # Promotion-specific résumé. DWCS is not a UFC bout.
    hist = promotion_history(fighter, org)
    org_wins = sum(1 for h in hist if str(h.get("result") or "").lower().startswith("w"))
    org_losses = sum(1 for h in hist if str(h.get("result") or "").lower().startswith("l"))
    streak = int(getattr(fighter, "current_streak", 0) or 0)
    recent = list(getattr(fighter, "recent_results", None) or [])
    last_result = str(recent[-1] if recent else "").upper()

    if org == "UFC":
        # Normal path: establish yourself, enter the real top three, then earn
        # the shot. A recent loss can never immediately generate another one.
        if rank is None or rank > 3 or len(hist) < 3 or org_wins < 2:
            return None
        if streak < 2 or last_result.startswith("L"):
            return None
    else:
        # Regional belts arrive faster. A proven veteran (8+ career pro wins)
        # may arrive as the promotion's #1 and challenge immediately; normal
        # prospects still need two wins inside the promotion. UFC never uses
        # this shortcut.
        career_pro_wins = int((getattr(fighter, "pro_record", None) or [0])[0] or 0)
        veteran_shortcut = bool(rank == 1 and career_pro_wins >= 8 and not last_result.startswith("L"))
        if not veteran_shortcut:
            if rank is None or rank > 2 or len(hist) < 2 or org_wins < 2:
                return None
            if last_result.startswith("L") and org_losses:
                return None

    if champ is not None and not _is_me(champ):
        return {"role": "challenger", "org": org, "wc": wc, "opponent": champ}
    if others:
        return {"role": "inaugural", "org": org, "wc": wc, "opponent": others[0]}
    return None
