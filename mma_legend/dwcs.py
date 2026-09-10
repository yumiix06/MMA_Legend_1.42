"""The Contender Series door (1.10).

Before this module, "DWCS" was just a room the booker quietly moved you into,
and any win there signed you to the UFC automatically. That is not how the
Contender Series works, and it removed the one moment on the ladder that is
supposed to feel like a test.

The real shape, and now the game's shape:

  1. You have to be **invited**. Invitations go to fighters on a real run at
     regional/national level, and they are not guaranteed.
  2. It is a **one-off**, outside your promotional contract. Your promotion
     allows it because it is a feeder, not a competitor.
  3. **Winning is not enough.** A grinding decision gets you a handshake and a
     "come back and show us more". A finish, or a dominant performance,
     gets the contract. You can win and walk away with nothing, which is the
     entire point of the show.
  4. Losing sends you back to the regional scene, not out of the sport.
"""
from __future__ import annotations

import random

INVITE_FLAG = "dwcs_invite"
DONE_FLAG = "dwcs_appearances"
CONTRACT_FLAG = "ufc_signed"

ORG_NAME = "DWCS"


def _flags(fighter) -> dict:
    f = getattr(fighter, "story_flags", None)
    if not isinstance(f, dict):
        fighter.story_flags = {}
        f = fighter.story_flags
    return f


def appearances(fighter) -> int:
    return int(_flags(fighter).get(DONE_FLAG, 0) or 0)


def win_streak(fighter) -> int:
    n = 0
    for x in reversed(list(getattr(fighter, "recent_results", None) or [])):
        if str(x).upper().startswith("W"):
            n += 1
        else:
            break
    return n


def eligible(fighter) -> tuple:
    """(ok, reason). What it takes to get the call."""
    if not getattr(fighter, "pro_debut", False):
        return (False, "Amateurs do not get the call.")
    if (getattr(fighter, "organization", "") or "") == "UFC":
        return (False, "You are already in the UFC.")
    if _flags(fighter).get(CONTRACT_FLAG):
        return (False, "You already earned your contract.")
    rec = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    wins, losses = int(rec[0]), int(rec[1])
    if wins < 6:
        return (False, "Need at least 6 pro wins. You have %s." % wins)
    if win_streak(fighter) < 3:
        return (False, "They want a live streak — 3 straight. You have %s." % win_streak(fighter))
    if losses > wins:
        return (False, "Losing record. Build it back up first.")
    if int(getattr(fighter, "fame", 0) or 0) < 10:
        return (False, "Nobody has heard of you yet. Fame 10+ gets you scouted.")
    if appearances(fighter) >= 2:
        return (False, "You have had your looks on the show.")
    return (True, "")


def invite_chance(fighter) -> float:
    ok, _why = eligible(fighter)
    if not ok:
        return 0.0
    rec = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    fame = int(getattr(fighter, "fame", 0) or 0)
    base = 0.10 + min(0.20, (int(rec[0]) - 5) * 0.03)
    base += min(0.12, max(0, fame - 10) * 0.005)
    base += min(0.10, (win_streak(fighter) - 3) * 0.03)
    # Finishes get you noticed far more than decisions.
    finishes = sum(
        1 for h in (getattr(fighter, "fight_history", None) or [])
        if h.get("result") == "Win" and h.get("method") in ("KO", "TKO", "Submission")
    )
    base += min(0.12, finishes * 0.02)
    if getattr(fighter, "manager_id", None) or getattr(fighter, "manager", None):
        base += 0.04
    return max(0.0, min(0.40, base))


def has_invite(fighter) -> bool:
    return bool(_flags(fighter).get(INVITE_FLAG))


def maybe_invite(fighter, console=None) -> bool:
    """Weekly roll. Returns True if an invitation just landed."""
    if has_invite(fighter):
        return False
    if random.random() >= invite_chance(fighter):
        return False
    _flags(fighter)[INVITE_FLAG] = {
        "week": int(getattr(fighter, "week", 0) or 0),
        "expires": int(getattr(fighter, "week", 0) or 0) + 8,
    }
    if console:
        console.milestone("CONTENDER SERIES CALL")
        console.print("A matchmaker for the Contender Series has been watching your run.")
        console.print("One fight. Win well enough and you leave with a UFC contract.")
        console.print("Win badly and you go home with a handshake.")
    return True


def invite_expired(fighter) -> bool:
    inv = _flags(fighter).get(INVITE_FLAG)
    if not isinstance(inv, dict):
        return False
    return int(getattr(fighter, "week", 0) or 0) > int(inv.get("expires", 0) or 0)


def clear_invite(fighter) -> None:
    _flags(fighter).pop(INVITE_FLAG, None)


def tick(fighter, console=None) -> None:
    """Weekly hook: expire a stale invitation, else try to generate one."""
    if has_invite(fighter):
        if invite_expired(fighter):
            clear_invite(fighter)
            if console:
                console.warn("The Contender Series window closed. They move on fast.")
        return
    maybe_invite(fighter, console)


def grade(outcome) -> tuple:
    """Judge a Contender Series performance.

    Returns (earned_contract, grade_label, why).
    """
    if outcome is None:
        return (False, "no result", "No result recorded.")
    if getattr(outcome, "winner", "") != "player":
        return (False, "loss", "You lost. That is the end of this look.")

    finish = getattr(outcome, "finish_label", None)
    method = str(getattr(outcome, "method", "") or "")
    fs = getattr(outcome, "f_stats", None)
    os_ = getattr(outcome, "o_stats", None)
    end_period = int(getattr(outcome, "end_period", 3) or 3)

    if finish and method in ("KO", "TKO", "Submission"):
        if end_period <= 2:
            return (True, "statement finish",
                    "You finished it inside two rounds. That is exactly what they buy.")
        return (True, "finish", "A finish is a finish. They are sold.")

    # A decision has to be a dominant one.
    dominance = 0
    if fs is not None and os_ is not None:
        if fs.knockdowns > os_.knockdowns:
            dominance += 2
        if fs.strikes_landed > os_.strikes_landed * 1.6:
            dominance += 2
        elif fs.strikes_landed > os_.strikes_landed * 1.2:
            dominance += 1
        if fs.takedowns_landed > os_.takedowns_landed + 1:
            dominance += 1
        if fs.control_ticks > os_.control_ticks * 1.5:
            dominance += 1
        if fs.submission_attempts >= 2:
            dominance += 1
        if os_.knockdowns > 0:
            dominance -= 1
    if dominance >= 4:
        return (True, "dominant decision",
                "You never gave him a round. They will take that.")
    if dominance >= 2:
        return (False, "clear decision",
                "A clear win, but they wanted you to take it from him. "
                "They said come back and show them more.")
    return (False, "grinding decision",
            "You won the fight and lost the room. They are not signing a "
            "grind. Go win one impressively and call again.")


def resolve(fighter, outcome, console=None) -> bool:
    """Apply the result of a Contender Series bout. True if signed."""
    flags = _flags(fighter)
    flags[DONE_FLAG] = appearances(fighter) + 1
    clear_invite(fighter)
    earned, label, why = grade(outcome)

    if console:
        console.section("CONTENDER SERIES VERDICT")
        console.print("Performance: %s" % label)
        console.print(why)

    if earned:
        accept = True
        if console is not None:
            home = getattr(fighter, "organization", "") or "the regional scene"
            console.print("Dana wants to sign you. This is a real UFC contract.")
            if home and home not in ("UFC", "DWCS", "Dana White Contender Series"):
                console.print("You are still with %s. Accepting means they cut you loose." % home)
            raw = (console.ask("Take the UFC deal? A yes / B stay where you are > ") or "A").strip().upper()
            accept = raw == "A"
        if not accept:
            from .notoriety import add_fame
            add_fame(fighter, 5, "DWCS contract performance")
            if console:
                console.info("You turn them down. The regional deal stays.")
            return False
        flags[CONTRACT_FLAG] = True
        try:
            from . import orgs
            orgs.sign_org(fighter, "UFC")
        except Exception:
            pass
        from .notoriety import add_fame
        add_fame(fighter, 8, "DWCS breakout")
        if console:
            console.milestone("UFC CONTRACT EARNED")
            console.print("You are on the roster. The matchmaker takes it from here.")
        return True

    # No contract. Back to the regional scene, but you were on the show.
    from .notoriety import add_fame
    add_fame(fighter, 3 if label != "loss" else 1, "DWCS appearance")
    try:
        from . import booking
        if booking.current_room(fighter) == "dwcs":
            booking.set_room(fighter, "national")
    except Exception:
        pass
    if console:
        left = 2 - appearances(fighter)
        if left > 0:
            console.info("You can earn another look. %s left." % left)
        else:
            console.warn("That was your last look at the Contender Series.")
    return False


def status_line(fighter) -> str:
    """Dashboard line."""
    if _flags(fighter).get(CONTRACT_FLAG):
        return ""
    if has_invite(fighter):
        inv = _flags(fighter).get(INVITE_FLAG) or {}
        left = int(inv.get("expires", 0) or 0) - int(getattr(fighter, "week", 0) or 0)
        return "CONTENDER SERIES INVITE — %sw to accept" % max(0, left)
    ok, why = eligible(fighter)
    if ok:
        return "Contender Series: being scouted"
    return ""
