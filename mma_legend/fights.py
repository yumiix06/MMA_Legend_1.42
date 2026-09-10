"""Finding opponents, running a fight night, and the amateur tournament ladder."""
from __future__ import annotations

import random

from . import constants as C
from . import data
from .combat import fight_mma, post_fight_analysis
from . import story
from .models import Fighter
from .ui import GameConsole


def _pick_watch_mode(console: GameConsole, current: str = "Sim") -> str:
    """Fight-view choice with the saved preference as the Enter default."""
    current = str(current or "Sim")
    label = {"Full":"Play-by-play", "Round":"Play-by-play", "Sim":"Live Sim", "Instant":"Instant", "Quick":"Instant"}.get(current, "Live Sim")
    console.print("Fight view (Enter = %s):" % label)
    console.print("  A) Play-by-play — interactive moments + corner")
    console.print("  B) Live Sim — automatic action + corner summaries")
    console.print("  C) Instant — jump to result and post-fight card")
    raw = (console.ask("Watch > ") or "").strip().upper()
    if not raw:
        return "Full" if current in ("Full","Round") else "Instant" if current in ("Instant","Quick") else "Sim"
    return {"A":"Full", "B":"Sim", "C":"Instant"}.get(raw, "Sim")


def recommend_gameplan(fighter, opponent) -> str:
    """Coach recommendation limited by the player's actual scouting depth."""
    try:
        from . import combat_intelligence as _ci
        return _ci.coach_recommendation(fighter, opponent)
    except Exception:
        return "Balanced"


def get_venue(tier: int) -> str:
    venues = ["Local Gym", "Community Center", "Regional Arena", "National Stadium",
              "International Coliseum", "Bellator Arena", "ONE Dome", "PFL Center",
              "Rizin Hall", "UFC Apex", "UFC Stadium"]
    return venues[min(tier, len(venues) - 1)]


def _kg_label(cls: str) -> str:
    lo, hi = C.WEIGHT_RANGES_KG.get(cls, (0, 0))
    short = {
        "Flyweight": "FLY", "Bantamweight": "BW", "Featherweight": "FW",
        "Lightweight": "LW", "Welterweight": "WW", "Middleweight": "MW",
        "Light Heavyweight": "LHW", "Heavyweight": "HW",
    }.get(cls, cls)
    return "%s (%s-%s)" % (short, lo, hi)


def get_weight_class_options(fighter) -> list:
    classes = C.WEIGHT_CLASSES
    walk = float(getattr(fighter, "walking_weight", None) or fighter.weight or 70)
    # 84 sits on MW cap and LHW floor
    if walk >= 84:
        natural = "Light Heavyweight" if walk < 93 else "Heavyweight"
        if walk >= 93:
            natural = "Heavyweight"
    elif walk >= 77:
        natural = "Middleweight"
    else:
        natural = fighter.natural_weight_class if fighter.natural_weight_class in classes else "Lightweight"
    if natural in classes:
        fighter.natural_weight_class = natural
    idx = classes.index(natural) if natural in classes else 3
    options = []
    options.append(("stay", natural, "Stay " + _kg_label(natural) + " no cut"))
    if idx > 0:
        options.append(("cut", classes[idx - 1], "Make " + _kg_label(classes[idx - 1]) + " light cut"))
    if idx > 1:
        options.append(("hard", classes[idx - 2], "Hard cut " + _kg_label(classes[idx - 2])))
    if idx < len(classes) - 1:
        options.append(("move up", classes[idx + 1], "Walk up " + _kg_label(classes[idx + 1])))
    return options


def _pick_weight_option(raw: str, options: list):
    raw = (raw or "").strip().upper()
    letters = "ABCDEFGH"
    if raw.isdigit():
        i = int(raw) - 1
        if 0 <= i < len(options):
            return options[i]
    if raw and raw[0] in letters:
        i = letters.index(raw[0])
        if i < len(options):
            return options[i]
    return None


def apply_class_body(f) -> None:
    """Compatibility wrapper; physiology.py is the canonical class profile."""
    from .physiology import apply_class_baseline
    apply_class_baseline(f)


def generate_random_opponent(fighter, country_bias=None, field: str = "normal") -> Fighter:
    """Build an opponent. country_bias: prefer this nation (nationals). field: normal|national|elite."""
    if data.OPPONENTS:
        pool = data.OPPONENTS
        if country_bias:
            same = [m for m in pool if m.get("country") == country_bias]
            if same and random.random() < 0.90:
                meta = random.choice(same)
            else:
                meta = random.choice(pool)
        else:
            meta = random.choice(pool)
        name = f"{meta['firstName']} {meta['lastName']}"
        recent = {str(x.get("opponent")) for x in list(getattr(fighter, "fight_history", None) or [])[-8:]}
        if name in recent and len(pool) > 4:
            meta = random.choice(pool)
            name = f"{meta['firstName']} {meta['lastName']}"
        country = meta.get("country", "USA")
        if country_bias and random.random() < 0.90:
            country = country_bias
        team = meta.get("team", "Free Agent")
        style = meta.get("style", "Balanced")
        archetype_name = meta.get("archetype")
    else:
        name = f"Random Opponent {random.randint(100, 999)}"
        country = country_bias or "USA"
        team, style, archetype_name = "Free Agent", "Balanced", None

    country_data = data.country_by_name(country) or {"name": country, "flag": "🌍", "bonus": {}}
    opp = Fighter.new_npc(name, country_data, style=style, team=team)
    opp.weight_class = fighter.weight_class
    opp.weight = fighter.weight + random.randint(-5, 5)
    opp.natural_weight_class = opp.weight_class
    opp.fight_weight_class = opp.weight_class
    _wm = random.uniform(1.02, 1.06) if opp.weight_class != "Heavyweight" else random.uniform(1.01, 1.04)
    opp.natural_weight = min(128.0, float(opp.weight) * _wm)
    opp.walking_weight = opp.natural_weight
    if fighter.pro_debut:
        pw = int((fighter.pro_record or [0, 0, 0])[0])
        pl = int((fighter.pro_record or [0, 0, 0])[1])
        opp.pro_record = [
            random.randint(max(0, pw - 2), pw + 3),
            random.randint(0, max(1, pl + 2)),
            random.randint(0, 1),
        ]
        opp.pro_debut = True
        opp.amateur_record = list(fighter.amateur_record or [0, 0, 0])
    else:
        aw = int((fighter.amateur_record or [0, 0, 0])[0])
        opp.amateur_record = [random.randint(max(0, aw - 2), aw + 2), random.randint(0, 2), 0]
        opp.pro_record = [0, 0, 0]
        opp.pro_debut = False

    from . import booking
    booking.apply_kit(opp, style or getattr(opp, "style", "MMA"))

    from .world import _apply_archetype
    _apply_archetype(opp, data.archetype_by_name(archetype_name))

    # Scale tightly to the player's real skill so training meets resistance.
    skills = list(C.SKILLS)
    player_avg = sum(getattr(fighter, s) for s in skills) / len(skills)
    tier_floor = 20 + fighter.promotion_tier * 4
    # Center slightly above the player so "even" nights still require good choices
    if not fighter.pro_debut:
        # Club amateurs. Do not clone a debug-boosted 90 stat line.
        cap = 56 if field == "normal" else (66 if field == "national" else 74)
        offset = random.uniform(-4, 2)
        target = min(cap, max(28, min(player_avg - 8, cap) + offset))
    else:
        offset = random.uniform(-1, 3) if fighter.promotion_tier == 0 and player_avg < 36 else random.uniform(1, 5)
        target = max(tier_floor, player_avg + offset)
    roll = random.random()
    if roll < 0.22:
        target += random.uniform(5, 11)   # tough night
    elif roll < 0.32:
        target -= random.uniform(3, 7)    # tune-up

    for s in skills:
        base = getattr(opp, s)
        from .physiology import target_stat_for_class, clamp_stat
        desired = target_stat_for_class(opp.weight_class, s, target) + random.uniform(-6, 6)
        # Prefer target over NPC template so ranking stays meaningful, but keep
        # divisional physical identity instead of overwriting it afterward.
        blended = 0.2 * base + 0.8 * desired
        setattr(opp, s, max(14, clamp_stat(opp, s, round(blended))))

    if getattr(fighter, "camp_active", False) or getattr(fighter, "camp_bonus", 0) > 2:
        from .physiology import gain_stat
        for s in ("cardio", "fight_iq", "durability", "speed"):
            gain_stat(opp, s, random.randint(1, 4))

    # Mirror player's best skills a bit so specialists still get tested
    top = sorted(skills, key=lambda s: getattr(fighter, s), reverse=True)[:3]
    from .physiology import gain_stat
    for s in top:
        gain_stat(opp, s, random.randint(2, 5))

    if not fighter.pro_debut:
        # Club kids are not gas tanks. Cap cardio near the player.
        cap_cardio = min(58, max(28, int(getattr(fighter, "cardio", 30)) + 8))
        opp.cardio = min(int(opp.cardio), cap_cardio)
        opp.energy = random.randint(70, 88)
        aw = int((fighter.amateur_record or [0, 0, 0])[0])
        opp.amateur_record = [random.randint(max(0, aw - 2), aw + 2), random.randint(0, 2), 0]
        opp.pro_record = [0, 0, 0]
        opp.pro_debut = False
    else:
        opp.energy = random.randint(82, 96)
    opp.health = random.randint(92, 100)
    return opp


def find_opponent_from_pool(fighter, pool) -> Fighter:
    from . import booking
    roster = list(getattr(pool, "fighters", []) or [])
    wc = getattr(fighter, "weight_class", None)
    opponents = [f for f in roster if booking.opponent_fits(fighter, f)
                 and (not wc or getattr(f, "weight_class", None) in (wc, None, ""))]
    if not opponents:
        ranked = pool.get_ranked_opponents(fighter.weight_class, exclude=fighter) if pool else []
        opponents = [f for f in ranked if booking.opponent_fits(fighter, f)]
    if not opponents:
        return generate_random_opponent(fighter)
    if len(opponents) == 1:
        return opponents[0]
    n = min(5, len(opponents))
    idx = random.choices(range(n), weights=list(range(n, 0, -1)), k=1)[0]
    return opponents[idx]



# Weight cutting is resolved only by cut.weigh_in() on fight night.
# The pre-1.24 interactive cut path was intentionally removed to prevent
# walking_weight corruption and double dehydration.

def find_fight(console: GameConsole, fighter, pool) -> None:
    from .systems15 import can_compete
    why = can_compete(fighter)
    if why:
        console.warn(why)
        console.pause(0.7)
        return
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week"):
        dw = int(booked.get("date_week") or 0)
        if fighter.week < dw:
            console.warn("Already booked week %s vs %s. Train the camp." % (
                dw, booked.get("org") or "that card"))
            console.pause(0.8)
            return
        booker_night(console, fighter, pool)
        return
    inj = getattr(fighter, "injury", None) or {}
    if inj.get("weeks"):
        console.warn("Hurt: %s (%sw). Fighting through is a choice." % (inj.get("area"), inj.get("weeks")))
        if console.ask("Fight anyway? A yes / B no: ").strip().upper() != "A":
            return
        fighter.energy = max(0, fighter.energy - 10)
    console.header("🔍 FINDING A FIGHT")
    if getattr(fighter, "suspension_weeks", 0) > 0:
        console.warn(f"🚫 You cannot compete while suspended ({fighter.suspension_weeks} week(s) remaining).")
        console.pause(1)
        return

    from . import v08
    if not fighter.pro_debut and fighter.amateur_record[0] >= fighter.amateur_wins_cap:
        console.gold("Amateur win cap. Time to turn pro.")
        turn_pro(console, fighter)
        return
    if v08.turn_pro_ready(fighter) and not v08.turn_pro_on_cooldown(fighter):
        console.gold("You can turn pro (5 amateur bouts). Later is smarter.")
        if console.ask("Open turn-pro now? A yes / B later: ").strip().upper() == "A":
            turn_pro(console, fighter)
            if fighter.pro_debut:
                return

    console.print("\nWEIGHT CLASS:", style="bold")
    options = get_weight_class_options(fighter)
    letters = "ABCDEFGH"
    for i, (_, _, desc) in enumerate(options):
        console.print("  %s) %s" % (letters[i], desc))
    picked = _pick_weight_option(console.ask("Choice letter or number > "), options)
    if picked is None:
        console.warn("Using stay (no cut).")
        action, chosen_wc = "stay", fighter.natural_weight_class
    else:
        action, chosen_wc, _ = picked

    fighter.fight_weight_class = chosen_wc
    fighter.weight_class = chosen_wc
    fighter._chose_cut = action in ("cut", "hard")
    from . import cut as _cut
    probe = _cut.cut_feasibility(fighter, chosen_wc)
    if action in ("cut", "hard"):
        console.print("Fight-week target: %.1fkg from %.1fkg walking (%.1f%%)." % (
            probe["cap"], probe["walk"], probe["frac"] * 100))
        if probe["band"] in ("hard", "brutal", "impossible"):
            console.warn(probe["label"].capitalize() + ". Diet/cut health now decide what you bring into the cage.")
        else:
            console.good(probe["label"].capitalize() + ".")
    else:
        console.good("Home division: " + chosen_wc)
    fighter.size_advantage = 0

    if fighter.pro_debut:
        inbox_night(console, fighter, pool)
        return

    opponent_fighter = _choose_opponent(console, fighter, pool)
    if opponent_fighter is None:
        return

    purse = _calc_purse(fighter, opponent_fighter)
    from . import v08
    flag = opponent_fighter.country_flag or "🌍"
    console.print(f"\nOpponent: {opponent_fighter.name} {flag} ({opponent_fighter.country})")
    console.print(f"Team: {opponent_fighter.team}")
    console.print("Him: " + v08.record_line(opponent_fighter))
    console.print("You: " + v08.record_line(fighter))
    console.print(f"Style: {getattr(opponent_fighter, 'style', 'MMA')}")
    walk_f = int(getattr(fighter,'walking_weight', fighter.weight) or fighter.weight)
    walk_o = int(getattr(opponent_fighter,'walking_weight', opponent_fighter.weight) or opponent_fighter.weight)
    console.print("Walk weight %skg vs %skg | purse $%s" % (walk_f, walk_o, purse))
    for line in v08.scout_lines(fighter, opponent_fighter):
        console.print(line)
    if v08.debut_penalty(fighter):
        console.warn("Soft debut penalty is on.")
    ans = console.ask("\n  A Camp (2 weeks) then fight   B Fight this week   C Decline > ").strip().upper()
    if ans == "C" or ans == "N":
        console.print("Declined this offer.")
        fighter.story_flags = fighter.story_flags or {}
        fighter.story_flags["declined_fight_week"] = fighter.week
        console.pause(1)
        return
    from . import booking
    offer = {
        "org": "Local Amateur",
        "room": "local",
        "date_week": fighter.week + (2 if ans != "B" else 0),
        "purse_win": purse,
        "purse_show": max(20, int(purse * 0.2)),
        "tag": "amateur",
        "opponent": opponent_fighter,
        "opponent_id": getattr(opponent_fighter, "fid", None),
        "matchmaker_id": "mm_fixer",
        "why": "local amateur card",
    }
    booking.set_booked(fighter, offer)
    try:
        from . import promotion_events
        promotion_events.attach_player_bout(pool, fighter, offer)
    except Exception:
        pass
    if ans != "B":
        from . import career as _career
        if hasattr(_career, "pick_and_start_camp"):
            _career.pick_and_start_camp(console, fighter, 2)
        console.good("Signed. Fight week %s. Train the camp." % offer["date_week"])
        return
    fight_result(console, fighter, opponent_fighter, purse, pool)
    fighter.booked_fight = None
    _final_autosave(fighter, pool, phase="amateur_bout_final")


def _resolve_booked_opponent(booked, pool):
    opp = booked.get("opponent")
    fid = booked.get("opponent_id")
    if pool is not None and fid:
        live = pool.get_by_id(fid)
        if live is not None:
            return live
    if opp is not None and not isinstance(opp, dict):
        return opp
    if isinstance(booked.get("opponent_snap"), dict):
        from .models import Fighter as _F
        return _F.from_dict(booked["opponent_snap"])
    return None


def inbox_night(console: GameConsole, fighter, pool) -> None:
    """Pro fight booking — the single place a pro takes a date.

    This is the only booking screen for professionals. The manager's read on
    each offer, purse negotiation, and contract status all live here rather
    than in a separate manager tab that could disagree with this one.
    """
    from . import booking, orgs, people, contracts
    from .systems15 import can_compete
    if not (getattr(fighter, "manager", None) or getattr(fighter, "manager_id", None)):
        console.warn("No manager. Matchmakers will not take your call.")
        console.print("Life → Manager, sign someone, then book through them.")
        people.manager_office_menu(console, fighter)
        return

    flags = getattr(fighter, "story_flags", None) or {}
    pending = flags.get("pending_renewal")
    if isinstance(pending, dict) and pending.get("org"):
        console.header("RE-SIGN", pending.get("org"))
        console.print("%s wants you back." % pending.get("org"))
        console.print("  %s fights · %sw · $%s win / $%s show" % (
            pending.get("fights"), pending.get("weeks"),
            pending.get("purse_win"), pending.get("purse_show")))
        clauses = list(pending.get("clauses") or [])
        console.print("  %s · %s" % ("exclusive" if pending.get("exclusive", True) else "non-exclusive",
                      ", ".join(x.replace("_", " ") for x in clauses) if clauses else "no special clauses"))
        console.print("  A) Re-sign")
        console.print("  N) Negotiate contract")
        console.print("  B) Walk — free agent")
        console.print("  X) Not now")
        pick = console.ask("Deal > ").strip().upper()
        if pick == "N":
            console.print("  A) More money   B) Fewer fights   C) Shorter term")
            console.print("  D) Short-notice premium   E) Title purse escalator")
            console.print("  F) Ask for non-exclusivity")
            ask = {"A":"money","B":"fights","C":"term","D":"short_notice",
                   "E":"title_escalator","F":"nonexclusive"}.get(
                       console.ask("Ask > ").strip().upper())
            if ask:
                ok, changed, line = contracts.negotiate(fighter, pending, ask)
                flags["pending_renewal"] = changed
                console.good(line) if ok else console.warn(line)
            console.pause(0.8)
            return
        if pick == "A":
            console.good(contracts.accept_renewal(fighter))
            console.pause(0.8)
            return
        if pick == "B":
            console.warn(contracts.decline_renewal(fighter))
            console.pause(0.8)
        else:
            console.print("Deal stays on the table.")

    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week"):
        if fighter.week >= int(booked["date_week"]):
            booker_night(console, fighter, pool)
        else:
            console.header("BOOKED", booked.get("org", ""))
            from .systems15 import opp_label
            wks = int(booked["date_week"]) - fighter.week
            console.print("vs %s" % opp_label(booked))
            console.print("Fight week %s — %s week(s) out." % (booked["date_week"], wks))
            if booked.get("title"):
                console.gold("TITLE FIGHT.")
            if int(getattr(fighter, "camp_weeks_remaining", 0) or 0) > 0:
                console.print("Camp: %s, %sw left." % (
                    getattr(fighter, "camp_focus", "general"),
                    fighter.camp_weeks_remaining))
            console.print("Train, rest, and make the date. One fight at a time.")
            console.pause(0.8)
        return

    why = can_compete(fighter)
    if why:
        console.warn(why)
        console.pause(0.9)
        return
    if fighter.fight_cooldown > 0:
        console.warn("Recovery: %s week(s)." % fighter.fight_cooldown)
        console.pause(0.8)
        return

    cold = booking.booker_cold(fighter)
    if cold:
        console.warn("Matchmaker is cold after your last decline. Wait %s week(s)." % cold)
        console.pause(0.8)
        return

    deal = contracts.active(fighter)
    offers = orgs.inbox(fighter, n=3, pool=pool) or []
    # An open Contender Series invitation outranks everything on the board.
    from . import dwcs as _dwcs
    if _dwcs.has_invite(fighter):
        shot = booking.build_offer(fighter, pool=pool, org_id="DWCS")
        shot["org"] = "DWCS"
        shot["dwcs"] = True
        shot["tag"] = "contender series"
        shot["why"] = "prove yourself — a win alone does not sign you"
        offers.insert(0, shot)
    # Exclusivity is hard. Previously this filtered locked offers but then
    # fell back to the locked list when everything was filtered out, which
    # let a signed fighter take an outside date anyway.
    legal, blocked = [], []
    for o in offers:
        allowed, reason = contracts.can_accept(fighter, str(o.get("org") or ""))
        (legal if allowed else blocked).append((o, reason))
    if not legal:
        wins = int((fighter.pro_record or [0])[0])
        if deal:
            home = deal.get("org")
        elif wins < 2:
            home = "Local Fight Nights"
        else:
            home = booking.org_for_room(fighter)
        forced = booking.build_offer(fighter, pool=pool, org_id=home)
        legal = [(forced, "")]

    console.header("FIGHT OFFERS", contracts.line(fighter))
    if deal:
        console.print("Under contract: %s" % contracts.line(fighter))
    for i, (off, _r) in enumerate(legal):
        letter = "ABC"[i] if i < 3 else str(i + 1)
        opp = off.get("opponent")
        console.print("  %s) %s  vs %s" % (
            letter, off.get("org"), getattr(opp, "name", "?")))
        console.print("     %s · $%s win / $%s show · fight week %s (%sw out)" % (
            off.get("tag"), off.get("purse_win"), off.get("purse_show"),
            off.get("date_week"), max(0, int(off.get("date_week", 0)) - fighter.week)))
        if off.get("career_opportunity"):
            console.print("     Career: %s · risk %s · upside %s/5" % (
                off.get("career_opportunity"), off.get("career_risk", "normal"),
                off.get("career_upside", 1)))
        if off.get("promotion_identity"):
            console.print("     %s identity: %s" % (off.get("org"), off.get("promotion_identity")), style="dim")
        if off.get("title"):
            role = off.get("title_role") or "challenger"
            console.gold("     TITLE FIGHT — %s %s (%s)." % (
                off.get("org"), off.get("weight_class") or getattr(fighter, "fight_weight_class", None) or getattr(fighter, "weight_class", ""), role))
        if off.get("dwcs"):
            console.gold("     CONTENDER SERIES — one fight, outside your contract.")
            console.print("     Win impressively and you leave with a UFC deal.")
            console.print("     Win badly and you leave with a handshake.")
        if off.get("opponent") is not None:
            console.print("     scout: %s" % booking.scout_one_liner(off["opponent"]))
        try:
            from .systems17 import manager_on_offer
            console.print("     %s" % manager_on_offer(fighter, off))
        except Exception:
            pass
    for off, reason in blocked:
        console.print("  --) %s — BLOCKED. %s" % (off.get("org"), reason), style="dim")
    console.print("  X) Take no fight this week")

    raw = console.ask("\n  Offer > ").strip().upper()
    if raw in ("X", ""):
        fighter.booker_decline_week = fighter.week
        org = legal[0][0].get("org") if legal else getattr(fighter, "organization", "")
        people.cool_matchmaker(fighter, org or "LFA", -8)
        console.print("Passed on the card. The matchmaker cooled on you.")
        console.pause(0.8)
        return
    idx = "ABC".find(raw[:1])
    if idx < 0 or idx >= len(legal):
        console.warn("No such offer.")
        console.pause(0.6)
        return
    offer = dict(legal[idx][0])

    # Second, separate question. Previously the offer letter was reused as the
    # action, so picking the SECOND offer (B) silently meant "sim it now" and
    # skipped the camp entirely.
    while True:
        console.print("")
        console.print("  A) Sign it — start camp for fight week %s" % offer.get("date_week"))
        console.print("  N) Negotiate the purse first")
        console.print("  X) Back out")
        act = console.ask("  Decision > ").strip().upper()
        if act == "N":
            ok, purse, line = people.negotiate_purse(fighter, offer)
            console.print(line)
            if ok:
                offer["purse_win"] = int(purse)
                offer["purse_show"] = max(40, int(purse * 0.20))
            continue
        if act == "A":
            break
        if act in ("X", "B", "0"):
            return
        console.warn("Choose A, N, or X.")

    allowed, reason = contracts.can_accept(fighter, str(offer.get("org") or ""))
    if not allowed:
        console.warn(reason)
        console.pause(1.0)
        return

    # Accepting a fight offer is NOT the same thing as signing an exclusive
    # promotional contract. 1.30 could blur those two states and make a player
    # appear automatically signed after one Balkan Combat date. Contracts are
    # created only through an explicit contract/signing action (or a feeder
    # conversion such as DWCS -> UFC).
    if not contracts.active(fighter):
        console.info("One-fight booking accepted. You remain a free agent unless you separately sign promotional terms.")

    booking.set_booked(fighter, offer)
    weeks = max(1, int(offer["date_week"]) - fighter.week)
    try:
        from . import promotion_events
        promotion_events.attach_player_bout(pool, fighter, offer)
    except Exception:
        pass
    from . import career as _career
    _career.pick_and_start_camp(console, fighter, weeks)
    console.good("Signed for %s. Fight week %s — %s weeks of camp." % (
        offer.get("org"), offer["date_week"], weeks))
    console.print("Come back each week and train. Fight night fires on week %s." % offer["date_week"])
    people.warm_matchmaker(fighter, str(offer.get("org") or "LFA"), 3)
    console.auto_pause("Signed")


def booker_night(console: GameConsole, fighter, pool) -> None:
    """Fight-week executor. Offering dates is inbox_night for pros."""
    from . import booking, v08
    if fighter.health < 12:
        console.warn("Too hurt to take a date. Rest.")
        return
    inj = getattr(fighter, "injury", None) or {}
    if inj.get("severity") == "serious" and inj.get("weeks", 0) > 0:
        console.warn("Serious injury. Booker will not date you (%sw)." % inj.get("weeks"))
        return
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week") and fighter.week >= int(booked["date_week"]):
        opp = _resolve_booked_opponent(booked, pool)
        if opp is None:
            console.warn("Card lost the opponent. Book again.")
            fighter.booked_fight = None
            return
        purse = int(booked.get("purse_win") or 280)
        fighter._show_purse = int(booked.get("purse_show") or int(purse * 0.2))
        was_dwcs = bool(booked.get("dwcs")) or str(booked.get("org") or "") == "DWCS"
        fighter._pending_title = bool(booked.get("title"))
        fighter._bout_meta = dict(booked)
        try:
            from . import promotion_events
            lines = promotion_events.card_lines(pool, booked.get("event_id"))
            fighter._bout_event_name = promotion_events.event_label(pool, booked.get("event_id"))
            if lines:
                console.header("EVENT CARD", lines[0])
                for line in lines[1:]:
                    console.print("  " + line)
        except Exception:
            fighter._bout_event_name = ""
        fighter._bout_org = booked.get("org")
        fighter.booked_fight = None
        fighter.camp_for_bout = 0
        fight_result(console, fighter, opp, purse, pool)
        fighter._bout_event_name = ""
        bout = getattr(fighter, "_last_outcome", None)
        if was_dwcs or booking.current_room(fighter) == "dwcs":
            # Winning the Contender Series is not enough on its own — the
            # performance is graded, and a grinding decision earns nothing.
            from . import dwcs as _dwcs
            _dwcs.resolve(fighter, bout, console)
        else:
            booking.maybe_promote(fighter)
        _final_autosave(fighter, pool, phase="booked_bout_final")
        return
    if booked:
        console.header("BOOKED", booked.get("org", ""))
        console.print("Date week %s (now %s). Camp is running." % (booked.get("date_week"), fighter.week))
        console.pause(0.8)
        return
    if getattr(fighter, "pro_debut", False):
        inbox_night(console, fighter, pool)
        return
    # amateur leftover — should not be the pro path
    offer = booking.build_offer(fighter, pool)
    booking.set_booked(fighter, offer)
    console.good("Local date week %s." % offer["date_week"])


def _rival_snapshot(fighter, opponent):
    return {
        "name": opponent.name,
        "fid": getattr(opponent, "fid", None),
        "heat": 25,
        "fights": 1,
        "last_week": getattr(fighter, "week", 1),
        "country": getattr(opponent, "country", None),
        "am": list(opponent.amateur_record or [0, 0, 0]),
        "pro": list(opponent.pro_record or [0, 0, 0]),
        "pro_debut": bool(getattr(opponent, "pro_debut", False)),
        "style": getattr(opponent, "style", None),
    }


def _rebuild_rival(fighter, pool):
    """Same person, same career stage. Never a random 15-2 vet."""
    from . import booking
    rec = next((r for r in (fighter.rivalries or []) if r.get("name") == fighter.rival), {}) or {}
    rid = getattr(fighter, "rival_id", None) or rec.get("fid")
    opp = pool.get_by_id(rid) if pool is not None and rid and hasattr(pool, "get_by_id") else None
    if opp is not None and opp is not fighter and booking.opponent_fits(fighter, opp):
        return opp
    bias = rec.get("country") or fighter.country
    opp = generate_random_opponent(fighter, country_bias=bias)
    opp.name = fighter.rival
    if rid:
        opp.fid = rid
        fighter.rival_id = rid
    if rec.get("am"):
        opp.amateur_record = list(rec["am"])
    if fighter.pro_debut:
        opp.pro_debut = True
        pw = int((fighter.pro_record or [0, 0, 0])[0])
        saved = list(rec.get("pro") or [0, 0, 0])
        if rec.get("pro_debut") and saved and saved[0] <= pw + 4:
            opp.pro_record = saved
        else:
            amw = int((rec.get("am") or [0, 0, 0])[0])
            opp.pro_record = [max(0, min(pw + 2, amw // 2)), min(2, int((rec.get("am") or [0, 0, 0])[1])), 0]
    else:
        opp.pro_debut = False
        opp.pro_record = [0, 0, 0]
        if rec.get("am"):
            opp.amateur_record = list(rec["am"])
    # A rebuilt rival must always be a bookable peer. The generator can drift
    # a few points above the matchmaking window, so pull the preview back
    # inside it rather than returning an opponent the booker would reject.
    from . import constants as _C
    for _ in range(6):
        if booking.opponent_fits(fighter, opp):
            break
        for sk in _C.SKILLS:
            cur = int(getattr(opp, sk, 40) or 40)
            setattr(opp, sk, max(12, cur - 3))
    return opp


def _choose_opponent(console: GameConsole, fighter, pool):
    from . import booking
    # Rival rematch only if they are still a fair fight
    if fighter.rival and story.rival_heat(fighter) >= 25:
        preview = _rebuild_rival(fighter, pool)
        same_stage = bool(getattr(preview, "pro_debut", False)) == bool(fighter.pro_debut)
        fair = same_stage and booking.opponent_fits(fighter, preview)
        if fair:
            console.print("Rival heat %s with %s." % (story.rival_heat(fighter), fighter.rival))
            if console.ask("Book the rematch? (A=Yes, B=Other fight): ").strip().upper() == "A":
                console.gold("Rematch signed: %s" % fighter.rival)
                return preview
        else:
            console.info("%s moved on. Not a fair rematch this week." % fighter.rival)

    if fighter.pro_debut and fighter.pro_record[0] >= 4 and fighter.fame >= 10 and not fighter.story_flags.get("showcase_done"):
        console.gold("SHOWCASE invite (contender night). Win looks good. Not a UFC contract.")
        if console.ask("Take it? A yes / B no: ").strip().upper() == "A":
            fighter.story_flags["showcase_done"] = True
            fighter.narrative_tags = list(fighter.narrative_tags or []) + ["prospect"]
            opp = generate_random_opponent(fighter)
            for s in C.SKILLS:
                setattr(opp, s, min(95, getattr(opp, s) + 8))
            return opp
    from . import booking
    if booking.can_use_ranked_picker(fighter):
        top = pool.rankings.get(fighter.weight_class, [])[:5]
        champ = pool.champions.get(fighter.weight_class)
        title_shot = champ and champ is not fighter and fighter in top[:2]
        if title_shot:
            console.gold("🏆 TITLE FIGHT OPPORTUNITY!")
            console.print(f"You are ranked in the top 2 and can challenge the champion: {champ.name}")
            if console.ask("\n  A) Fight for the title!  B) Fight a regular opponent > ").strip().upper() == "A":
                fighter._pending_title = True
                return champ
            return find_opponent_from_pool(fighter, pool)

        top_opponents = pool.get_ranked_opponents(fighter.weight_class, exclude=fighter, limit=5)
        if not top_opponents:
            console.print("No ranked opponents available. Fighting a random opponent.")
            return generate_random_opponent(fighter)
        console.print("\nRanked opponents:", style="bold")
        for i, f in enumerate(top_opponents):
            console.print(f"  {i + 1}) {f.name} ({f.country_flag})  "
                          f"Record: {f.pro_record[0]}-{f.pro_record[1]}-{f.pro_record[2]}  "
                          f"Style: {getattr(f, 'style', 'MMA')}")
        choice = console.ask("\n  Choice (number, or X for random) > ").strip().upper()
        if choice == "X":
            return generate_random_opponent(fighter)
        try:
            return top_opponents[int(choice) - 1]
        except (ValueError, IndexError):
            return generate_random_opponent(fighter)

    live = find_opponent_from_pool(fighter, pool)
    if live is not None and getattr(live, "fid", None):
        return live
    bias = None if fighter.pro_debut else fighter.country
    opponent_fighter = generate_random_opponent(fighter, country_bias=bias)
    if pool is not None:
        if not getattr(opponent_fighter, "fid", None):
            opponent_fighter.fid = "npc_%s" % getattr(pool, "next_id", 9000)
            pool.next_id = int(getattr(pool, "next_id", 9000)) + 1
        pool.fighters.append(opponent_fighter)
    tier_bonus = fighter.promotion_tier * 2
    for stat in ("striking", "kicks", "grappling", "submissions"):
        setattr(opponent_fighter, stat, min(95, getattr(opponent_fighter, stat) + tier_bonus))
    return opponent_fighter


def _calc_purse(fighter, opponent, is_title: bool = False) -> int:
    base = 100 + fighter.promotion_tier * 200 + fighter.fame * 2 + fighter.press_hype
    if opponent:
        rec = opponent.pro_record if fighter.pro_debut else opponent.amateur_record
        base += rec[0] * 10
    multiplier = 1.0
    for org in data.PRO_ORGS:
        if fighter.promotion_tier == org.get("tier", 0):
            multiplier = org.get("purse_multiplier", 1.0)
            break
    multiplier *= story.purse_multiplier(fighter, opponent, is_title=is_title)
    return int(base * multiplier)


def _ufc_title_introductions(console, fighter, opponent, pool=None, weight_class=None) -> None:
    """Bruce-style championship order without impersonating a real announcer."""
    from .nicknames import display_name
    wc = weight_class or getattr(fighter, "fight_weight_class", None) or fighter.weight_class
    champ = pool.belt_holder("UFC", wc) if pool is not None and hasattr(pool, "belt_holder") else None
    if champ is None and pool is not None:
        champ = getattr(pool, "champions", {}).get(wc)
    challenger = opponent if champ is fighter else fighter
    champion = fighter if champ is fighter else opponent
    console.header("UFC CHAMPIONSHIP", "%s · five rounds" % wc)
    console.print("Introducing first: the challenger.")
    for who, role in ((challenger, "CHALLENGER"), (champion, "CHAMPION")):
        rec = list(getattr(who, "pro_record", None) or [0, 0, 0])
        console.section(role)
        from .ui import wrap_text
        for line in wrap_text(display_name(who), min(42, int(getattr(console, "width", 44) or 44))):
            console.print(line)
        console.print("%s · %s-%s-%s · %skg" % (
            getattr(who, "country", ""), rec[0], rec[1], rec[2], getattr(who, "weight", "?")))
    console.gold("For the UFC championship — the fight starts now.")


def _title_introductions(console, fighter, opponent, org: str, weight_class: str, pool=None) -> None:
    """Promotion-neutral championship presentation for non-UFC title bouts."""
    champ = pool.belt_holder(org, weight_class) if pool is not None and hasattr(pool, "belt_holder") else None
    challenger = opponent if champ is fighter else fighter
    champion = fighter if champ is fighter else opponent
    console.header("%s CHAMPIONSHIP" % org.upper(), "%s · five rounds" % weight_class)
    for who, role in ((challenger, "CHALLENGER"), (champion, "CHAMPION")):
        rec = list(getattr(who, "pro_record", None) or [0,0,0])
        console.section(role)
        console.print("%s · %s" % (getattr(who, "name", ""), getattr(who, "country", "")))
        console.print("%s-%s-%s · %scm reach · %s" % (rec[0],rec[1],rec[2],
                      int(getattr(who, "reach", 0) or 0), getattr(who, "stance", "Orthodox") or "Orthodox"))
    console.gold("The %s %s championship is on the line." % (org, weight_class))


def _post_fight_summary(console, fighter, opponent, result: str, method: str, bout=None, booked=None) -> None:
    """One consolidated card before the player returns to the weekly loop."""
    booked = booked or {}
    console.header("POST-FIGHT SUMMARY", str(booked.get("event_name") or booked.get("org") or "Fight complete"))
    console.gold("%s — %s" % (result.upper(), method)) if result == "Win" else console.warn("%s — %s" % (result.upper(), method)) if result == "Loss" else console.print("DRAW — %s" % method)
    console.print("  vs %s · performance %.1f" % (getattr(opponent, "name", "Opponent"), float(getattr(fighter, "performance_rating", 0.0) or 0.0)))
    if bout is not None:
        st=bout.f_stats.as_dict(); ost=bout.o_stats.as_dict()
        console.section("FIGHT STATS")
        console.print("  Strikes %s/%s  vs  %s/%s" % (st.get("strikes_landed",0),st.get("strikes_attempted",0),ost.get("strikes_landed",0),ost.get("strikes_attempted",0)))
        console.print("  Takedowns %s/%s  vs  %s/%s" % (st.get("takedowns_landed",0),st.get("takedowns_attempted",0),ost.get("takedowns_landed",0),ost.get("takedowns_attempted",0)))
        console.print("  KD %s-%s · Control %ss-%ss · Sub attempts %s-%s" % (st.get("knockdowns",0),ost.get("knockdowns",0),st.get("control_sec",0),ost.get("control_sec",0),st.get("submission_attempts",0),ost.get("submission_attempts",0)))
    pr=list(getattr(fighter,"pro_record",None) or [0,0,0]); ar=list(getattr(fighter,"amateur_record",None) or [0,0,0])
    console.section("CAREER IMPACT")
    console.print("  Record: Pro %s-%s-%s · Amateur %s-%s-%s" % (*pr,*ar))
    console.print("  Money $%s · Fame %s · Legacy %s" % (format(int(getattr(fighter,"money",0) or 0),","),int(getattr(fighter,"fame",0) or 0),int(getattr(fighter,"legacy_score",0) or 0)))
    dmg=dict(getattr(fighter,"damage",None) or {})
    if int(dmg.get("total",0) or 0) or int(getattr(fighter,"fight_cooldown",0) or 0):
        console.print("  Recovery: %sw · damage %s · cuts %s" % (int(getattr(fighter,"fight_cooldown",0) or 0),dmg.get("total",0),dmg.get("cuts",0)))
    adjustments=list(getattr(fighter,"last_fight_adjustments",None) or [])
    if adjustments:
        console.section("TACTICAL ADJUSTMENTS")
        seen=[]
        for line in adjustments:
            if line and line not in seen: seen.append(line)
        for line in seen[-3:]: console.print("  " + str(line))


def fight_result(console: GameConsole, fighter, opponent, purse: int, pool) -> None:
    is_title = bool(getattr(fighter, "_pending_title", False))
    is_amateur = not fighter.pro_debut
    fighter._pending_title = False
    ctx = story.context_label(fighter, opponent, is_title=is_title)
    # Purse must exist before a missed-weight percentage can be charged.
    if not purse or int(purse) < 40:
        purse = _calc_purse(fighter, opponent, is_title=(ctx == "TITLE FIGHT"))
    elif ctx == "TITLE FIGHT":
        purse = int(purse * 1.25)
    console.header("⚔️ FIGHT NIGHT", ctx)
    flag = opponent.country_flag or "🌍"
    console.print(f"{fighter.name} {fighter.country_flag} vs {opponent.name} {flag}")
    console.print(f"Venue: {get_venue(fighter.promotion_tier)}  |  {ctx}")
    booked_meta = dict(getattr(fighter, "_bout_meta", None) or {})
    fight_wc = str(booked_meta.get("weight_class") or getattr(fighter, "fight_weight_class", None) or fighter.weight_class)
    old_rank = None
    try:
        from . import phase3
        old_rank = phase3.rank_snapshot(fighter, pool, booked_meta.get("org") or fighter.organization, fight_wc)
        phase3.fight_week_open(console, fighter, opponent, booked_meta, is_title=is_title)
    except Exception:
        pass
    try:
        story.press_conference(console, fighter, opponent, booked_meta)
    except Exception:
        pass

    # 1.24: one weigh-in pipeline for both amateur and pro.  Old versions ran
    # an immediate cut in find_fight() and then attempted a second cut here;
    # this block also used is_amateur before it existed, so the broad except
    # silently skipped the real weigh-in.
    from . import cut
    wi = cut.weigh_in(fighter, console)
    fighter._weigh_in = wi
    owi = cut.weigh_in(opponent, None)
    opponent._weigh_in = owi
    if not wi["made"]:
        if not is_amateur:
            fighter.money = fighter.money - int(purse * wi["penalty"] / 100)
        from .notoriety import add_fame
        add_fame(fighter, -1, "missed weight")
        fighter.narrative_tags = list(fighter.narrative_tags or []) + ["weight_trouble"]
        try:
            from . import memory as _mem, npc as _npc, people as _ppl
            pr = _ppl.promoter_for(getattr(fighter, "organization", "") or "")
            if pr is not None:
                _mem.remember(fighter, _npc.npc_id(pr), "missed_weight", "%.1f over" % wi["over_kg"])
        except Exception:
            pass
    elif wi["cut_drain"] >= 8:
        console.print("You made it, but the %.1f%% cut cost %s fight-night energy." % (wi["cut_pct"], wi["cut_drain"]))
    gap = cut.size_gap(fighter, opponent)
    console.print("Scale %.1f → cage %.1fkg | opponent ~%.1fkg | size %+d" % (
        wi["scale_kg"], wi["cage_kg"], owi["cage_kg"], gap))
    try:
        from . import phase3
        phase3.staredown(console, fighter, opponent, booked_meta, is_title=is_title)
    except Exception:
        pass

    if ctx == "RIVALRY FIGHT":
        console.gold(f"Heat {story.rival_heat(fighter)} — this one means more.")
        fighter.press_hype = min(100, fighter.press_hype + 4)
        fighter.confidence = min(100, fighter.confidence + 3)
    elif ctx == "TITLE FIGHT":
        console.gold("Championship stakes. Purse and hype are up.")
        fighter.press_hype = min(100, fighter.press_hype + 10)
        title_org = str(booked_meta.get("org") or getattr(fighter, "_bout_org", "") or fighter.organization or "")
        if title_org == "UFC":
            _ufc_title_introductions(console, fighter, opponent, pool, fight_wc)
        elif title_org:
            _title_introductions(console, fighter, opponent, title_org, fight_wc, pool)
    getattr(console, "section", lambda title: console.print("\n" + title))("GAMEPLAN")
    plans = {
        "A": ("Pressure", {"target":"head","pace":"high","td":"Opportunistic","range":"pocket","defense":"guard"}, "Walk him down; power, volume and clinch pressure. High gas demand."),
        "B": ("Counter", {"target":"head","pace":"low","td":"Safe","range":"boxing","defense":"counter"}, "Make him lead, punish misses and protect the gas tank."),
        "C": ("Wrestle-heavy", {"target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"movement"}, "Chain entries, mat returns, rides and top position."),
        "D": ("Kickboxing Outside", {"target":"body","pace":"mid","td":"Safe","range":"kicking","defense":"movement"}, "Jab/teep/kick at range and avoid long grappling exchanges."),
        "E": ("Submission Hunter", {"target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"guard"}, "Get to the mat, advance position and hunt the finish."),
        "F": ("Clinch & Control", {"target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"guard"}, "Close distance, dirty box, trip/throw and control."),
        "G": ("Balanced", {"target":"body","pace":"mid","td":"Opportunistic","range":"boxing","defense":"guard"}, "No hard bias; adapt to the fight."),
        "H": ("Anti-Wrestling", {"target":"head","pace":"mid","td":"Safe","range":"boxing","defense":"movement"}, "Hold center, punish entries, sprawl and disengage."),
        "I": ("Body Attack", {"target":"body","pace":"mid","td":"Opportunistic","range":"boxing","defense":"guard"}, "Invest downstairs and attack the opponent's gas tank."),
        "J": ("Leg Kick Attack", {"target":"legs","pace":"mid","td":"Safe","range":"kicking","defense":"movement"}, "Damage mobility with low kicks while managing range."),
        "K": ("Taekwondo Kicking", {"target":"head","pace":"mid","td":"Safe","range":"kicking","defense":"movement"}, "Long stance, side kicks and high-value spinning attacks off clean setups."),
    }
    recommended = recommend_gameplan(fighter, opponent)
    preferred = str(getattr(fighter, "preferred_gameplan", "Balanced") or "Balanced")
    for k,(name,_spec,desc) in plans.items():
        tags=[]
        if name == recommended: tags.append("COACH")
        if name == preferred and name != recommended: tags.append("LAST")
        suffix = (" [" + "/".join(tags) + "]") if tags else ""
        console.print("  %s) %-19s%s" % (k, name, suffix))
        console.print("     " + desc, style="dim")
    console.print("  R) Use coach recommendation: %s" % recommended)
    name_to_key={v[0]:k for k,v in plans.items()}
    raw=(console.ask("Plan (Enter = %s) > " % preferred) or "").strip().upper()
    pick = name_to_key.get(preferred, "G") if not raw else (name_to_key.get(recommended,"G") if raw == "R" else raw)
    gameplan, base_plan, _desc = plans.get(pick, plans[name_to_key.get(preferred,"G")])
    plan=dict(base_plan); plan["name"]=gameplan
    impact = {
        "Pressure":"↑ pressure/power/clinch · ↑ gas use",
        "Counter":"↑ counters/sprawls · ↓ reckless entries",
        "Wrestle-heavy":"↑ shots/chains/rides · ↓ power hunting",
        "Kickboxing Outside":"↑ range kicks/teeps · ↓ wrestling entries",
        "Submission Hunter":"↑ passes/back takes/submissions",
        "Clinch & Control":"↑ clinch/trips/control · ↓ long range",
        "Balanced":"adaptive mix · no major bias",
        "Anti-Wrestling":"↑ movement/sprawls/entry punishment",
        "Body Attack":"↑ body offense · targets opponent gas",
        "Leg Kick Attack":"↑ low kicks · targets mobility",
        "Taekwondo Kicking":"↑ side/high/spinning kicks · ↑ range control · ↑ counter risk on misses",
    }.get(gameplan, "")
    card = [
        "%s%s" % (gameplan, " · COACH PICK" if gameplan == recommended else ""),
        "Target %s · Pace %s · TD %s" % (plan["target"], plan["pace"], plan["td"]),
        "Range %s · Defense %s" % (plan["range"], plan["defense"]),
        impact,
    ]
    if hasattr(console, "panel"):
        console.panel("TACTICAL CARD", card)
    else:
        console.print("TACTICAL CARD")
        for line in card: console.print("  " + line)
    if (console.ask("A) Accept  E) Edit details > ") or "A").strip().upper() == "E":
        console.print("Target A head  B body  C legs")
        plan["target"] = {"A":"head","B":"body","C":"legs"}.get(console.ask("Target > ").strip().upper(), plan["target"])
        console.print("Pace A low  B mid  C high")
        plan["pace"] = {"A":"low","B":"mid","C":"high"}.get(console.ask("Pace > ").strip().upper(), plan["pace"])
        console.print("TD A safe  B opportunistic  C aggressive")
        plan["td"] = {"A":"Safe","B":"Opportunistic","C":"Aggressive"}.get(console.ask("TD > ").strip().upper(), plan["td"])
        console.print("Range A outside  B kicking  C boxing  D pocket")
        plan["range"] = {"A":"outside","B":"kicking","C":"boxing","D":"pocket"}.get(console.ask("Range > ").strip().upper(), plan["range"])
        console.print("Defense A movement  B guard  C counter")
        plan["defense"] = {"A":"movement","B":"guard","C":"counter"}.get(console.ask("Defense > ").strip().upper(), plan["defense"])
    tgt, pace, td = plan["target"], plan["pace"], plan["td"]
    preferred_range, defense = plan["range"], plan["defense"]
    fighter._fight_plan = plan
    fighter.preferred_gameplan = gameplan
    fighter.last_gameplan = dict(plan)
    try:
        from . import telemetry
        telemetry.decision("fight_plan", choice=gameplan, target=tgt, pace=pace, takedowns=td,
                           preferred_range=preferred_range, defense=defense, recommended=recommended,
                           opponent=getattr(opponent, "name", ""), opponent_id=getattr(opponent, "fid", None))
        telemetry.begin_fight(fighter, opponent, org=getattr(fighter, "_bout_org", None) or fighter.organization or "",
                              rules="mma", rounds=(3 if not fighter.pro_debut else (5 if is_title or fighter.promotion_tier >= 10 else 3)),
                              gameplan=gameplan)
    except Exception:
        pass
    _detail = getattr(fighter, "fight_details", "Round") or "Round"
    fighter.fight_details = _pick_watch_mode(console, _detail)

    rounds = 3 if not fighter.pro_debut else (5 if is_title or fighter.promotion_tier >= 10 else 3)
    if is_title:
        fighter._pending_title = True
    finish, f_score, o_score, technique_used = fight_mma(console, fighter, opponent, rounds, gameplan)
    fighter.fight_details = _detail
    fighter._pending_title = False
    bout = getattr(fighter, "_last_outcome", None)

    if bout is not None:
        if bout.winner == "player":
            outcome = "win_finish" if bout.finish_label else "win_decision"
        elif bout.winner == "opponent":
            outcome = "loss_finish" if bout.finish_label else "loss_decision"
        else:
            outcome = "draw"
        finish = bout.finish_label
        technique_used = bout.technique
    else:
        outcome = _resolve_outcome(finish, f_score, o_score)
    legacy_gain = _apply_outcome(console, fighter, opponent, outcome, finish, purse, is_amateur)
    if not is_amateur:
        from . import notoriety
        notoriety.add_fame(
            fighter,
            notoriety.bout_fame(fighter, opponent, result=outcome,
                                finish=bool(finish), booked=booked_meta),
            "fight exposure",
        )
        try:
            from . import living_careers
            line = living_careers.resolve_player_opportunity(fighter, booked_meta, outcome, finish or "")
            if line:
                console.good(line)
        except Exception:
            pass

    if pool is not None and not is_amateur and hasattr(pool, "award_belt"):
        try:
            from . import identity as _id
            booked = getattr(fighter, "booked_fight", None) or {}
            org = booked.get("org") or getattr(fighter, "_bout_org", None) or _id.canonical_org(fighter)
            wc = fight_wc
            champ = pool.belt_holder(org, wc) if hasattr(pool, "belt_holder") else None
            title = bool(booked.get("title") or is_title or champ in (opponent, fighter))
            if title and outcome in ("win_finish", "win_decision"):
                if champ is fighter and hasattr(pool, "record_title_defense"):
                    pool.record_title_defense(org, wc, fighter, opponent)
                else:
                    pool.award_belt(org, wc, fighter, defeated=champ or opponent)
                console.gold("%s %s belt." % (org, wc))
            elif title and outcome in ("loss_finish", "loss_decision") and champ is fighter:
                pool.award_belt(org, wc, opponent, defeated=fighter)
            elif title and outcome in ("loss_finish", "loss_decision") and champ is opponent:
                if hasattr(pool, "record_title_defense"):
                    pool.record_title_defense(org, wc, opponent, fighter)
        except Exception:
            pass

    fighter.legacy_score = max(0, fighter.legacy_score + legacy_gain)
    from . import v08
    fighter.last_week_note = "fight " + (finish or "decision")
    console.print(f"Money: ${fighter.money} | Fame: {fighter.fame} | Legacy: {fighter.legacy_score}")

    post_fight_analysis(console, fighter, opponent, finish, rounds, f_score, o_score, technique_used)
    result = "Win" if outcome.startswith("win") else "Loss" if outcome.startswith("loss") else "Draw"
    if not is_amateur:
        try:
            story.post_fight_interview(console, fighter, opponent, result, booked_meta)
        except Exception:
            pass
    method = (bout.method if bout is not None else (finish.replace(" Loss", "") if finish else "Decision"))
    sport = getattr(bout, "sport", None) or "mma"
    event = getattr(fighter, "_bout_event_name", None) or getattr(fighter, "_bout_org", None) or fighter.organization or ""
    from . import record as _rec
    _rec.commit(fighter, opponent.name, result, method, max(1, rounds),
                event=event, stats=bout.f_stats.as_dict() if bout is not None else None,
                opponent_stats=bout.o_stats.as_dict() if bout is not None else None,
                sport=sport, amateur=is_amateur)
    try:
        from . import promotion_events
        promotion_events.complete_player_bout(pool, booked_meta.get("event_id"), result, opponent.name,
                                              method=method, rating=float(getattr(fighter, "performance_rating", 0.0) or 0.0))
    except Exception:
        pass
    try:
        from . import nicknames
        nicknames.offer_player(console, fighter, pool)
    except Exception:
        pass
    try:
        from . import telemetry
        _fb = getattr(bout, "f_body", None) if bout is not None else None
        _ob = getattr(bout, "o_body", None) if bout is not None else None
        telemetry.end_fight(
            result=result, method=method, round=getattr(bout, "end_period", rounds) if bout is not None else rounds,
            technique=getattr(bout, "technique", None) if bout is not None else technique_used,
            player_stats=bout.f_stats.as_dict() if bout is not None else {},
            opponent_stats=bout.o_stats.as_dict() if bout is not None else {},
            player_body={"loc": dict(getattr(_fb, "loc", {}) or {}), "cuts": dict(getattr(_fb, "cuts", {}) or {}),
                         "concussive": getattr(_fb, "concussive", 0)} if _fb is not None else {},
            opponent_body={"loc": dict(getattr(_ob, "loc", {}) or {}), "cuts": dict(getattr(_ob, "cuts", {}) or {}),
                           "concussive": getattr(_ob, "concussive", 0)} if _ob is not None else {})
    except Exception:
        pass
    console.print("Record: " + v08.record_line(fighter))
    try:
        from .systems17 import note_opponent
        note_opponent(fighter, opponent)
    except Exception:
        pass
    opp_res = "Loss" if result == "Win" else "Win" if result == "Loss" else "Draw"
    _rec.commit(opponent, fighter.name, opp_res, method, max(1, rounds),
                event=event,
                stats=bout.o_stats.as_dict() if bout is not None else None,
                opponent_stats=bout.f_stats.as_dict() if bout is not None else None,
                sport="mma", amateur=is_amateur)
    try:
        from . import perks
        perks.note_bout(fighter, bout, result, opponent)
        perks.evaluate(fighter, console, bout)
        perks.post_bout_career_bonus(fighter, opponent, result)
    except Exception:
        pass
    _handle_promotion(console, fighter, is_amateur)

    # What happened in the cage now follows you out of it.
    try:
        from . import damage as _dmg
        _bm = getattr(bout, "f_stats", None) and getattr(bout, "f_body", None)
        _hurt = _dmg.post_fight(fighter, getattr(bout, "f_body", None),
                                lost_badly=(result == "Loss" and bool(finish)),
                                console=console)
        if _hurt:
            console.section("AFTER THE FIGHT")
            console.print(_dmg.summary(fighter))
            out = _dmg.weeks_out(fighter)
            if out >= 3:
                console.print("You are not training properly for %s week(s)." % out)
                console.print("Physio or surgery will shorten it — see the life menu.")
    except Exception:
        pass

    # Camp sharpness and opponent study are bout-specific resources.
    fighter.camp_bonus = 0
    fighter.opponent_read = 0
    fighter.camp_preparation = {}
    opponent.camp_bonus = 0
    opponent.opponent_read = 0
    opponent.camp_preparation = {}
    fighter.fight_cooldown = 2
    if not is_amateur:
        try:
            from . import contracts
            contracts.note_fight(fighter, console)
        except Exception:
            pass
    fid = getattr(opponent, "fid", None)
    if fid:
        ids = list(getattr(fighter, "recent_opponent_ids", None) or [])
        ids.append(fid)
        fighter.recent_opponent_ids = ids[-8:]
        live = pool.get_by_id(fid) if pool is not None else None
        if live is None and pool is not None:
            pool.fighters.append(opponent)
            live = opponent
        if live is not None and live is not opponent:
            live.amateur_record = list(opponent.amateur_record)
            live.pro_record = list(opponent.pro_record)
            live.recent_results = list(getattr(opponent, "recent_results", None) or [])
            live.last_fight_stats = getattr(opponent, "last_fight_stats", {}) or {}
    if pool is not None:
        pool.update_rankings()
        if not is_amateur:
            try:
                from . import phase3
                phase3.post_event(console, fighter, opponent, result, method, pool, booked_meta, old_rank=old_rank)
            except Exception:
                pass
    try:
        _post_fight_summary(console, fighter, opponent, result, method, bout=bout, booked=booked_meta)
    except Exception:
        pass
    # Cross-division title dates temporarily change the fight class, not the
    # fighter's normal home division. The belt ledger remembers both straps.
    fighter.fight_weight_class = fighter.weight_class
    # Saving is owned by the *caller* after all contextual post-fight systems
    # (perks, DWCS grading, room promotion, tournament bookkeeping) finish.
    # 1.23 saved here too early and produced two different truths at week 205.
    console.auto_pause("Fight result")


def _final_autosave(fighter, pool, phase: str = "post_bout_final") -> None:
    if pool is None:
        return
    try:
        from . import persistence
        persistence.autosave(fighter, pool, phase=phase)
        persistence.autosave(fighter, pool, persistence.DEFAULT_SAVE, phase=phase)
    except Exception as e:
        try:
            from . import diagnostics
            diagnostics.log_error("post_fight_final_autosave", e)
        except Exception:
            pass


def _resolve_outcome(finish, f_score, o_score) -> str:
    if finish in ("KO", "TKO", "Submission", "Doctor Stoppage", "Corner Stoppage"):
        return "win_finish"
    if finish in ("KO Loss", "TKO Loss", "Submission Loss", "Doctor Stoppage Loss", "Corner Stoppage Loss"):
        return "loss_finish"
    if f_score > o_score:
        return "win_decision"
    if o_score > f_score:
        return "loss_decision"
    return "draw"


def _apply_outcome(console, fighter, opponent, outcome, finish, purse, is_amateur) -> int:
    """Money, morale, fame and streaks for a finished bout.

    This function must NOT touch W-L any more. Since 1.18 the official record
    is derived from fight_history by `record.commit()`, which runs later in
    fight_result(). The legacy in-place increments that used to live here were
    still running, so every pro bout was counted twice: a 4-1 opponent came out
    of one fight at 4-3, and a debuting player went 0-0 -> 2-0.

    Amateur records are still incremented here, because the amateur ledger is
    not derived from history.
    """
    fr = fighter.amateur_record if is_amateur else fighter.pro_record
    orr = opponent.amateur_record if is_amateur else opponent.pro_record
    # Pro W-L is owned by record.commit(). Amateur W-L is owned here.
    bump = is_amateur

    if outcome == "draw":
        console.print("It's a DRAW!")
        if bump:
            fr[2] += 1
            orr[2] += 1
        return 0

    if outcome in ("win_finish", "win_decision"):
        finish_bonus = outcome == "win_finish"
        console.good(f"🏆 {fighter.name} WINS" + (f" BY {finish.upper()}!" if finish_bonus else " by Decision!"))
        if bump:
            fr[0] += 1
            orr[1] += 1
        fighter.reputation += 10 if finish_bonus else 5
        cutp = int(purse * (getattr(fighter, "manager_cut", 0) or 0) / 100)
        fighter.money += max(0, purse - cutp)
        fighter.confidence = min(100, fighter.confidence + (10 if finish_bonus else 5))
        bout = getattr(fighter, "_last_outcome", None)
        if bout is not None:
            fighter.career_knockdowns = int(getattr(fighter, "career_knockdowns", 0) or 0) + int(getattr(bout.f_stats, "knockdowns", 0) or 0)
            fighter.career_times_down = int(getattr(fighter, "career_times_down", 0) or 0) + int(getattr(bout.f_stats, "times_down", 0) or 0)
        fighter.followers += (random.randint(1, 3) if finish_bonus else random.randint(0, 2))
        fighter.last_week_win = True
        if is_amateur:
            fighter.cardio = min(99, fighter.cardio + 1)
            fighter.durability = min(99, fighter.durability + 1)
            fighter.fight_iq = min(99, fighter.fight_iq + 1)
        legacy_gain = 3 if finish_bonus else 2

        same_gym = bool(getattr(opponent, "team", None) and opponent.team == getattr(fighter, "team", None))
        recruited = fighter.teammate == opponent.name or same_gym
        rival_chance = 0.16 if finish_bonus else 0.08
        if not fighter.rival and not recruited and random.random() < rival_chance:
            story.register_rival(fighter, opponent.name, heat=25, rival_id=getattr(opponent, "fid", None))
            snap = _rival_snapshot(fighter, opponent)
            for r in fighter.rivalries:
                if r.get("name") == opponent.name:
                    r.update(snap)
                    r["heat"] = max(int(r.get("heat") or 0), 25)
            console.print(f"🔥 New rival: {opponent.name}!")
        teammate_chance = 0.05 if finish_bonus else 0.03
        if not fighter.teammate and fighter.rival != opponent.name and random.random() < teammate_chance:
            fighter.teammate = opponent.name
            if getattr(fighter, "team", None) and not getattr(opponent, "team", None):
                opponent.team = fighter.team
            console.print(f"🤝 Recruited to the gym: {opponent.name}!", style="blue")
        if is_amateur and "National Amateur" in fighter.amateur_titles and not fighter.national_team:
            fighter.national_team = True
            console.gold("🇺🇸 You've been invited to the National Team!")
        return legacy_gain

    # loss_finish / loss_decision
    finish_loss = outcome == "loss_finish"
    console.warn(f"💀 {fighter.name} LOSES" + (f" BY {finish.replace(' Loss', '').upper()}!" if finish_loss else " by Decision!"))
    if bump:
        fr[1] += 1
        orr[0] += 1
    fighter.reputation = max(0, fighter.reputation - (5 if finish_loss else 3))
    fighter.confidence = max(0, fighter.confidence - (15 if finish_loss else 10))
    drain = 8 if getattr(fighter, "_in_tournament", False) else (20 if finish_loss else 15)
    fighter.energy = max(0, fighter.energy - drain)
    if finish_loss:
        fighter.health = max(8, fighter.health - 18)
        if random.random() < 0.14:
            from .cut import apply_injury
            apply_injury(fighter, random.choice(["hand", "knee", "eye", "ribs"]), sev=3)
            fighter.injury["severity"] = "serious"
            console.warn("Serious injury. Rehab under E) Life → W.")
    show = int(getattr(fighter, "_show_purse", 0) or max(0, int(purse * 0.20)))
    if show and not is_amateur:
        cutp = int(show * (getattr(fighter, "manager_cut", 0) or 0) / 100)
        fighter.money += max(0, show - cutp)
        console.print("Show money $%s." % (show - cutp))
    return -1


def _handle_promotion(console: GameConsole, fighter, is_amateur: bool) -> None:
    if is_amateur:
        thresholds = [(5, 1, "NATIONAL AMATEUR"), (10, 2, "EUROPEAN AMATEUR"), (15, 3, "IMMAF WORLD AMATEUR")]
        nxt = None
        for wins, tier, label in thresholds:
            if fighter.amateur_record[0] >= wins and fighter.promotion_tier < tier:
                nxt = (tier, label)
                break
        if nxt:
            fighter.promotion_tier = nxt[0]
            console.good("Promoted to %s (one rung)." % nxt[1])
        if fighter.amateur_record[0] >= fighter.amateur_wins_cap and not fighter.pro_debut:
            console.gold("Amateur win cap. Time to turn pro.")
            turn_pro(console, fighter)
    else:
        from . import booking
        moved = booking.maybe_promote(fighter)
        if moved:
            console.good("Booker moved you to %s." % booking.ROOMS[moved]["label"])


def turn_pro(console: GameConsole, fighter) -> None:
    from . import v08
    console.header("TURN PROFESSIONAL")
    console.print("Parents stop. IMMAF closes. Signed amateur comps cancel.")
    console.print("The guys on the other side already have the miles.")
    if v08.am_bouts(fighter) < 10:
        console.warn("Under 10 amateur bouts: debut penalty on cardio / IQ.")
    console.print("You: " + v08.record_line(fighter))
    choice = console.ask("\n  A Confirm turn pro   B Decline (5 week wait)   C Retire > ").strip().upper()
    if choice == "C":
        fighter.retired = True
        console.print("Retired.")
        return
    if choice != "A":
        v08.mark_turn_pro_declined(fighter)
        fighter.story_flags = fighter.story_flags or {}
        fighter.story_flags["declined_pro"] = True
        console.info("Offer returns in 5 weeks.")
        return
    fighter.pro_debut = True
    from . import booking
    from . import orgs
    orgs.sign_org(fighter, orgs.home_org(fighter.country))
    booking.set_room(fighter, fighter.room or "local")
    fighter.money += 1000
    v08.cancel_amateur_comps(fighter)
    story.add_tag(fighter, "pro")
    try:
        story.start_chain_manual(fighter, "turn_pro_arc", console)
        story.advance_active_chain(console, fighter)
    except Exception:
        pass
    console.good("Pro. Local Fight Nights. +$1000. Amateur record stays on the card.")
    fighter.last_week_note = "turned pro"
    console.auto_pause("Turn pro")


def _same_day_gas(console, fighter, opponent, field, bout_index) -> None:
    """Both men already fought today. Do not hand the next guy a full tank."""
    import random as _r
    from .engine import simulate_fight, MMARuleset
    mate = field[max(0, (bout_index + 1) % max(1, len(field)))]
    if mate is opponent and len(field) > 1:
        mate = field[0] if field[0] is not opponent else field[-1]
    try:
        prior = simulate_fight(opponent, mate, MMARuleset(amateur=True), console=None, interactive=False)
        how = getattr(prior, "method", "Decision")
    except Exception:
        how = "Decision"
        opponent.energy = max(22, int(getattr(opponent, "energy", 80) or 80) - 22)
    # Player gets a corner stool, not a night's sleep.
    rec = 6 + int(getattr(fighter, "cardio", 40) or 40) // 25
    fighter.energy = min(58, max(18, int(fighter.energy) + rec))
    extra = 16 if how in ("KO", "TKO", "Submission") else 11
    opponent.energy = max(18, min(52, int(getattr(opponent, "energy", 40) or 40) - extra))
    if console:
        console.info("Same-day turnaround. His last bout %s. Gas you %s / him %s." % (
            how, int(fighter.energy), int(opponent.energy)))


def enter_tournament(console: GameConsole, fighter, pool) -> None:
    """Always-on amateur brackets. Higher tiers unlock by wins, reputation, or titles."""
    from .systems15 import can_compete
    why = can_compete(fighter)
    if why:
        console.warn(why)
        return
    if fighter.health < 12:
        console.warn("Too hurt to take a bracket. Rest.")
        return
    console.header("🏅 LOCAL BRACKET", "Club level only")
    if fighter.pro_debut:
        console.warn("Professionals cannot enter amateur tournaments.")
        console.pause(0.6)
        return

    console.print(
        f"Your amateur record: {fighter.amateur_record[0]}-{fighter.amateur_record[1]}-{fighter.amateur_record[2]}  |  Rep {fighter.reputation}  |  Fame {fighter.fame}"
    )
    if fighter.amateur_titles:
        console.print("Titles: " + ", ".join(fighter.amateur_titles))
    console.print()

    available = []
    locked = []
    for t in data.TOURNAMENTS_DB:
        if str(t.get("level","")).lower() not in ("local", "local amateur"):
            continue
        need_wins = int(t.get("min_wins", 0))
        need_rep = int(t.get("min_reputation", 0))
        # Title shortcut: winning previous tier helps unlock the next
        title_ok = False
        level = t.get("level", "")
        if level == "National Amateur" and "Local" in fighter.amateur_titles:
            title_ok = fighter.amateur_record[0] >= max(3, need_wins - 2)
        if level == "European Amateur" and "National Amateur" in fighter.amateur_titles:
            title_ok = fighter.amateur_record[0] >= max(6, need_wins - 3)
        if level == "IMMAF World Amateur" and "European Amateur" in fighter.amateur_titles:
            title_ok = fighter.amateur_record[0] >= max(10, need_wins - 3)

        qualifies = (
            (fighter.amateur_record[0] >= need_wins and fighter.reputation >= need_rep)
            or title_ok
        )
        if qualifies:
            available.append(t)
        else:
            locked.append((t, need_wins, need_rep))

    if available:
        console.print("Open brackets:")
        for i, t in enumerate(available):
            from .notoriety import amateur_title_fame
            fame_preview = amateur_title_fame(t.get("level"))
            console.print(
                f"  {i + 1}) {t['level']} — ${t['prize']} | Fame +{fame_preview} | {t['opponents']} fights"
            )
    else:
        console.print("No open brackets yet.")

    if locked:
        console.print("\nLocked (what you need):")
        for t, need_wins, need_rep in locked:
            console.print(
                f"  • {t['level']} — need {need_wins} am. wins (you {fighter.amateur_record[0]}) "
                f"and {need_rep} rep (you {fighter.reputation})"
            )
            if t.get("level") == "National Amateur":
                console.print("      or: Local title + a few more wins")
            if t.get("level") == "European Amateur":
                console.print("      or: National title + more wins")

    if not available:
        console.pause(1.0)
        return

    console.print("  X) Back")
    choice = console.ask("\n  Choice > ").strip().upper()
    if choice == "X":
        return
    try:
        tourney = available[int(choice) - 1]
    except (ValueError, IndexError):
        console.warn("Invalid.")
        console.pause(0.5)
        return

    if tourney["level"] in (fighter.amateur_titles or []) and tourney["level"] == "Local":
        console.warn("You already won Local. Move up.")
        console.pause(0.5)
        return
    fee = 20 if tourney["level"]=="Local" else 40
    if fighter.money < fee:
        console.warn("Cannot cover travel/entry $%s." % fee)
        return
    fighter.money -= fee
    console.print("Entering %s. Entry $%s. Prize $%s" % (tourney["level"], fee, tourney["prize"]))
    console.print(f"Win {tourney['opponents']} fights in a row.")
    if console.ask("\nAccept? (A=Yes, B=No): ").strip().upper() != "A":
        console.print("Declined.")
        return

    wins = 0
    total_opponents = tourney["opponents"]
    level = tourney.get("level", "")
    bias = None if ("World" in level or "IMMAF" in level or "European" in level) else fighter.country
    field = []
    used_names = set()
    for _ in range(max(4, total_opponents * 2)):
        cand = generate_random_opponent(fighter, country_bias=bias)
        if cand.name in used_names:
            continue
        used_names.add(cand.name)
        cand.energy = random.randint(72, 88)
        field.append(cand)
    while len(field) < total_opponents:
        field.append(generate_random_opponent(fighter, country_bias=bias))
    fighter._in_tournament = True
    fighter.energy = max(48, min(82, int(fighter.energy)))
    console.print("Bracket of %s. Other bouts run the same day." % total_opponents)
    for i in range(total_opponents):
        console.header(f"TOURNAMENT MATCH {i + 1}/{total_opponents}")
        opponent = field[i]
        if i:
            _same_day_gas(console, fighter, opponent, field, i)
        console.print(f"Opponent: {opponent.name} ({opponent.country}) · {getattr(opponent, 'style', 'MMA')}")
        console.print(
            f"Record: {opponent.amateur_record[0]}-{opponent.amateur_record[1]}-{opponent.amateur_record[2]}"
        )
        if console.ask("\nFight? (A=Yes, B=Forfeit): ").strip().upper() != "A":
            console.print("You forfeit the tournament.")
            break

        losses_before = fighter.amateur_record[1]
        fight_result(console, fighter, opponent, 0, pool)
        _final_autosave(fighter, pool, phase="tournament_bout_final")
        if fighter.amateur_record[1] > losses_before:
            console.warn(f"Eliminated in match {i + 1}.")
            break
        wins += 1
        if wins >= total_opponents:
            console.gold(f"🏆 YOU WIN THE {tourney['level'].upper()}!")
            fighter.money += tourney["prize"]
            from .notoriety import add_fame, amateur_title_fame
            fame_award = amateur_title_fame(tourney["level"])
            add_fame(fighter, fame_award, "amateur tournament title")
            fighter.reputation += max(3, fame_award)
            fighter.legacy_score += 5
            if tourney["level"] not in fighter.amateur_titles:
                fighter.amateur_titles.append(tourney["level"])
            console.print(f"💰 +${tourney['prize']} | ⭐ +{fame_award} Fame | Rep up")
            # Clear promotion path messaging
            if tourney["level"] == "Local":
                console.info("Next: National Championships on the calendar (D → B).")
            elif tourney["level"] == "National Amateur":
                if not fighter.national_team:
                    fighter.national_team = True
                    console.gold("🏅 Invited to the National Team!")
                console.info("Next path: European Amateur (D) or National Championships calendar (M).")
            elif tourney["level"] == "European Amateur":
                console.info("Next: IMMAF World Amateur when you qualify.")
            console.auto_pause("Tournament win")
    fighter._in_tournament = False


# ---------- NATIONAL / CONTINENTAL COMPETITIONS (2x per year) ----------

# Weeks of the year (1-52) when major amateur competitions run
_COMPETITION_CALENDAR = {
    "National Championships": [12, 38],
    # One continental championship per year. The displayed event name is
    # resolved from the fighter's country (European / Pan-American / Asian /
    # African / Oceania) so MMA follows the same geography as the side sports.
    "Continental Championships": [22],
    "IMMAF World Amateur": [30],
}


def _competition_label(fighter, name: str) -> str:
    if name == "Continental Championships":
        try:
            from . import amateur_sports
            return amateur_sports.continental_name(getattr(fighter, "country", ""))
        except Exception:
            return name
    return name


def _year_week(fighter) -> int:
    """Week-of-year from career week (loops yearly)."""
    return ((fighter.week - 1) % 52) + 1


def upcoming_competitions(fighter) -> list:
    """Competitions open for signup this season week (window: 8 to 1 weeks before event)."""
    yw = _year_week(fighter)
    out = []
    if fighter.pro_debut:
        return out
    for base_name, weeks in _COMPETITION_CALENDAR.items():
        name = _competition_label(fighter, base_name)
        for w in weeks:
            # signup from 8 weeks before until the week before the event
            open_from = w - 8
            open_to = w - 1
            if open_from <= yw <= open_to:
                from . import v08
                if base_name.startswith("National") and fighter.amateur_record[0] < 4:
                    continue
                if base_name.startswith("Continental"):
                    if fighter.amateur_record[0] < 8 or not v08.continental_eligible(fighter):
                        continue
                if base_name.startswith("IMMAF") or base_name.startswith("World"):
                    if fighter.amateur_record[0] < 12 or not v08.worlds_eligible(fighter):
                        continue
                if name.startswith("ADCC"):
                    belt = (getattr(fighter, "bjj_belt", None) or "").lower()
                    g = int(getattr(fighter, "grappling", 40) or 40)
                    if belt not in ("blue", "purple", "brown", "black") and g < 58:
                        continue
                    if "Worlds" in name and int(getattr(fighter, "fame", 0) or 0) < 8 and belt not in ("brown", "black"):
                        continue
                out.append({
                    "name": name,
                    "event_week": w,
                    "year_week": yw,
                    "weeks_left": w - yw,
                })
    return out


def _next_competition_info(fighter) -> list:
    """Upcoming events on the calendar (for display even when signup is closed)."""
    yw = _year_week(fighter)
    info = []
    for base_name, weeks in _COMPETITION_CALENDAR.items():
        name = _competition_label(fighter, base_name)
        for w in weeks:
            delta = w - yw
            if delta < 0:
                delta += 52  # next year cycle
            need = 4 if base_name.startswith("National") else (8 if base_name.startswith("Continental") else 12)
            info.append({
                "name": name,
                "event_week": w,
                "weeks_until": delta,
                "signup_opens_in": max(0, delta - 8),
                "need_wins": need,
            })
    info.sort(key=lambda x: x["weeks_until"])
    return info


def competition_menu(console: GameConsole, fighter, pool) -> None:
    """Sign up for scheduled National / European / World championships (2x year)."""
    console.header("🌍 COMPETITIONS", "Scheduled championships")
    if fighter.pro_debut:
        console.warn("Pro fighters cannot enter amateur championships.")
        console.pause(0.6)
        return
    if (fighter.competition_signup
            and str(getattr(fighter, "competition_sport", "MMA") or "MMA") != "MMA"):
        from . import amateur_sports
        amateur_sports.competition_calendar(console, fighter, pool)
        return

    yw = _year_week(fighter)
    console.print(f"Season week: {yw}/52  (career week {fighter.week})")
    console.print(
        f"Amateur record {fighter.amateur_record[0]}-{fighter.amateur_record[1]}-{fighter.amateur_record[2]}  |  "
        f"{'🏅 NT' if fighter.national_team else 'not NT'}"
    )
    console.print()
    console.print("Calendar only for National / Europe / Worlds. Brackets = local.")
    console.print("Sign up in the window, then run camp — the event fires on event week.")
    console.print()

    if fighter.competition_signup:
        console.gold(
            f"Already signed: {fighter.competition_signup} — event season week {fighter.competition_week}"
        )
        left = fighter.competition_week - yw
        if left < 0:
            left += 52
        console.print(f"Weeks until event: ~{left}")
        console.print("Tip: start Training Camp (L) so you arrive sharp.")
        if fighter.national_team:
            console.info("🏅 National Team support active for prep.")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(0.8))("Press Enter to continue")
        return

    upcoming = upcoming_competitions(fighter)
    if upcoming:
        console.print("OPEN FOR SIGN-UP NOW:")
        for i, c in enumerate(upcoming):
            console.print(
                f"  {i + 1}) {c['name']} — event in {c['weeks_left']} week(s) (season week {c['event_week']})"
            )
        console.print("  X) Back")
        raw = console.ask("\n  Sign up > ").strip().upper()
        if raw == "X":
            return
        try:
            c = upcoming[int(raw) - 1]
        except (ValueError, IndexError):
            console.warn("Invalid.")
            return
        fighter.competition_signup = c["name"]
        fighter.competition_week = c["event_week"]
        fighter.competition_prep = True
        fighter.competition_sport = "MMA"
        fighter.competition_level = (
            "world" if "World" in c["name"] else
            "national" if "National" in c["name"] else
            "continental"
        )
        year = ((max(1, int(fighter.week)) - 1) // 52) + 1
        fighter.competition_due_week = (year - 1) * 52 + int(c["event_week"])
        yw = _year_week(fighter)
        left = int(c["event_week"]) - yw
        if left < 0:
            left += 52
        from . import career as _career
        _career.pick_and_start_camp(console, fighter, max(3, min(8, left)))
        console.good(f"📋 Registered for {c['name']}!")
        if fighter.national_team:
            console.gold("🏅 NT will support your preparation.")
        getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(0.8))("Press Enter to continue")
        return

    # Nothing open — show full calendar so the player knows when to come back
    console.warn("No sign-up window is open this week.")
    console.print()
    console.print("Calendar (next events):")
    for info in _next_competition_info(fighter)[:6]:
        if info["signup_opens_in"] == 0 and info["weeks_until"] <= 8:
            status = "window open soon / check again"
        elif info["signup_opens_in"] > 0:
            status = f"signup opens in ~{info['signup_opens_in']}w"
        else:
            status = f"event in ~{info['weeks_until']}w"
        console.print(
            f"  • {info['name']} (season week {info['event_week']}) — {status} — need ≥{info['need_wins']} am. wins"
        )
    console.print()
    try:
        from . import amateur_sports
        continental = amateur_sports.continental_name(getattr(fighter, "country", ""))
    except Exception:
        continental = "Continental Championships"
    console.print("%s: NT + National silver/gold." % continental)
    getattr(console, "continue_prompt", lambda *_a, **_k: console.pause(1.2))("Press Enter to continue")


def check_competition_week(console: GameConsole, fighter, pool) -> None:
    """If this is the event week and fighter is signed up, run the competition."""
    if not fighter.competition_signup:
        return
    if str(getattr(fighter, "competition_sport", "MMA") or "MMA") != "MMA":
        from . import amateur_sports
        amateur_sports.check_scheduled_competition(console, fighter, pool)
        return
    from .systems15 import can_compete
    why = can_compete(fighter)
    if why:
        console.warn("%s Competition deferred." % why)
        fighter.competition_week = min(52, int(fighter.competition_week or 0) + 1)
        if int(getattr(fighter, "competition_due_week", 0) or 0):
            fighter.competition_due_week += 1
        return
    yw = _year_week(fighter)
    due = int(getattr(fighter, "competition_due_week", 0) or 0)
    if (due and int(fighter.week) < due) or (not due and yw != fighter.competition_week):
        # gentle reminder when close
        if 0 < fighter.competition_week - yw <= 2 and not fighter.camp_active:
            console.warn(
                f"⏳ {fighter.competition_signup} is in {fighter.competition_week - yw} week(s) — start camp!"
            )
        return

    name = fighter.competition_signup
    if "ADCC" in str(name):
        _adcc_week(console, fighter, pool, name)
        from . import v08
        v08.cancel_amateur_comps(fighter)
        return
    console.header(f"🏅 {name.upper()}", "Competition week")
    # Resolve into a tournament-like multi-fight
    if "World" in name:
        fights_needed, prize, fame = 4, 2500, 8
        comp_level = "world"
    elif "National" in name:
        fights_needed, prize, fame = 3, 600, 3
        comp_level = "national"
    else:
        fights_needed, prize, fame = 3, 1200, 5
        comp_level = "continental"

    if fighter.national_team:
        prize = int(prize * 1.25)
        console.info("🏅 NT support: better purse and coaching notes.")

    if fighter.camp_active or fighter.camp_bonus > 0:
        console.good(f"Camp sharpness active (+{fighter.camp_bonus}).")
    else:
        console.warn("No camp residual — you'll be underprepared.")

    wins = 0
    field = []
    for n in range(fights_needed):
        bias = fighter.country if comp_level == "national" else None
        if comp_level == "continental":
            try:
                from .systems15 import continent as _continent
                region = _continent(getattr(fighter, "country", ""))
                choices = [c.get("name") for c in data.COUNTRIES
                           if _continent(c.get("name", "")) == region and c.get("name") != fighter.country]
                bias = random.choice(choices) if choices else None
            except Exception:
                bias = None
        opp = generate_random_opponent(fighter, country_bias=bias)
        bump = 4 if comp_level == "world" else (3 if comp_level == "continental" else 2)
        for s in ("striking", "grappling", "cardio", "fight_iq"):
            setattr(opp, s, min(95, getattr(opp, s) + bump + n))
        field.append(opp)
    for i in range(fights_needed):
        console.header(f"MATCH {i+1} of {fights_needed}")
        if "National" in name:
            console.info(f"National championships — mostly {fighter.country} fighters.")
        opponent = field[i]
        if i:
            _same_day_gas(console, fighter, opponent, field, i)
        console.print(f"Opponent: {opponent.name} ({getattr(opponent, 'style', 'MMA')})")
        if console.ask("Fight? (A=Yes, B=Forfeit): ").strip().upper() != "A":
            console.warn("You withdrew.")
            break
        losses_before = fighter.amateur_record[1]
        fight_result(console, fighter, opponent, 0, pool)
        _final_autosave(fighter, pool, phase="tournament_bout_final")
        if fighter.amateur_record[1] > losses_before:
            console.warn(f"Eliminated in match {i+1}.")
            break
        wins += 1
        if wins >= fights_needed:
            console.gold(f"🏆 {name} CHAMPION!")
            fighter.money += prize
            from .notoriety import add_fame
            add_fame(fighter, fame, "major amateur gold")
            fighter.reputation += fame // 2
            fighter.legacy_score += 8
            if name not in fighter.amateur_titles:
                fighter.amateur_titles.append(name)
            from . import v08
            v08.award_medal(fighter, name, "gold")
            fighter.story_flags = fighter.story_flags or {}
            fighter.story_flags["need_nt_letter"] = True
            if "National" in name and not fighter.national_team:
                fighter.national_team = True
                console.gold("National team look after the medal.")
            console.print(f"💰 +${prize} | ⭐ +{fame} Fame | GOLD")
            break
    else:
        from . import v08
        # loop finished without gold
        pass
    from . import v08
    if wins == fights_needed - 1:
        v08.award_medal(fighter, name, "silver")
        fighter.money += prize // 3
        from .notoriety import add_fame
        add_fame(fighter, max(1, fame // 2), "major amateur silver")
        fighter.story_flags = fighter.story_flags or {}
        fighter.story_flags["need_nt_letter"] = True
        console.gold("SILVER. Finalist.")
    elif 0 < wins <= fights_needed - 2:
        v08.award_medal(fighter, name, "bronze")
        fighter.money += prize // 6
        from .notoriety import add_fame
        add_fame(fighter, 1, "major amateur bronze")
        fighter.story_flags = fighter.story_flags or {}
        fighter.story_flags["need_nt_letter"] = True
        console.gold("BRONZE. Semi.")

    from . import v08
    v08.cancel_amateur_comps(fighter)
    console.auto_pause("Competition done")


def no_gi_night(console: GameConsole, fighter, pool) -> None:
    """Local no-gi. Does not count toward the 5-fight pro door."""
    from .systems15 import can_compete
    why = can_compete(fighter)
    if why:
        console.warn(why)
        return
    from . import v08
    console.header("NO-GI NIGHT", "Experience + small cash")
    if fighter.pro_debut:
        console.warn("This room is amateur.")
        return
    flags = fighter.story_flags or {}
    last = int(flags.get("cd_nogi", -99))
    if fighter.week - last < 3 and last > 0:
        console.warn("Cooldown. Try in %s weeks." % (3 - (fighter.week - last)))
        return
    opp = generate_random_opponent(fighter, country_bias=fighter.country)
    console.print("Opponent: %s (%s)" % (opp.name, opp.country))
    go = console.ask("A fight  B sim  X back > ").strip().upper()
    if go == "X" or go == "C":
        return
    from .combat import fight_grappling
    old = getattr(fighter, "fight_details", "Round")
    fighter.fight_details = "Sim" if go == "B" else "Full"
    bout = fight_grappling(console, fighter, opp, gameplan="Submission Hunter", interactive=True)
    fighter.fight_details = old
    result = str(getattr(bout, "result_word", "") or "")
    if result.upper() == "WIN":
        result = "Win"
    elif result.upper() == "LOSS":
        result = "Loss"
    elif result.upper() == "DRAW":
        result = "Draw"
    fighter.record_fight(opp.name, result, bout.method, 1, "Local no-gi", sport="grappling",
                         stats=bout.f_stats.as_dict())
    cash = random.randint(40, 120)
    fighter.energy = max(0, fighter.energy - 12)
    fighter.nogi_nights = int(getattr(fighter, "nogi_nights", 0) or 0) + 1
    flags["cd_nogi"] = fighter.week
    fighter.story_flags = flags
    fighter.grappling = min(99, fighter.grappling + (2 if result == "Win" else 1))
    fighter.ground_control = min(99, fighter.ground_control + 1)
    fighter.submissions = min(99, fighter.submissions + (1 if result == "Win" else 0))
    if result == "Win":
        fighter.money += cash
        flags["nogi_wins"] = int(flags.get("nogi_wins", 0) or 0) + 1
        if flags["nogi_wins"] >= 3:
            flags["nogi_hot"] = True
        console.good("YOU WIN BY %s%s" % (bout.method.upper(),
                                         (" — %s-%s" % (bout.f_score, bout.o_score)) if bout.method == "Points" else ""))
        console.good("+$%s." % cash)
    elif result == "Draw":
        fighter.money += cash // 2
        console.print("DRAW. Paid $%s." % (cash // 2))
    else:
        fighter.money += cash // 3
        console.warn("LOSS — %s. Paid $%s." % (bout.method, cash // 3))
    fighter.last_week_note = "no-gi " + result.lower()
    console.pause(0.8)


def _adcc_week(console: GameConsole, fighter, pool, name: str) -> None:
    """ADCC points night. Worlds can invite a superfight if fame is high."""
    from .combat import fight_grappling
    console.header(name, "no-gi · ADCC points")
    bouts = 3 if "Worlds" in name else 2
    wins = 0
    old = fighter.fight_details
    fighter.fight_details = _pick_watch_mode(console, old)
    for i in range(bouts):
        opp = generate_random_opponent(fighter, country_bias=fighter.country if "Nationals" in name else None)
        opp.style = "BJJ"
        console.print("Match %s / %s vs %s" % (i + 1, bouts, opp.name))
        bout = fight_grappling(console, fighter, opp, gameplan="Submission Hunter", interactive=True)
        word = str(getattr(bout, "result_word", "") or "")
        won = word.upper() in ("WIN", "W")
        console.print("  %s — %s  pts %s-%s" % (word, bout.method, bout.f_score, bout.o_score))
        if won:
            wins += 1
        fighter.energy = max(8, fighter.energy - 10)
        if not won:
            break
    fighter.fight_details = old
    if wins == bouts:
        fighter.money += 400 if "Worlds" in name else 180
        from .notoriety import add_fame
        add_fame(fighter, 4 if "Worlds" in name else 1, "grappling title")
        console.gold("ADCC run complete.")
    else:
        fighter.money += 60
        console.print("Out at match %s." % (wins + 1))
    if "Worlds" in name and int(getattr(fighter, "fame", 0) or 0) >= 22:
        console.gold("Invitational superfight offered.")
        if console.ask("Take it? A yes / B no: ").strip().upper() == "A":
            ace = generate_random_opponent(fighter, country_bias=None)
            ace.grappling = min(99, ace.grappling + 12)
            ace.submissions = min(99, ace.submissions + 10)
            ace.name = ace.name.split()[0] + " (seed)"
            fight_grappling(console, fighter, ace, gameplan="Submission Hunter", interactive=True)
    fighter.competition_signup = None
    fighter.competition_week = 0
