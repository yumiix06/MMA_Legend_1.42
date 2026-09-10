"""Promotional contracts (1.9).

Before this module, signing with an organisation set `fighter.organization` and
nothing else. There was no contract record, so `systems17.contract_locked()`
found nothing to enforce and a "signed" fighter could take a date from any
promotion on the board. Contracts now have a real shape:

    org           who you are signed to
    fights_left   bouts still owed on the deal
    weeks_left    calendar term; a deal can expire before it is fought out
    signed_week   when it started
    purse_win / purse_show   the money terms you negotiated
    exclusive     True for every real deal

Exclusivity is enforced in one place, `can_accept()`, which every booking path
calls. The single carve-out is the UFC feeder: a fighter under a regional deal
may take a Contender Series date, because that is how the real ladder works.
"""
from __future__ import annotations

import random

# The Contender Series is a feeder, not a competitor. A regional promotion
# will let a fighter take that call.
FEEDER_ORGS = frozenset({"DWCS", "Dana White Contender Series", "Contender Series"})

# Default deal shapes by tier of promotion.
DEFAULT_TERMS = {
    "local": (3, 52),
    "regional": (4, 78),
    "national": (4, 78),
    "mid": (5, 104),
    "dwcs": (1, 26),
    "ufc": (6, 130),
}


def ensure(fighter) -> dict:
    c = getattr(fighter, "org_contract", None)
    if not isinstance(c, dict):
        c = {}
        fighter.org_contract = c
    return c


def active(fighter) -> dict | None:
    """The live contract, or None if the fighter is a free agent.

    Contracts written before 1.9 have no `weeks_left`/`fights_total`. They are
    migrated in place here rather than being read as expired, so a 1.7/1.8
    save keeps its deal instead of silently turning the fighter into a free
    agent on load.
    """
    c = getattr(fighter, "org_contract", None)
    if isinstance(c, dict) and not c.get("org"):
        # Runtime repair for 1.24 DWCS saves: the visible organization could be
        # UFC while a blank contract made the fighter a free agent.
        try:
            from . import identity
            org = getattr(fighter, "organization", None)
            # Only repair the known corrupt-save shape: it was an explicitly
            # exclusive deal whose org field was lost.  An empty dict is the
            # intentional representation of a released/free-agent fighter and
            # must never be grown back into a contract.
            if identity.is_named(org) and c.get("exclusive") is True:
                c["org"] = org
                c["room"] = identity.band_for(org, c.get("room") or getattr(fighter, "room", "regional"))
                c.setdefault("fights_left", 1)
                c.setdefault("fights_total", c.get("fights_left", 1))
                c.setdefault("weeks_left", 78)
        except Exception:
            pass
    if not isinstance(c, dict) or not c.get("org"):
        return None
    c.setdefault("fights_left", 1)
    c.setdefault("fights_total", c.get("fights_left", 1))
    c.setdefault("exclusive", True)
    c.setdefault("clauses", [])
    if "weeks_left" not in c:
        # Legacy deal: give it a standard remaining term.
        room = c.get("room") or "regional"
        c["weeks_left"] = DEFAULT_TERMS.get(room, (4, 78))[1]
    if int(c.get("fights_left", 0) or 0) <= 0:
        return None
    if int(c.get("weeks_left", 0) or 0) <= 0:
        return None
    return c


def sign(fighter, org: str, fights: int | None = None, weeks: int | None = None,
         purse_win: int = 0, purse_show: int = 0, room: str | None = None,
         exclusive: bool = True, clauses: list | None = None) -> dict:
    """Put the fighter under a real promotional deal.

    v1.30 supports negotiated exclusivity and small named clauses.  The shape
    remains plain JSON so old saves migrate without a special object model.
    """
    from . import booking
    org = str(org or "").strip()
    if not org:
        raise ValueError("contract organization cannot be blank")
    room = room or booking.current_room(fighter)
    d_fights, d_weeks = DEFAULT_TERMS.get(room, (4, 78))
    contract = {
        "org": org,
        "fights_left": int(fights or d_fights),
        "fights_total": int(fights or d_fights),
        "weeks_left": int(weeks or d_weeks),
        "signed_week": int(getattr(fighter, "week", 1) or 1),
        "purse_win": int(purse_win or 0),
        "purse_show": int(purse_show or 0),
        "exclusive": bool(exclusive),
        "clauses": list(dict.fromkeys(str(x) for x in (clauses or []) if x)),
        "room": room,
    }
    fighter.org_contract = contract
    fighter.organization = org
    return contract


def release(fighter, reason: str = "expired") -> str:
    c = getattr(fighter, "org_contract", None) or {}
    org = c.get("org") or getattr(fighter, "organization", "") or "your promotion"
    fighter.org_contract = {}
    # A released fighter is a free agent in both contract and identity state.
    # Leaving organization populated allowed identity.sync() to reconstruct
    # the contract on the following weekly tick/load.
    fighter.organization = None
    flags = getattr(fighter, "story_flags", None)
    if isinstance(flags, dict):
        flags["org_rank"] = None
        flags["org_board"] = None
        flags["ufc_rank"] = None
        flags["ufc_signed"] = False
        flags["title_offer_week"] = 0
        flags["last_release"] = {"org": org, "reason": reason,
                                 "week": int(getattr(fighter, "week", 0) or 0)}
    return "%s deal with %s is over (%s). You are a free agent." % (
        "Your", org, reason)


def can_accept(fighter, org: str) -> tuple:
    """(allowed, reason). The single gate every booking path must use."""
    org = str(org or "")
    c = active(fighter)
    if not c:
        return (True, "")
    home = str(c.get("org") or "")
    if org == home:
        return (True, "")
    if not bool(c.get("exclusive", True)):
        return (True, "Your current contract is non-exclusive.")
    if org in FEEDER_ORGS and home != "UFC":
        return (True, "Contender Series is a permitted feeder — your promotion allows it.")
    return (False, "You are signed to %s for %s more fight(s). Taking a %s date is a breach." % (
        home, c.get("fights_left"), org))


def note_fight(fighter, console=None) -> str:
    """Burn one fight off the deal. Call after every pro bout."""
    c = getattr(fighter, "org_contract", None)
    if not isinstance(c, dict) or not c.get("org"):
        return ""
    left = int(c.get("fights_left", 0) or 0) - 1
    c["fights_left"] = max(0, left)
    if left <= 0:
        queue_renewal(fighter)
        msg = "Last fight on the %s deal. They will want to talk terms." % c.get("org")
        if console:
            console.gold(msg)
        return msg
    if console and left <= 1:
        console.info("%s fight left on the %s deal." % (left, c.get("org")))
    return ""


def tick(fighter, console=None) -> None:
    """Weekly: run down the calendar term and expire dead deals."""
    c = getattr(fighter, "org_contract", None)
    if not isinstance(c, dict) or not c.get("org"):
        return
    weeks = int(c.get("weeks_left", 0) or 0)
    if weeks > 0:
        c["weeks_left"] = weeks - 1
    fights_left = int(c.get("fights_left", 0) or 0)
    if c["weeks_left"] <= 0 or fights_left <= 0:
        # Do not silently dump a champ / starter. Queue paper first.
        queued = queue_renewal(fighter)
        if c["weeks_left"] <= 0 and not queued:
            msg = release(fighter, "term expired")
            if console:
                console.warn(msg)
        elif console and queued:
            console.info("%s wants to talk a new deal." % c.get("org"))


def offer_renewal(fighter, org: str | None = None) -> dict:
    """Terms the promotion would put in front of the fighter now."""
    from . import booking
    from . import orgs
    org = org or (getattr(fighter, "org_contract", None) or {}).get("org") \
        or getattr(fighter, "organization", "") or "LFA"
    room = booking.current_room(fighter)
    win, show = booking.purse_for(fighter, room)
    dom = 0.0
    try:
        dom = orgs.dominance(fighter)
    except Exception:
        pass
    # Winning gets you a better deal. Losing gets you a shorter one.
    mult = 1.0 + min(0.6, max(0.0, dom - 10) * 0.03)
    fights, weeks = DEFAULT_TERMS.get(room, (4, 78))
    if dom >= 22:
        fights += 1
    current = active(fighter) or {}
    return {
        "org": org,
        "fights": fights,
        "weeks": weeks,
        "purse_win": int(win * mult),
        "purse_show": int(show * mult),
        "room": room,
        "exclusive": bool(current.get("exclusive", True)),
        "clauses": list(current.get("clauses") or []),
    }


def queue_renewal(fighter) -> dict | None:
    """One pending re-sign. Does not drop organization."""
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}
        flags = fighter.story_flags
    if isinstance(flags.get("pending_renewal"), dict):
        return flags["pending_renewal"]
    org = (getattr(fighter, "org_contract", None) or {}).get("org") \
        or getattr(fighter, "organization", "") or ""
    if not org:
        return None
    terms = offer_renewal(fighter, org)
    flags["pending_renewal"] = terms
    return terms


def accept_renewal(fighter) -> str:
    flags = getattr(fighter, "story_flags", None) or {}
    terms = flags.get("pending_renewal")
    if not isinstance(terms, dict):
        return "No deal on the table."
    sign(fighter, terms.get("org") or fighter.organization,
         fights=terms.get("fights"), weeks=terms.get("weeks"),
         purse_win=terms.get("purse_win") or 0,
         purse_show=terms.get("purse_show") or 0,
         room=terms.get("room"), exclusive=terms.get("exclusive", True),
         clauses=terms.get("clauses") or [])
    flags["pending_renewal"] = None
    from . import identity
    identity.sync(fighter)
    return "Re-signed with %s · %s fights · %sw." % (
        terms.get("org"), terms.get("fights"), terms.get("weeks"))


def decline_renewal(fighter) -> str:
    flags = getattr(fighter, "story_flags", None) or {}
    terms = flags.get("pending_renewal") if isinstance(flags, dict) else None
    org = (terms or {}).get("org") if isinstance(terms, dict) else ""
    if isinstance(flags, dict):
        flags["pending_renewal"] = None
    return release(fighter, "declined renewal")


def negotiate(fighter, terms: dict, ask: str = "money") -> tuple:
    """Negotiate contract structure, not just a one-fight purse.

    Manager competency, personality, relationship, résumé leverage and the
    promoter's remembered history all contribute.  Requests are deliberately
    modest so negotiation adds agency without becoming a money exploit.
    """
    from . import people
    terms = dict(terms or {})
    terms.setdefault("exclusive", True)
    terms["clauses"] = list(terms.get("clauses") or [])
    mgr = people.current_manager(fighter)
    rapport = people.rapport(fighter, mgr.id) if mgr else 50
    skill = int(getattr(mgr, "negotiation", 35 if not mgr else 50) or 50) if mgr else 25
    quirk = getattr(mgr, "quirk", "") if mgr else ""
    try:
        from . import orgs
        leverage = float(orgs.dominance(fighter) or 0.0)
    except Exception:
        leverage = 0.0
    promoter = people.promoter_for(str(terms.get("org") or getattr(fighter, "organization", "") or ""))
    mem = 0
    if promoter:
        try:
            from . import memory
            mem = memory.score(fighter, promoter.id)
        except Exception:
            mem = 0
    chance = 0.14 + skill / 170.0 + (rapport - 50) / 320.0
    chance += min(0.18, max(0.0, leverage - 8) * 0.008) + mem / 120.0
    if quirk == "aggressive": chance += 0.06
    if ask == "nonexclusive":
        chance -= 0.18
        # Top promotions sell exclusivity as part of the product.  A manager
        # can negotiate money/clauses there, not permission to fight rivals.
        if str(terms.get("org") or "") in ("UFC", "PFL", "Bellator"):
            return False, terms, "%s will not offer a non-exclusive contract." % terms.get("org")
    chance = max(0.08, min(0.90, chance))
    if random.random() > chance:
        if promoter:
            try:
                from . import memory
                memory.remember(fighter, promoter.id, "hard_negotiation", ask)
            except Exception:
                pass
        return False, terms, "They will not move on %s. Terms stand." % ask.replace("_", " ")

    if ask == "fights":
        terms["fights"] = max(1, int(terms.get("fights", 4) or 4) - 1)
        line = "They trimmed it to %s fights." % terms["fights"]
    elif ask == "term":
        terms["weeks"] = max(26, int(terms.get("weeks", 78) or 78) - 26)
        line = "Term cut to %s weeks." % terms["weeks"]
    elif ask == "nonexclusive":
        terms["exclusive"] = False
        line = "They agree to a non-exclusive deal. Outside dates are now possible."
    elif ask in ("short_notice", "title_escalator"):
        clause = ask
        if clause not in terms["clauses"]:
            terms["clauses"].append(clause)
        label = "25% short-notice premium" if ask == "short_notice" else "title-fight purse escalator"
        line = "Clause added: %s." % label
    else:
        bump = 1.10 + max(0, skill - 50) / 500.0 + random.random() * 0.10
        terms["purse_win"] = int(int(terms.get("purse_win", 0) or 0) * bump)
        terms["purse_show"] = int(int(terms.get("purse_show", 0) or 0) * bump)
        line = "Purse moved to $%s win / $%s show." % (terms["purse_win"], terms["purse_show"])
    if promoter:
        try:
            from . import memory
            memory.remember(fighter, promoter.id, "professional_negotiation", ask)
        except Exception:
            pass
    if mgr:
        try: people.adjust_rapport(fighter, mgr.id, 1)
        except Exception: pass
    return True, terms, line


def apply_offer_clauses(fighter, offer: dict) -> dict:
    """Apply negotiated contract clauses to a concrete bout offer once."""
    out = dict(offer or {})
    c = active(fighter) or {}
    clauses = set(c.get("clauses") or [])
    if out.get("short_notice") and "short_notice" in clauses and not out.get("_short_clause_applied"):
        out["purse_win"] = int(int(out.get("purse_win", 0) or 0) * 1.25)
        out["purse_show"] = int(int(out.get("purse_show", 0) or 0) * 1.25)
        out["_short_clause_applied"] = True
    if out.get("title") and "title_escalator" in clauses and not out.get("_title_clause_applied"):
        out["purse_win"] = int(int(out.get("purse_win", 0) or 0) * 1.20)
        out["purse_show"] = int(int(out.get("purse_show", 0) or 0) * 1.20)
        out["_title_clause_applied"] = True
    return out


def line(fighter) -> str:
    """One-line dashboard summary."""
    c = active(fighter)
    if not c:
        return "Free agent"
    lock = "exclusive" if c.get("exclusive", True) else "non-exclusive"
    clauses = list(c.get("clauses") or [])
    tail = (" · " + ", ".join(x.replace("_", " ") for x in clauses)) if clauses else ""
    return "%s · %s fight(s) left · %sw · %s%s" % (
        c.get("org"), c.get("fights_left"), c.get("weeks_left"), lock, tail)
