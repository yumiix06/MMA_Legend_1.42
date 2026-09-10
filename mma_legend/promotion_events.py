"""Persistent promotion calendars, cards and short-notice replacements."""
from __future__ import annotations

import random
import re

from . import orgs as ORG_DATA


CADENCE = {"UFC": 3, "PFL": 6, "Bellator": 5, "BRAVE CF": 7, "KSW": 6,
           "Cage Warriors": 6, "Balkan Combat": 8, "LFA": 6, "Road FC": 7,
           "ARES FC": 7, "ACA": 6, "EFC": 8}
LOCATIONS = {
    "UFC": ("Las Vegas", "New York", "London", "Abu Dhabi"),
    "PFL": ("Chicago", "New York", "Riyadh"), "Bellator": ("Dublin", "Paris", "Chicago"),
    "KSW": ("Warsaw", "Krakow"), "Balkan Combat": ("Sofia", "Belgrade", "Bucharest"),
    "Cage Warriors": ("London", "Manchester", "Dublin"), "LFA": ("Denver", "Dallas", "Phoenix"),
    "BRAVE CF": ("Manama", "Dubai"), "Road FC": ("Seoul", "Tokyo"),
    "ARES FC": ("Paris", "Lyon"), "ACA": ("Moscow", "Almaty"), "EFC": ("Cape Town", "Lagos"),
}


def ensure(pool) -> None:
    if not isinstance(getattr(pool, "events", None), list):
        pool.events = []
    if not isinstance(getattr(pool, "event_history", None), list):
        pool.event_history = []
    if not isinstance(getattr(pool, "title_history", None), list):
        pool.title_history = []
    if not isinstance(getattr(pool, "matchup_history", None), dict):
        pool.matchup_history = {}
    if not isinstance(getattr(pool, "matchup_lifetime", None), dict):
        pool.matchup_lifetime = {}
    pool.next_event_id = max(1, int(getattr(pool, "next_event_id", 1) or 1))
    if not isinstance(getattr(pool, "event_counters", None), dict):
        pool.event_counters = {}
    _label_legacy_cards(pool)


def _counter_row(pool, org: str) -> dict:
    counters = getattr(pool, "event_counters", None)
    if not isinstance(counters, dict):
        pool.event_counters = {}
        counters = pool.event_counters
    row = counters.setdefault(str(org), {"numbered": 0, "fight_night": 0})
    if not isinstance(row, dict):
        row = {"numbered": 0, "fight_night": 0}; counters[str(org)] = row
    row.setdefault("numbered", 0); row.setdefault("fight_night", 0)
    return row


def _identity(pool, org: str, numbered: bool) -> tuple[str, str, int]:
    row = _counter_row(pool, org)
    series = "numbered" if numbered else "fight_night"
    row[series] = int(row.get(series, 0) or 0) + 1
    n = int(row[series])
    name = "%s %s" % (org, n) if numbered else "%s Fight Night %s" % (org, n)
    return name, series, n


def _label_legacy_cards(pool) -> None:
    """Give pre-1.32 scheduled/history cards stable series identities once."""
    cards = list(getattr(pool, "event_history", None) or []) + list(getattr(pool, "events", None) or [])
    # First absorb counters from already-labelled cards (including loaded 1.32 saves).
    for ev in cards:
        org = str(ev.get("org") or "")
        if not org or not ev.get("event_name"):
            continue
        series = str(ev.get("series") or ("fight_night" if "Fight Night" in str(ev.get("event_name")) else "numbered"))
        try:
            n = int(ev.get("number") or re.findall(r"(\d+)$", str(ev.get("event_name")))[-1])
        except Exception:
            continue
        row = _counter_row(pool, org)
        row[series] = max(int(row.get(series, 0) or 0), n)
    # Then migrate only unnamed cards. Chronological order keeps numbering intuitive.
    for ev in sorted(cards, key=lambda x: (int(x.get("week", 0) or 0), str(x.get("id") or ""))):
        if ev.get("event_name"):
            continue
        org = str(ev.get("org") or "")
        if not org:
            continue
        numbered = any(bool(b.get("title")) for b in (ev.get("bouts") or []))
        name, series, n = _identity(pool, org, numbered)
        ev["event_name"] = name; ev["series"] = series; ev["number"] = n


def event_label(pool, event_id: str) -> str:
    ensure(pool)
    ev = next((x for x in list(pool.events or []) + list(pool.event_history or []) if x.get("id") == event_id), None)
    if not ev:
        return ""
    return str(ev.get("event_name") or ev.get("org") or "")


def _open_ids(pool) -> set[str]:
    out = set()
    for ev in pool.events:
        if ev.get("status") != "scheduled":
            continue
        for bout in ev.get("bouts", []):
            if bout.get("status") != "scheduled":
                continue
            out.update(x for x in (bout.get("red_id"), bout.get("blue_id")) if x)
    return out


def _pair_key(a_id: str, b_id: str) -> str:
    return "|".join(sorted((str(a_id), str(b_id))))


def _meeting_count(pool, a_id: str, b_id: str) -> int:
    """Lifetime meetings for the hard trilogy ceiling.

    `matchup_history` is intentionally a recent five-season tactical memory and
    may be pruned. `matchup_lifetime` is tiny sparse metadata that never forgets
    a completed pairing, so a fourth fight cannot leak through years later.
    """
    key = _pair_key(a_id, b_id)
    lifetime = getattr(pool, "matchup_lifetime", None) or {}
    recent = getattr(pool, "matchup_history", None) or {}
    try:
        life_n = int(lifetime.get(key, 0) or 0) if isinstance(lifetime, dict) else 0
    except (TypeError, ValueError):
        life_n = 0
    try:
        recent_n = int((recent.get(key) or {}).get("count", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        recent_n = 0
    # max() also gives older v16 saves a safe migration path: their recent
    # table can seed the lifetime count without ever lowering known meetings.
    return max(life_n, recent_n)


def _record_shape(f):
    r=list(getattr(f,"pro_record",[0,0,0]) or [0,0,0]); w,l,d=(r+[0,0,0])[:3]
    bouts=w+l+d; rate=(w/max(1,bouts))
    return w,l,d,bouts,rate

def _rank_pos(pool, org, wc, fighter) -> int:
    board=list(pool.get_org_top(org,wc,30) or [])
    try: return board.index(fighter)+1
    except ValueError: return 99

def _career_role(pool, org, wc, f) -> str:
    w,l,d,bouts,rate=_record_shape(f); rank=_rank_pos(pool,org,wc,f); streak=int(getattr(f,"current_streak",0) or 0)
    if pool.belt_holder(org,wc) is f: return "champion"
    if rank <= 5 and w >= 4 and streak >= 1: return "contender"
    if bouts <= 8 and int(getattr(f,"age",30) or 30) <= 30 and rate >= .55 and streak >= 1: return "prospect"
    if bouts >= 10 and .35 <= rate <= .70: return "gatekeeper"
    if streak <= -2 and bouts >= 5: return "rebuild"
    if bouts >= 8 and l >= w + 3: return "journeyman"
    return "roster"

def _pair_cost(pool, a, b, week: int, intent: str = "competitive", org: str = "", wc: str = "") -> float:
    """Competitive matchmaking cost with explicit sporting roles and hard repeat suppression."""
    rec_a=list(getattr(a,"pro_record",[0,0,0]) or [0,0,0]); rec_b=list(getattr(b,"pro_record",[0,0,0]) or [0,0,0])
    exp_gap=abs(sum(rec_a)-sum(rec_b))
    try: score_gap=abs(float(pool._rank_score(a))-float(pool._rank_score(b)))
    except Exception: score_gap=0.0
    meta=pool.matchup_history.get(_pair_key(a.fid,b.fid),{})
    last=int(meta.get("last_week",-9999) or -9999); count=int(meta.get("count",0) or 0); age=max(0,int(week)-last)
    if intent == "rematch": repeat=(45.0 if age < 39 else 5.0) * max(0,count-1)
    else:
        repeat=(420.0 if age < 52 else 180.0 if age < 104 else 55.0 if age < 156 else 15.0)*count
        if count >= 3 and age < 208: repeat += 500.0
    role_pen=0.0
    if org and wc:
        ra,rb=_career_role(pool,org,wc,a),_career_role(pool,org,wc,b)
        roles={ra,rb}
        if intent == "title_eliminator": role_pen += 0 if ra==rb=="contender" else 120
        elif intent == "prospect_vs_gatekeeper": role_pen += 0 if roles=={"prospect","gatekeeper"} else 90
        elif intent == "rebuild": role_pen += 0 if "rebuild" in roles and ("gatekeeper" in roles or "journeyman" in roles or "roster" in roles) else 75
        elif intent == "competitive" and "champion" in roles: role_pen += 80
    activity=min(30,int(getattr(b,"idle_weeks",0) or 0))*0.35
    living = 0.0
    try:
        from . import living_careers
        living = living_careers.matchup_adjustment(pool,org,wc,a,b,intent)
    except Exception:
        living = 0.0
    return score_gap*.30 + exp_gap*.85 + repeat + role_pen - activity + living + random.random()*2.0

def _best_pair(pool, org, wc, names, intent, predicate=None):
    candidates=[]
    for i,a in enumerate(names):
        for b in names[i+1:]:
            if predicate and not predicate(a,b): continue
            if _meeting_count(pool, a.fid, b.fid) >= 3:
                continue
            candidates.append((_pair_cost(pool,a,b,pool.week if hasattr(pool,"week") else 0,intent,org,wc),a,b))
    if not candidates: return None
    _,a,b=min(candidates,key=lambda x:x[0]); return a,b

def _role_pair(pool, org: str, wc: str, names: list, week: int):
    """Return (a,b,semantic_role). This is the active card-builder path."""
    if len(names)<2: return None,None,"activity_fight"
    roles={getattr(f,"fid",id(f)):_career_role(pool,org,wc,f) for f in names}
    role_of=lambda f: roles.get(getattr(f,"fid",id(f)), "roster")

    # Long-idle fighters cannot be starved forever by repeated prospect or
    # contender storytelling. Once someone crosses a year without a bout,
    # activity is the sporting priority as long as a legal fresh peer exists.
    urgent=max(names,key=lambda f:int(getattr(f,"idle_weeks",0) or 0))
    if int(getattr(urgent,"idle_weeks",0) or 0) >= 52:
        fresh=[f for f in names if f is not urgent and _meeting_count(pool,urgent.fid,f.fid) < 3]
        if fresh:
            opp=min(fresh,key=lambda f:_pair_cost(pool,urgent,f,week,"competitive",org,wc))
            return urgent,opp,"activity_fight"

    try:
        from . import living_careers
        _prof=living_careers.profile(org)
    except Exception:
        _prof={"merit":.5,"protect":.5,"activity":.5}
    contenders=[f for f in names if role_of(f)=="contender"]
    contender_chance=min(.90,.30 + .50*float(_prof.get("merit",.5)))
    if len(contenders)>=2 and (org in ("UFC","PFL","Bellator") or random.random()<contender_chance):
        pair=_best_pair(pool,org,wc,contenders,"title_eliminator")
        if pair: return pair[0],pair[1],"title_eliminator"
    prospects=[f for f in names if role_of(f)=="prospect"]; gates=[f for f in names if role_of(f)=="gatekeeper"]
    showcase_chance=min(.90,.30 + .60*float(_prof.get("protect",.5)))
    if prospects and gates and random.random()<showcase_chance:
        eligible=[]
        for a in prospects:
            for b in gates:
                if _meeting_count(pool, a.fid, b.fid) >= 3:
                    continue
                eligible.append((_pair_cost(pool,a,b,week,"prospect_vs_gatekeeper",org,wc),a,b))
        if eligible:
            pair=min(eligible,key=lambda x:x[0])
            return pair[1],pair[2],"prospect_vs_gatekeeper"
    rebuild=[f for f in names if role_of(f)=="rebuild"]
    if rebuild and random.random()<.38:
        candidates=[]
        for a in rebuild:
            for b in names:
                if b is a or role_of(b) not in ("gatekeeper","journeyman","roster"):
                    continue
                if _meeting_count(pool, a.fid, b.fid) >= 3:
                    continue
                candidates.append((_pair_cost(pool,a,b,week,"rebuild",org,wc),a,b))
        if candidates:
            _,a,b=min(candidates,key=lambda x:x[0])
            return a,b,"rebuild"
    # Deliberate rematches are rare and require enough time since the first meeting.
    if random.random()<.07:
        rem=[]
        for i,a in enumerate(names):
            for b in names[i+1:]:
                m=pool.matchup_history.get(_pair_key(a.fid,b.fid),{})
                if _meeting_count(pool, a.fid, b.fid)==1 and week-int(m.get("last_week",0) or 0)>=78:
                    rem.append((_pair_cost(pool,a,b,week,"rematch",org,wc),a,b))
        if rem:
            _,a,b=min(rem,key=lambda x:x[0]); return a,b,"rematch"
    a=max(names,key=lambda f:(bool(getattr(f,"npc_wants_fight",False)),int(getattr(f,"idle_weeks",0) or 0),pool._rank_score(f)))
    choices=[f for f in names if f is not a and _meeting_count(pool, a.fid, f.fid) < 3]
    if not choices:
        return None,None,"activity_fight"
    b=min(choices,key=lambda f:_pair_cost(pool,a,f,week,"competitive",org,wc))
    return a,b,"activity_fight"


def _pick_title(pool, org: str, week: int, roster: list) -> tuple | None:
    """Book the promotion's most overdue healthy champion, including double champs.

    Belt ownership, not the fighter's current home division, is authoritative.
    This lets a legitimate two-division champion defend either belt without
    silently vacating the other one.
    """
    ready = []
    belts = getattr(pool, "belts", None) or {}
    roster_ids = {str(getattr(f, "fid", "") or "") for f in roster}
    for key, info in belts.items():
        if not isinstance(info, dict) or str(info.get("org") or "") != org:
            continue
        wc = str(info.get("wc") or (str(key).split("|", 1)[1] if "|" in str(key) else ""))
        champ = pool.belt_holder(org, wc)
        if champ is None or not getattr(champ, "active", True) or getattr(champ, "npc_injury_weeks", 0):
            continue
        # Future-card integrity: a champion already committed to another open
        # card is not eligible to be scheduled again here. _build_card()
        # passes a roster with all open-card fighter IDs removed.
        if str(getattr(champ, "fid", "") or "") not in roster_ids:
            continue
        projected_idle = int(getattr(champ, "idle_weeks", 0) or 0) + max(0, week - int(getattr(pool, "week", 0) or 0))
        last_def = int(info.get("last_defense_week", info.get("won_week", 0)) or 0)
        title_gap = max(0, int(week) - last_def)
        threshold = 16 if org == "UFC" else 20
        if max(projected_idle, title_gap) < threshold:
            continue
        challengers = [f for f in roster if f is not champ and f.weight_class == wc]
        if not challengers:
            continue
        board = [f for f in pool.get_org_top(org, wc, 15) if f in challengers]
        choices = board or sorted(challengers, key=pool._rank_score, reverse=True)
        contender_set = [f for f in choices[:10]
                         if _meeting_count(pool, champ.fid, f.fid) < 3]
        if not contender_set:
            continue
        challenger = min(contender_set, key=lambda f: (
            _pair_cost(pool, champ, f, week, "title", org, wc)
            + choices.index(f) * 1.5
        ))
        ready.append((max(projected_idle, title_gap), pool._rank_score(challenger), wc, champ, challenger))
    if not ready:
        return None
    _, _, wc, champ, challenger = max(ready, key=lambda row: (row[0], row[1]))
    return champ, challenger, wc


def _build_card(pool, org: str, week: int) -> dict:
    used=_open_ids(pool)
    roster=[f for f in pool.fighters if getattr(f,"active",True) and getattr(f,"pro_debut",False)
            and getattr(f,"organization",None)==org and not getattr(f,"npc_injury_weeks",0) and getattr(f,"fid",None) not in used]
    random.shuffle(roster); by_wc={}
    for f in roster: by_wc.setdefault(f.weight_class,[]).append(f)
    bouts=[]; max_bouts=9 if org in ("UFC","PFL","Bellator") else 7
    title_pair=_pick_title(pool,org,week,roster)
    if title_pair:
        champ,challenger,title_wc=title_pair
        bouts.append({"red_id":champ.fid,"blue_id":challenger.fid,"weight_class":title_wc,"slot":"main","title":True,"status":"scheduled","matchup_role":"title_defense"})
        by_wc[title_wc]=[f for f in by_wc.get(title_wc,[]) if f not in (champ,challenger)]

        # Promotions with eight divisions cannot keep every champion active if
        # every card is limited to one title fight. A second title is allowed
        # only when another belt is already materially overdue (roughly ten months),
        # preserving ordinary card variety while preventing 80-100 week reign
        # gaps in slower promotions.
        roster2=[f for f in roster if f not in (champ,challenger)]
        second=_pick_title(pool,org,week,roster2)
        if second:
            champ2,challenger2,wc2=second
            key2=str(org)+"|"+str(wc2)
            info2=(getattr(pool,"belts",None) or {}).get(key2,{})
            last2=int(info2.get("last_defense_week",info2.get("won_week",week)) or week)
            projected_gap=max(0,int(week)-last2)
            projected_idle=int(getattr(champ2,"idle_weeks",0) or 0)+max(0,int(week)-int(getattr(pool,"week",0) or 0))
            if max(projected_gap,projected_idle) >= 40 and len(bouts)<max_bouts:
                bouts.append({"red_id":champ2.fid,"blue_id":challenger2.fid,"weight_class":wc2,"slot":"co-main","title":True,"status":"scheduled","matchup_role":"title_defense"})
                by_wc[wc2]=[f for f in by_wc.get(wc2,[]) if f not in (champ2,challenger2)]
    while len(bouts)<max_bouts:
        viable=[(wc,names) for wc,names in by_wc.items() if len(names)>=2]
        if not viable: break
        wc,names=max(viable,key=lambda item:max(int(getattr(f,"idle_weeks",0) or 0) for f in item[1]))
        a,b,role=_role_pair(pool,org,wc,names,week)
        if not a or not b:
            # A saturated trilogy-only division must not abort the rest of the
            # card. Remove this division from this card-build pass and let
            # other weight classes fill the remaining slots.
            by_wc.pop(wc, None)
            continue
        names.remove(a); names.remove(b)
        bouts.append({"red_id":a.fid,"blue_id":b.fid,"weight_class":wc,"slot":"prelim","title":False,"status":"scheduled","matchup_role":role})
    if bouts:
        if not bouts[0].get("title"):
            bouts.sort(key=lambda bout:sum(pool._rank_score(pool.get_by_id(fid)) for fid in (bout["red_id"],bout["blue_id"])),reverse=True)
            bouts[0]["slot"]="main"
        if len(bouts)>1: bouts[1]["slot"]="co-main"
        # Main-card depth is explicit; lower-ranked bouts remain prelims.
        for i, bout in enumerate(bouts):
            if i == 0: bout["slot"] = "main"
            elif i == 1: bout["slot"] = "co-main"
            elif i < 5: bout["slot"] = "main-card"
            else: bout["slot"] = "prelim"
    eid="%s-%05d"%(org.replace(" ","")[:5].upper(),pool.next_event_id); pool.next_event_id+=1
    numbered = any(bool(b.get("title")) for b in bouts)
    event_name, series, number = _identity(pool, org, numbered)
    return {"id":eid,"org":org,"event_name":event_name,"series":series,"number":number,
            "week":int(week),"location":random.choice(LOCATIONS.get(org,(ORG_DATA.ORGS[org]["region"],))),
            "status":"scheduled","bouts":bouts}


def maintain(pool, horizon: int = 14) -> None:
    """Each promoter keeps its own cadence and future cards."""
    ensure(pool)
    repair_titles(pool)
    now = int(getattr(pool, "week", 0) or 0)
    for org in ORG_DATA.ORGS:
        future = sorted(int(e.get("week", 0)) for e in pool.events
                        if e.get("org") == org and e.get("status") == "scheduled" and int(e.get("week", 0)) >= now)
        last = future[-1] if future else now + random.randint(1, CADENCE.get(org, 7))
        if not future:
            card = _build_card(pool, org, last)
            if card["bouts"]:
                pool.events.append(card)
        while last < now + horizon:
            last += CADENCE.get(org, 7)
            card = _build_card(pool, org, last)
            if card["bouts"]:
                pool.events.append(card)


def repair_titles(pool) -> int:
    """Downgrade stale title labels when the live champion is no longer booked."""
    ensure(pool)
    changed = 0
    for ev in pool.events:
        if ev.get("status") != "scheduled":
            continue
        for bout in ev.get("bouts", []):
            if not bout.get("title"):
                continue
            holder = pool.belt_holder(ev.get("org"), bout.get("weight_class")) if hasattr(pool, "belt_holder") else None
            if holder is None or getattr(holder, "fid", None) not in (bout.get("red_id"), bout.get("blue_id")):
                bout["title"] = False
                changed += 1
    return changed


def offer_slot(pool, fighter, offer: dict) -> dict:
    """Attach an offer to a real scheduled card without reserving the fighter."""
    ensure(pool)
    org = str(offer.get("org") or "")
    now = int(getattr(fighter, "week", 0) or 0)
    cards = [e for e in pool.events if e.get("org") == org and e.get("status") == "scheduled"
             and int(e.get("week", 0)) > now]
    if not cards:
        maintain(pool, 18)
        cards = [e for e in pool.events if e.get("org") == org and e.get("status") == "scheduled"
                 and int(e.get("week", 0)) > now]
    if cards:
        desired = int(offer.get("date_week", now + 6) or now + 6)
        urgent = [e for e in cards if 1 <= int(e["week"]) - now <= 3]
        card = random.choice(urgent) if urgent and random.random() < 0.14 else min(
            cards, key=lambda e: abs(int(e["week"]) - desired))
        offer["event_id"] = card["id"]
        offer["date_week"] = int(card["week"])
        offer["location"] = card["location"]
        left = int(card["week"]) - now
        if left <= 3:
            offer["short_notice"] = True
            offer["tag"] = "short notice"
    return offer


def attach_player_bout(pool, fighter, offer: dict) -> None:
    ensure(pool)
    eid = offer.get("event_id")
    ev = next((e for e in pool.events if e.get("id") == eid), None)
    if not ev:
        return
    # A fighter has only one open booking and one slot on this card.
    opponent_id = offer.get("opponent_id")
    for event in pool.events:
        for bout in event.get("bouts", []):
            if "PLAYER" in (bout.get("red_id"), bout.get("blue_id")) or opponent_id in (bout.get("red_id"), bout.get("blue_id")):
                bout["status"] = "cancelled"
    if offer.get("title"):
        if ev.get("series") != "numbered":
            name, series, n = _identity(pool, str(ev.get("org") or ""), True)
            ev["event_name"] = name; ev["series"] = series; ev["number"] = n
        for bout in ev.get("bouts", []):
            if bout.get("slot") == "co-main":
                bout["slot"] = "featured"
            elif bout.get("slot") == "main":
                bout["slot"] = "co-main"
    ev["bouts"].append({"red_id": "PLAYER", "blue_id": offer.get("opponent_id"),
                        "weight_class": offer.get("weight_class") or getattr(fighter, "fight_weight_class", None) or fighter.weight_class,
                        "slot": "main" if offer.get("title") else "featured",
                        "title": bool(offer.get("title")), "status": "scheduled",
                        "matchup_role": offer.get("matchup_role") or ("title_challenge" if offer.get("title") else "player_offer")})


def process_player_withdrawal(pool, player) -> str | None:
    booked=getattr(player,"booked_fight",None)
    if not isinstance(booked,dict) or not booked.get("date_week"): return None
    weeks=int(booked["date_week"])-int(getattr(player,"week",0) or 0)
    if weeks<1 or weeks>6 or booked.get("replacement_made"): return None
    if random.random()>=0.012: return None
    old_id=booked.get("opponent_id"); busy=_open_ids(pool)
    choices=[f for f in pool.fighters if getattr(f,"active",True) and getattr(f,"pro_debut",False) and f.weight_class==player.weight_class
             and f.fid!=old_id and getattr(f,"organization",None)==booked.get("org") and f.fid not in busy]
    if not choices:
        ev=next((e for e in pool.events if e.get("id")==booked.get("event_id")),None)
        if ev:
            for bout in ev.get("bouts",[]):
                if "PLAYER" in (bout.get("red_id"),bout.get("blue_id")): bout["status"]="cancelled"
        player.booked_fight=None; player.camp_active=False; player.camp_weeks_remaining=0
        return "Opponent withdrew and no replacement accepted. The bout is cancelled."
    old=getattr(booked.get("opponent"),"name","opponent"); replacement=random.choice(choices)
    booked["opponent"]=replacement; booked["opponent_id"]=replacement.fid; booked["replacement_made"]=True; booked["short_notice"]=weeks<=3
    booked["tag"]="replacement"+(" · short notice" if weeks<=3 else "")
    if weeks<=3:
        booked["purse_win"]=int(int(booked.get("purse_win",0) or 0)*1.20); booked["purse_show"]=int(int(booked.get("purse_show",0) or 0)*1.20)
        player.fame=min(100,int(getattr(player,"fame",0) or 0)+2)
        try:
            from . import contracts, people, memory
            bumped=contracts.apply_offer_clauses(player,booked); booked.update(bumped)
            mm=people.matchmaker_for(str(booked.get("org") or ""))
            if mm: memory.remember(player,mm.id,"reliable_short_notice",replacement.name)
        except Exception: pass
    ev=next((e for e in pool.events if e.get("id")==booked.get("event_id")),None)
    if ev:
        for bout in ev.get("bouts",[]):
            if bout.get("status")=="scheduled" and "PLAYER" in (bout.get("red_id"),bout.get("blue_id")):
                if bout.get("red_id")=="PLAYER": bout["blue_id"]=replacement.fid
                else: bout["red_id"]=replacement.fid
                bout["replacement"]=True; bout["short_notice"]=weeks<=3; bout["matchup_role"]="short_notice_replacement"; break
    return "%s withdrew. %s steps in for week %s%s."%(old,replacement.name,booked["date_week"]," — short notice premium added" if weeks<=3 else "")

def process_world_withdrawals(pool) -> list[str]:
    """Rare NPC withdrawals create replacements without stalling cards."""
    ensure(pool); lines=[]; now=int(getattr(pool,"week",0) or 0); busy=_open_ids(pool)
    for ev in pool.events:
        left=int(ev.get("week",0) or 0)-now
        if ev.get("status")!="scheduled" or not 1<=left<=4: continue
        for bout in ev.get("bouts",[]):
            if bout.get("status")!="scheduled" or "PLAYER" in (bout.get("red_id"),bout.get("blue_id")) or bout.get("replacement"): continue
            a,b=pool.get_by_id(bout.get("red_id")),pool.get_by_id(bout.get("blue_id")); injured=[f for f in (a,b) if f and getattr(f,"npc_injury_weeks",0)]
            chance=.004 + (.10 if injured else 0.0)
            if random.random()>=chance: continue
            out=injured[0] if injured else random.choice([a,b]); keep=b if out is a else a
            choices=[f for f in pool.fighters if getattr(f,"active",True) and getattr(f,"pro_debut",False) and getattr(f,"organization",None)==ev.get("org")
                     and getattr(f,"weight_class",None)==bout.get("weight_class") and f not in (a,b) and f.fid not in busy and not getattr(f,"npc_injury_weeks",0)
                     and _meeting_count(pool, getattr(keep,"fid",None), getattr(f,"fid",None)) < 3]
            if not choices:
                bout["status"]="cancelled"; lines.append("%s loses a bout after %s withdraws."%(ev.get("org"),out.name)); continue
            repl=min(choices,key=lambda f:_pair_cost(pool,keep,f,ev.get("week",now),"competitive",ev.get("org"),bout.get("weight_class")))
            if bout.get("red_id")==out.fid: bout["red_id"]=repl.fid
            else: bout["blue_id"]=repl.fid
            bout["replacement"]=True; bout["short_notice"]=left<=2; bout["withdrawal"]=out.name; bout["matchup_role"]="short_notice_replacement"
            busy.add(repl.fid); lines.append("%s: %s replaces %s on short notice."%(ev.get("org"),repl.name,out.name))
    return lines


def _record_form(fighter, opponent, result: str, org: str, week: int) -> None:
    code = str(result or "D").upper()[:1]
    fighter.recent_results = (list(getattr(fighter, "recent_results", None) or []) + [code])[-5:]
    streak = int(getattr(fighter, "current_streak", 0) or 0)
    if code == "W":
        fighter.current_streak = streak + 1 if streak > 0 else 1
    elif code == "L":
        fighter.current_streak = streak - 1 if streak < 0 else -1
    else:
        fighter.current_streak = 0
    fighter.idle_weeks = 0
    history = list(getattr(fighter, "fight_history", None) or [])
    history.append({"opponent": opponent.name, "opponent_id": getattr(opponent, "fid", None),
                    "result": {"W": "Win", "L": "Loss"}.get(code, "Draw"),
                    "method": "Simulated", "round": 0, "event": org,
                    "week": int(week), "pro": True, "sport": "mma", "ruleset": "mma"})
    # NPC history informs rankings and promotion movement without allowing a
    # 20-year world save to grow without limit.
    fighter.fight_history = history[-60:]


def _record_matchup(pool, a, b, week: int) -> None:
    ensure(pool)
    key = _pair_key(a.fid, b.fid)
    old = pool.matchup_history.get(key, {})
    pool.matchup_history[key] = {"count": int(old.get("count", 0) or 0) + 1,
                                 "last_week": int(week)}
    # Lifetime memory is separate from the recency table. It is never pruned;
    # a 20-year career therefore cannot "forget" a trilogy and book fight #4.
    pool.matchup_lifetime[key] = max(int(pool.matchup_lifetime.get(key, 0) or 0), int(old.get("count", 0) or 0)) + 1

    # Pairing recency only needs the last five seasons.
    floor = int(week) - 260
    if len(pool.matchup_history) > 4000:
        pool.matchup_history = {k: v for k, v in pool.matchup_history.items()
                                if int(v.get("last_week", 0) or 0) >= floor}


def resolve_due(pool) -> list[str]:
    ensure(pool)
    lines = []
    due = [e for e in pool.events if e.get("status") == "scheduled" and int(e.get("week", 0)) <= pool.week]
    for ev in due:
        results = [str(b.get("result")) for b in ev.get("bouts", []) if b.get("status") == "complete" and b.get("result")]
        title_changes = []
        for bout in ev.get("bouts", []):
            if bout.get("status") != "scheduled" or "PLAYER" in (bout.get("red_id"), bout.get("blue_id")):
                continue
            a, b = pool.get_by_id(bout.get("red_id")), pool.get_by_id(bout.get("blue_id"))
            if not a or not b or not a.active or not b.active:
                bout["status"] = "cancelled"
                continue
            champion = pool.belt_holder(ev["org"], bout["weight_class"]) if bout.get("title") else None
            winner, loser, draw = pool.simulate_ai_fight(a, b)
            if draw:
                a.pro_record[2] += 1; b.pro_record[2] += 1
                _record_form(a, b, "D", ev["org"], ev["week"])
                _record_form(b, a, "D", ev["org"], ev["week"])
                text = "%s vs %s — draw" % (a.name, b.name)
            else:
                winner.pro_record[0] += 1; loser.pro_record[1] += 1
                _record_form(winner, loser, "W", ev["org"], ev["week"])
                _record_form(loser, winner, "L", ev["org"], ev["week"])
                text = "%s def. %s" % (winner.name, loser.name)
                if bout.get("title"):
                    if champion is winner:
                        pool.record_title_defense(ev["org"], bout["weight_class"], winner, loser)
                    else:
                        pool.award_belt(ev["org"], bout["weight_class"], winner,
                                        reason="title fight", defeated=champion or loser)
                        title_changes.append({"weight_class": bout["weight_class"],
                                              "winner": winner.name,
                                              "previous": getattr(champion or loser, "name", None)})
            _record_matchup(pool, a, b, ev["week"])
            bout["status"] = "complete"
            bout["result"] = text
            bout["winner_id"] = None if draw else winner.fid
            results.append(text)
        ev["status"] = "complete"
        ev["results"] = results
        pool.event_history.append({"id": ev["id"], "org": ev["org"], "event_name": ev.get("event_name") or ev["org"],
                                   "series": ev.get("series"), "number": ev.get("number"), "week": ev["week"],
                                   "location": ev["location"], "results": results,
                                   "title_changes": title_changes,
                                   "bouts": [dict(b) for b in ev.get("bouts", [])]})
        if results:
            lines.append("%s · %s: %s." % (ev.get("event_name") or ev["org"], ev["location"], results[0]))
    pool.events = [e for e in pool.events if e.get("status") == "scheduled"]
    pool.event_history = pool.event_history[-160:]
    return lines


def complete_player_bout(pool, event_id: str, result: str, opponent_name: str,
                         method: str = "", rating: float = 0.0) -> None:
    ensure(pool)
    ev = next((e for e in pool.events if e.get("id") == event_id), None)
    archived = next((e for e in reversed(pool.event_history) if e.get("id") == event_id), None)
    target = ev or archived
    if not target:
        return
    for bout in target.get("bouts", []):
        if "PLAYER" not in (bout.get("red_id"), bout.get("blue_id")):
            continue
        if bout.get("status") in ("scheduled", "complete"):
            text = "PLAYER %s vs %s" % (str(result).lower(), opponent_name)
            if method:
                text += " (%s)" % method
            bout["status"] = "complete"
            bout["result"] = text
            bout["method"] = method
            bout["performance_rating"] = float(rating or 0.0)
            if archived is not None:
                results = [x for x in list(archived.get("results") or []) if not str(x).startswith("PLAYER ")]
                archived["results"] = [text] + results
            break


def completed_card_lines(pool, limit: int = 5) -> list[str]:
    """Readable recent-card summaries with title changes and post-event notes."""
    ensure(pool)
    rows = []
    for ev in reversed(list(pool.event_history or [])[-max(1, int(limit)):]):
        rows.append("w%s %s · %s" % (ev.get("week", "?"), ev.get("event_name") or ev.get("org", ""), ev.get("location", "")))
        results = list(ev.get("results") or [])
        for result in results[:3]:
            rows.append("  " + str(result))
        if len(results) > 3:
            rows.append("  +%s more bout%s" % (len(results)-3, "" if len(results)-3 == 1 else "s"))
        for change in list(ev.get("title_changes") or []):
            rows.append("  TITLE %s: %s%s" % (change.get("weight_class", ""), change.get("winner", ""),
                        (" def. " + str(change.get("previous"))) if change.get("previous") else ""))
        for note in list(ev.get("post_event") or [])[-2:]:
            bits = []
            if note.get("bonus"): bits.append("bonus $%s" % format(int(note["bonus"]), ","))
            if note.get("rank_before") and note.get("rank_after") and note.get("rank_before") != note.get("rank_after"):
                bits.append("rank #%s→#%s" % (note["rank_before"], note["rank_after"]))
            if bits: rows.append("  %s: %s" % (note.get("fighter", ""), " · ".join(bits)))
    return rows


def card_lines(pool, event_id: str) -> list[str]:
    ensure(pool)
    ev = next((x for x in pool.events if x.get("id") == event_id), None)
    if not ev:
        return []
    rows = ["%s · %s · week %s" % (ev.get("event_name") or ev["org"], ev["location"], ev["week"])]
    order = {"main": 0, "co-main": 1, "main-card": 2, "featured": 2, "prelim": 3}
    for bout in sorted(ev.get("bouts", []), key=lambda x: order.get(x.get("slot"), 9)):
        if bout.get("status") == "cancelled":
            continue
        a = "YOU" if bout.get("red_id") == "PLAYER" else getattr(pool.get_by_id(bout.get("red_id")), "name", "TBA")
        b = "YOU" if bout.get("blue_id") == "PLAYER" else getattr(pool.get_by_id(bout.get("blue_id")), "name", "TBA")
        rows.append("%s%s: %s vs %s" % (bout.get("slot", "prelim"), " TITLE" if bout.get("title") else "", a, b))
    return rows
