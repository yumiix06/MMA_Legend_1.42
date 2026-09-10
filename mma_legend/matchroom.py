"""The single booking entry point.

Fights could previously be booked from five places — `find_fight`,
`inbox_night`, `booker_night`, the competition week hook and no-gi night —
each with its own eligibility checks, its own purse handling and its own camp
logic. That is why a rule true on one screen was false on another: the manager
menu and the inbox could disagree about the same offer, and the manager menu
called `inbox_night(console, fighter, None)` with no fighter pool at all.

Everything routes through `book()` now. One gate, one sign-and-camp path, one
place to change how booking works.
"""
from __future__ import annotations


def gate(fighter) -> tuple:
    """(ok, reason). The single answer to 'can this fighter take a fight?'"""
    from .systems15 import can_compete

    why = can_compete(fighter)
    if why:
        return (False, why)
    try:
        from . import damage as _dmg
        ok, reason = _dmg.can_fight(fighter)
        if not ok:
            return (False, reason)
    except Exception:
        pass
    if int(getattr(fighter, "fight_cooldown", 0) or 0) > 0:
        return (False, "Recovery: %s week(s)." % fighter.fight_cooldown)
    if int(getattr(fighter, "camp_weeks_remaining", 0) or 0) > 0:
        booked = getattr(fighter, "booked_fight", None)
        if not isinstance(booked, dict):
            return (False, "In camp. Finish it before taking paper.")
    return (True, "")


def booked_status(fighter) -> dict:
    """What the player currently has on the books, or {}."""
    b = getattr(fighter, "booked_fight", None)
    if not isinstance(b, dict) or not b.get("date_week"):
        return {}
    week = int(getattr(fighter, "week", 0) or 0)
    date = int(b.get("date_week") or 0)
    return {
        "offer": b,
        "date_week": date,
        "weeks_out": max(0, date - week),
        "due": week >= date,
    }


def show_booked(console, fighter) -> None:
    """Fight-prep hub. Pure information: browsing it never spends the week."""
    from .systems15 import opp_label
    from .ui import status_strip

    st = booked_status(fighter)
    if not st:
        return
    b = st["offer"]
    while True:
        console.header("FIGHT PREP", str(b.get("event_name") or b.get("org") or "Booked fight"))
        status_strip(console, fighter)
        console.print("  vs %s · %s week%s out" % (opp_label(b), st["weeks_out"], "" if st["weeks_out"] == 1 else "s"))
        if b.get("title"): console.gold("  CHAMPIONSHIP FIGHT")
        console.print("  A) Fight overview / tale of tape")
        console.print("  B) Scouting report")
        console.print("  C) Weight / camp status")
        console.print("  D) Purse / contract")
        console.print("  X) Back")
        ch=(console.ask("Prep > ") or "X").strip().upper()
        if ch in ("X","0",""): return
        opp=b.get("opponent")
        if opp is None:
            snap=b.get("opponent_snap") or b.get("opponent_snapshot")
            if isinstance(snap,dict):
                try:
                    from .models import Fighter
                    opp=Fighter.from_dict(snap)
                except Exception:
                    opp=None
        if ch == "A":
            console.section("TALE OF THE TAPE")
            for who, tag in ((fighter,"YOU"),(opp,"OPP")):
                if who is None: continue
                rec=list(getattr(who,"pro_record",None) or getattr(who,"amateur_record",None) or [0,0,0])
                console.print("  %s %-20s %s-%s-%s"%(tag,getattr(who,"name","TBA"),rec[0],rec[1],rec[2]))
                console.print("      %scm · reach %scm · %s"%(int(getattr(who,"height",0) or 0),int(getattr(who,"reach",0) or 0),getattr(who,"stance","Orthodox")))
            console.print("  %s · fight week %s"%(b.get("weight_class") or getattr(fighter,"fight_weight_class",""),st["date_week"]))
        elif ch == "B":
            console.section("SCOUTING")
            if opp is None:
                console.print("  Opponent data is not available yet.")
            else:
                try:
                    from . import combat_intelligence as _ci
                    for line in _ci.scout_lines(fighter, opp):
                        console.print("  " + line.strip())
                    console.print("  Coach lean: %s" % _ci.coach_recommendation(fighter, opp))
                except Exception:
                    console.print("  Tape report unavailable.")
        elif ch == "C":
            console.section("CAMP / WEIGHT")
            camp=int(getattr(fighter,"camp_weeks_remaining",0) or 0)
            console.print("  Camp: %s · %sw left"%(getattr(fighter,"camp_focus",None) or "general",camp))
            try:
                from . import cut
                prog=cut.weight_campaign_summary(fighter)
                console.print("  Walk %.1fkg · target %.1fkg · limit %.1fkg"%(prog["current"],prog["target"],prog["limit"]))
                console.print("  Pace: %s · %.1fkg remaining before final cut"%(prog.get("pace","on track"),prog.get("remaining",0.0)))
            except Exception:
                console.print("  Walk %.1fkg"%float(getattr(fighter,"walking_weight",getattr(fighter,"weight",0)) or 0))
            console.print("  Nutrition is available from the weekly menu.",style="dim")
        elif ch == "D":
            console.section("MONEY / PAPER")
            console.print("  Offer: $%s show / $%s win"%(format(int(b.get("purse_show",b.get("show",0)) or 0),","),format(int(b.get("purse_win",b.get("win",0)) or 0),",")))
            deal=getattr(fighter,"org_contract",None)
            if isinstance(deal,dict):
                console.print("  Contract: %s · %s fight%s left"%(deal.get("org") or getattr(fighter,"organization",""),int(deal.get("fights_left",0) or 0),"" if int(deal.get("fights_left",0) or 0)==1 else "s"))
                clauses=list(deal.get("clauses") or [])
                if clauses: console.print("  Clauses: "+", ".join(str(x).replace("_"," ") for x in clauses))
            else:
                console.print("  No active promotional contract recorded.")
        else:
            console.warn("Invalid."); continue
        getattr(console,"continue_prompt",lambda *_a,**_k: None)("Press Enter to prep menu")

def sign_and_camp(console, fighter, offer: dict, pool=None) -> bool:
    """Take a date and open the camp that belongs to it.

    The only place a fight gets booked. Guarantees the date is in the future
    and that a camp exists for it.
    """
    from . import booking, career as _career, contracts, people

    org = str(offer.get("org") or "")
    allowed, reason = contracts.can_accept(fighter, org)
    if not allowed:
        console.warn(reason)
        console.pause(1.0)
        return False

    booking.set_booked(fighter, offer)
    date = int(fighter.booked_fight.get("date_week") or offer.get("date_week") or 0)
    weeks = max(1, date - int(getattr(fighter, "week", 0) or 0))
    _career.pick_and_start_camp(console, fighter, weeks)
    console.good("Signed for %s. Fight week %s — %s weeks of camp." % (org, date, weeks))
    try:
        people.warm_matchmaker(fighter, org or "LFA", 3)
        from . import memory as _mem, npc as _npc
        mm = people.matchmaker_for(org or "LFA")
        if mm is not None:
            _mem.remember(fighter, _npc.npc_id(mm), "accepted_offer", org)
    except Exception:
        pass
    try:
        from .cut import CLASS_LIMIT
        home = getattr(fighter, "fight_weight_class", None) or fighter.weight_class
        cap = float(CLASS_LIMIT.get(home, 0) or 0)
        walk = float(getattr(fighter, "walking_weight", fighter.weight) or fighter.weight)
        if cap and walk > cap:
            console.print("You need to be %.1fkg on the scale. Walking %.1fkg." % (cap, walk))
    except Exception:
        pass
    console.auto_pause("Signed")
    return True


def book(console, fighter, pool=None) -> None:
    """THE booking screen. Every menu route lands here."""
    from . import fights

    st = booked_status(fighter)
    if st:
        if st["due"]:
            fights.booker_night(console, fighter, pool)
        else:
            show_booked(console, fighter)
        return

    ok, why = gate(fighter)
    if not ok:
        console.warn(why)
        console.pause(0.9)
        return

    if getattr(fighter, "pro_debut", False):
        fights.inbox_night(console, fighter, pool)
    else:
        fights.find_fight(console, fighter, pool)
