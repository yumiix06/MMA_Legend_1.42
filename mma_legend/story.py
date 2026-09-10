"""v0.5 Phase 2 — story base: tags, chains, post-fight interviews."""
from __future__ import annotations

import random
from typing import Any, Optional

from . import data
from .ui import GameConsole

# Loaded from story_chains.json via data module
def _chains() -> list:
    return list(getattr(data, "STORY_CHAINS", []) or [])


def ensure_story_fields(fighter) -> None:
    if not hasattr(fighter, "narrative_tags") or fighter.narrative_tags is None:
        fighter.narrative_tags = []
    if not hasattr(fighter, "active_chains") or fighter.active_chains is None:
        fighter.active_chains = []
    if not hasattr(fighter, "story_flags") or fighter.story_flags is None:
        fighter.story_flags = {}
    if not hasattr(fighter, "rivalries") or fighter.rivalries is None:
        fighter.rivalries = []


def add_tag(fighter, tag: str) -> None:
    ensure_story_fields(fighter)
    if tag and tag not in fighter.narrative_tags:
        fighter.narrative_tags.append(tag)


def _apply_effects(fighter, effects: dict) -> None:
    if not effects:
        return
    for key, value in effects.items():
        if key == "rival_heat":
            _bump_rival_heat(fighter, int(value))
            continue
        if key == "money":
            fighter.money = max(0, fighter.money + int(value))
        elif key == "fame":
            from .notoriety import add_fame
            add_fame(fighter, int(value), "story")
        elif key == "followers":
            from .notoriety import add_followers
            add_followers(fighter, int(value))
        elif key in ("reputation", "legacy_score", "press_hype"):
            setattr(fighter, key, max(0, getattr(fighter, key, 0) + int(value)))
        elif hasattr(fighter, key):
            cur = getattr(fighter, key)
            if isinstance(cur, (int, float)):
                if key in ("money", "fame", "followers"):
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


def _bump_rival_heat(fighter, amount: int) -> None:
    ensure_story_fields(fighter)
    if fighter.rival:
        for r in fighter.rivalries:
            if r.get("name") == fighter.rival:
                r["heat"] = min(100, r.get("heat", 0) + amount)
                return
        fighter.rivalries.append({
            "name": fighter.rival,
            "heat": min(100, max(0, amount)),
            "fights": 0,
            "last_week": fighter.week,
        })
    elif amount > 0:
        # seed placeholder until a name is set
        fighter.story_flags["pending_rival_heat"] = (
            fighter.story_flags.get("pending_rival_heat", 0) + amount
        )


def _set_rival_placeholder(fighter, console: GameConsole, pool=None) -> None:
    """Create a named rival seed from callout chains.

    Prefers an actual living Fighter from the pool (near the player's
    weight class) so the rival is a real, trackable NPC with a stable id —
    not just a name string that may never correspond to anyone in the
    world. Falls back to a flavor-only name if no pool is available.
    """
    ensure_story_fields(fighter)
    name = None
    rival_id = None
    if pool is not None:
        from . import booking
        same_country = []
        peers = []
        for f in getattr(pool, "fighters", []) or []:
            if f is fighter or f.name == getattr(fighter, "rival", None):
                continue
            if getattr(f, "weight_class", None) != fighter.weight_class:
                continue
            if not booking.opponent_fits(fighter, f):
                continue
            peers.append(f)
            if getattr(f, "country", None) == getattr(fighter, "country", None):
                same_country.append(f)
        bag = same_country or peers
        if bag:
            pick = random.choice(bag)
            name, rival_id = pick.name, getattr(pick, "fid", None)
    if name is None:
        from . import data as D
        meta = random.choice(D.OPPONENTS) if D.OPPONENTS else None
        name = f"{meta['firstName']} {meta['lastName']}" if meta else f"Rival {random.randint(100,999)}"
    if not fighter.rival:
        fighter.rival = name
        fighter.rival_id = rival_id
        heat = 20 + fighter.story_flags.pop("pending_rival_heat", 0)
        fighter.rivalries.append({
            "name": name, "heat": min(100, heat), "fights": 0, "last_week": fighter.week,
        })
        console.gold(f"🔥 Rivalry forming with {name}.")


def _chain_by_id(cid: str) -> Optional[dict]:
    for c in _chains():
        if c.get("id") == cid:
            return c
    return None


def _can_start(fighter, chain: dict) -> bool:
    ensure_story_fields(fighter)
    if any(a.get("id") == chain["id"] for a in fighter.active_chains):
        return False
    if fighter.story_flags.get(f"done_{chain['id']}"):
        return False
    when = chain.get("start_when") or {}
    if when.get("manual_only"):
        return False
    wins = fighter.get_total_record()[0]
    pro = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    pro_wins, pro_losses = int(pro[0]), int(pro[1])
    if "min_wins" in when and wins < when["min_wins"]:
        return False
    if "max_wins" in when and wins > when["max_wins"]:
        return False
    if "min_pro_wins" in when and pro_wins < int(when["min_pro_wins"]):
        return False
    if "max_pro_losses" in when and pro_losses > int(when["max_pro_losses"]):
        return False
    if when.get("requires_pro") and not fighter.pro_debut:
        return False
    if "max_org_rank" in when:
        rank = (getattr(fighter, "story_flags", None) or {}).get("org_rank")
        if not isinstance(rank, int) or rank > int(when["max_org_rank"]):
            return False
    if when.get("not_pro") and fighter.pro_debut:
        return False
    if when.get("national_team") and not fighter.national_team:
        return False
    if "min_fame" in when and fighter.fame < when["min_fame"]:
        return False
    if "min_health_below" in when and fighter.health >= when["min_health_below"]:
        return False
    if "min_promotion_tier" in when and getattr(fighter, "promotion_tier", 0) < when["min_promotion_tier"]:
        return False
    if "min_losses" in when:
        total_losses = fighter.get_total_record()[1]
        if total_losses < when["min_losses"]:
            return False
    if when.get("requires_injury") and not (getattr(fighter, "injury", None) or {}).get("weeks"):
        return False
    chance = float(when.get("chance", 0.2))
    return random.random() < chance


def try_start_chain(fighter, console: Optional[GameConsole] = None) -> Optional[str]:
    """Start at most one new chain if none active."""
    ensure_story_fields(fighter)
    if fighter.active_chains:
        return None
    candidates = [c for c in _chains() if _can_start(fighter, c)]
    if not candidates:
        return None
    candidates.sort(key=lambda c: -c.get("priority", 0))
    chain = candidates[0]
    fighter.active_chains.append({
        "id": chain["id"],
        "step": 0,
        "started_week": fighter.week,
        "expires_week": fighter.week + 6,
    })
    if console:
        console.info(f"📖 Story: {chain.get('name', chain['id'])} begins.")
    return chain["id"]


def start_chain_manual(fighter, chain_id: str, console: Optional[GameConsole] = None) -> bool:
    ensure_story_fields(fighter)
    chain = _chain_by_id(chain_id)
    if not chain:
        return False
    # replace or add
    fighter.active_chains = [a for a in fighter.active_chains if a.get("id") != chain_id]
    if len(fighter.active_chains) >= 1:
        # allow turn_pro to interrupt by taking the slot
        fighter.active_chains = []
    fighter.active_chains.append({
        "id": chain_id,
        "step": 0,
        "started_week": fighter.week,
        "expires_week": fighter.week + 8,
    })
    if console:
        console.info(f"📖 Story: {chain.get('name', chain_id)} begins.")
    return True


def _run_step(console: GameConsole, fighter, chain: dict, step: dict, pool=None) -> None:
    console.header("📖 STORY", chain.get("name", "Chapter"))
    console.print(step.get("title", ""))
    console.print(step.get("description", ""))
    effects = step.get("effects") or {}
    if effects and not step.get("choices"):
        _apply_effects(fighter, effects)
        console.print("Effects: " + ", ".join(f"{k} {v:+d}" if isinstance(v, int) else f"{k}:{v}" for k, v in effects.items()))

    choices = step.get("choices")
    next_id = step.get("next")
    if choices:
        for c in choices:
            console.print(f"  {c.get('label', c.get('key'))}")
        raw = console.ask("\n  Choice > ").strip().upper()
        selected = next((c for c in choices if str(c.get("key", "")).upper() == raw or str(c.get("label", "")).upper().startswith(raw)), None)
        if not selected:
            selected = choices[0]
            console.warn("Defaulted to first option.")
        _apply_effects(fighter, selected.get("effects") or {})
        if selected.get("set_rival_from"):
            _set_rival_placeholder(fighter, console, pool)
        if selected.get("tag"):
            add_tag(fighter, selected["tag"])
        next_id = selected.get("next", next_id)
        console.info("You chose: " + selected.get("label", ""))
    getattr(console, "continue_prompt", lambda *_a, **_k: console.read_pause(
        (step.get("title") or "") + " " + (step.get("description") or ""), extra=0.2
    ))("Press Enter to continue")

    # update active chain step
    ensure_story_fields(fighter)
    active = next((a for a in fighter.active_chains if a.get("id") == chain["id"]), None)
    if active is None:
        return
    if next_id is None:
        # complete
        fighter.active_chains = [a for a in fighter.active_chains if a.get("id") != chain["id"]]
        fighter.story_flags[f"done_{chain['id']}"] = True
        tag = step.get("tag_on_complete")
        if tag:
            add_tag(fighter, tag)
            console.gold(f"Tag earned: {tag}")
        if step.get("flag_on_end"):
            fighter.story_flags[step["flag_on_end"]] = True
    else:
        active["step"] = int(next_id)


def advance_active_chain(console: GameConsole, fighter, pool=None) -> bool:
    """Run the current step of the active chain. Returns True if something ran."""
    ensure_story_fields(fighter)
    if not fighter.active_chains:
        return False
    active = fighter.active_chains[0]
    if fighter.week > active.get("expires_week", 10**9):
        fighter.active_chains.pop(0)
        console.info("📖 A storyline faded without resolution.")
        return False
    chain = _chain_by_id(active["id"])
    if not chain:
        fighter.active_chains.pop(0)
        return False
    steps = {int(s["id"]): s for s in chain.get("steps", [])}
    step = steps.get(int(active.get("step", 0)))
    if not step:
        fighter.active_chains.pop(0)
        return False
    _run_step(console, fighter, chain, step, pool)
    return True


def weekly_story(console: GameConsole, fighter, pool=None) -> bool:
    """Prefer chain progress; otherwise maybe start a chain. Returns True if story content shown."""
    ensure_story_fields(fighter)
    if fighter.active_chains:
        return advance_active_chain(console, fighter, pool)
    started = try_start_chain(fighter, console)
    if started:
        return advance_active_chain(console, fighter, pool)
    return False


def press_conference(console: GameConsole, fighter, opponent, booked=None) -> bool:
    """A real pre-fight scene, reserved for titles and major cards."""
    from . import notoriety
    if not notoriety.should_press(fighter, booked):
        return False
    title = bool((booked or {}).get("title") or getattr(fighter, "_pending_title", False))
    console.header("PRESS CONFERENCE", "Championship media day" if title else "Main-event media day")
    console.print("%s sits across from %s." % (fighter.name, opponent.name))
    console.print("  A) Technical — explain the matchup")
    console.print("  B) Respectful — sell the sport")
    console.print("  C) Heated — promise a finish")
    ans = console.ask("Answer > ").strip().upper()
    if ans == "A":
        fighter.fight_iq = min(100, fighter.fight_iq + 1)
        fighter.reputation = min(100, fighter.reputation + 2)
    elif ans == "B":
        fighter.reputation = min(100, fighter.reputation + 3)
        notoriety.add_followers(fighter, 2)
    else:
        fighter.press_hype = min(100, fighter.press_hype + (12 if title else 8))
        notoriety.add_fame(fighter, 1, "major press conference")
        _bump_rival_heat(fighter, 5)
        ensure_story_fields(fighter)
        fighter.story_flags["last_trash_talk_opponent"] = getattr(opponent, "fid", None) or opponent.name
        fighter.story_flags["last_trash_talk_week"] = int(getattr(fighter, "week", 0) or 0)
    return True


def post_fight_interview(console: GameConsole, fighter, opponent, result: str, booked=None) -> bool:
    """Contextual interview, suppressed for amateur and low-end pro bouts."""
    from . import notoriety
    if not notoriety.should_interview(fighter, booked):
        return False
    ensure_story_fields(fighter)
    tier = notoriety.media_tier(fighter, booked)
    console.header("🎤 POST-FIGHT", "Broadcast desk" if tier == "major" else "Regional media row")
    console.print(f"Result: {result} vs {opponent.name}")
    console.print("  A) Humble — credit opponent, thank corner")
    console.print("  B) Fire — hype yourself, call out the division")
    console.print("  C) Cold — short answers, walk off")
    ans = console.ask("\n  Tone > ").strip().upper()
    if ans.startswith("A"):
        fighter.reputation = min(100, fighter.reputation + 3)
        fighter.happiness = min(100, fighter.happiness + 2)
        if result == "Win":
            add_tag(fighter, "fan_favorite")
        console.info("Humble take. Respect goes up.")
    elif ans.startswith("B"):
        fighter.press_hype = min(100, fighter.press_hype + 8)
        notoriety.add_fame(fighter, 2 if tier == "major" else 1, "post-fight soundbite")
        notoriety.add_followers(fighter, 2 if tier == "major" else 1)
        if result == "Win":
            add_tag(fighter, "villain") if random.random() < 0.35 else add_tag(fighter, "contender")
        if result == "Loss":
            _bump_rival_heat(fighter, 10)
        console.info("Fiery soundbite. Clips will circulate.")
    else:
        fighter.discipline = min(100, fighter.discipline + 2)
        fighter.press_hype = max(0, fighter.press_hype - 2)
        console.info("Cold exit. Media wants more next time.")
    # Rival tracking if fought rival
    if fighter.rival and opponent.name == fighter.rival:
        for r in fighter.rivalries:
            if r.get("name") == fighter.rival:
                r["fights"] = r.get("fights", 0) + 1
                r["last_week"] = fighter.week
                r["heat"] = min(100, r.get("heat", 0) + (8 if result == "Win" else 12))
    getattr(console, "continue_prompt", lambda *_a, **_k: console.read_pause("interview", extra=0.15))("Press Enter to continue")
    return True


def story_dashboard_line(fighter) -> list:
    ensure_story_fields(fighter)
    lines = []
    if fighter.narrative_tags:
        lines.append("Tags: " + ", ".join(fighter.narrative_tags[-4:]))
    if fighter.active_chains:
        a = fighter.active_chains[0]
        ch = _chain_by_id(a["id"])
        name = (ch or {}).get("name", a["id"])
        lines.append(f"Story: {name} (step {a.get('step', 0)})")
    return lines



# ---------- Phase 3: rivalry, news, relationships ----------

def rival_heat(fighter) -> int:
    ensure_story_fields(fighter)
    if not fighter.rival:
        return 0
    for r in fighter.rivalries:
        if r.get("name") == fighter.rival:
            return int(r.get("heat", 0))
    return int(fighter.relationships.get("rival", 0))


def register_rival(fighter, name: str, heat: int = 20, rival_id: Optional[str] = None) -> None:
    ensure_story_fields(fighter)
    fighter.rival = name
    if rival_id:
        fighter.rival_id = rival_id
    for r in fighter.rivalries:
        if r.get("name") == name:
            r["heat"] = min(100, r.get("heat", 0) + heat)
            r["last_week"] = fighter.week
            return
    fighter.rivalries.append({
        "name": name, "heat": min(100, heat), "fights": 0, "last_week": fighter.week,
        "fid": rival_id,
    })
    fighter.relationships["rival"] = min(100, fighter.relationships.get("rival", 0) + heat)


def tick_relationships(fighter) -> None:
    """Slow weekly drift — neglect cools, high heat fades slightly."""
    ensure_story_fields(fighter)
    rel = fighter.relationships
    # Family / friends drift toward 40 if ignored
    for k in ("family", "friends"):
        if rel.get(k, 50) > 40:
            rel[k] = max(40, rel[k] - 1)
    if fighter.camp_active:
        rel["coach"] = min(100, rel.get("coach", 50) + 1)
    else:
        if rel.get("coach", 50) > 35 and fighter.week % 3 == 0:
            rel["coach"] = max(35, rel["coach"] - 1)
    # Rival heat decays slowly if not fed
    for r in fighter.rivalries:
        last = int(r.get("last_week", fighter.week))
        if fighter.week - last >= 8:
            r["heat"] = max(0, int(r.get("heat", 0)) - 2)
    # Current pro status must be earned on the pro ledger.  In 1.23 a
    # 21-win amateur became a regional "contender" the instant he turned pro.
    if fighter.pro_debut:
        add_tag(fighter, "pro")
    pro = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    rank = (getattr(fighter, "story_flags", None) or {}).get("org_rank")
    if fighter.pro_debut and int(pro[0]) >= 4 and fighter.fame >= 25:
        if isinstance(rank, int) and rank <= 8:
            add_tag(fighter, "contender")


def career_label(fighter) -> str:
    """Current career status, derived from live pro context rather than old tags."""
    if not getattr(fighter, "pro_debut", False):
        w = int((getattr(fighter, "amateur_record", None) or [0])[0])
        return "amateur prospect" if w < 6 else "elite amateur"
    flags = getattr(fighter, "story_flags", None) or {}
    rec = list(getattr(fighter, "pro_record", None) or [0, 0, 0])
    w, l = int(rec[0]), int(rec[1])
    bouts = sum(int(x) for x in rec[:3])
    if flags.get("org_belt"):
        return "champion"
    rank = flags.get("org_rank")
    if w >= 4 and isinstance(rank, int) and rank <= 3:
        return "title contender"
    if w >= 3 and isinstance(rank, int) and rank <= 8:
        return "contender"
    if bouts >= 6 and l >= w + 3:
        return "journeyman"
    if bouts <= 3:
        return "pro prospect"
    return "established pro"


def show_weekly_news(console: GameConsole, pool, fighter) -> None:
    """Short UFC-centric ticker."""
    news = list(getattr(pool, "news", []) or [])
    if not news:
        return
    console.section("News")
    from .ui import wrap_text
    for line in news[-2:]:
        wrapped = wrap_text("• " + line, 42)
        for i, wline in enumerate(wrapped):
            console.print(("  " if i == 0 else "    ") + wline)
    # Personal beat
    if fighter.rival and rival_heat(fighter) >= 40:
        console.print(f"  • Media still talking about you vs {fighter.rival}.")
    label = career_label(fighter)
    flavor = [t for t in list(getattr(fighter, "narrative_tags", None) or [])
              if t in ("fan_favorite", "villain", "comeback_story", "weight_trouble")]
    called = [label] + flavor[-1:]
    console.print("  • You're being called: %s" % ", ".join(called))


def relationship_menu(console: GameConsole, fighter) -> bool:
    """People action. Returns True only when the player actually spends the half-week."""
    ensure_story_fields(fighter)
    console.header("👥 PEOPLE", "HALF WEEK only after you choose someone")
    rel = fighter.relationships
    console.print(f"  Coach {rel.get('coach',50)}  •  Family {rel.get('family',50)}  •  Friends {rel.get('friends',50)}")
    console.print(f"  Teammate: {fighter.teammate or '—'}  •  Rival: {fighter.rival or '—'}")
    console.print()
    console.print("  A) Talk to coach")
    console.print("  B) Call family")
    console.print("  C) Hang with friends / teammate")
    console.print("  D) Study rival")
    console.print("  X) Back")
    c = console.ask("\n  Choice > ").strip().upper()
    if c in ("X", "0", ""):
        return False
    if c not in ("A", "B", "C", "D"):
        console.warn("Invalid.")
        return False
    if c == "D" and not fighter.rival:
        console.info("No rival yet — win, lose close, or answer a callout.")
        return False
    if fighter.energy < 6:
        console.warn("Too tired.")
        return False
    fighter.energy -= 6
    if c == "A":
        rel["coach"] = min(100, rel.get("coach", 50) + 6)
        fighter.confidence = min(100, fighter.confidence + 2)
        console.good("Coach session. Relationship +6.")
        if rel["coach"] >= 70 and random.random() < 0.3:
            fighter.fight_iq = min(100, fighter.fight_iq + 1)
            console.info("A small IQ tip sticks.")
    elif c == "B":
        rel["family"] = min(100, rel.get("family", 50) + 8)
        fighter.happiness = min(100, fighter.happiness + 6)
        console.good("Family call. Happiness up.")
    elif c == "C":
        rel["friends"] = min(100, rel.get("friends", 50) + 6)
        fighter.happiness = min(100, fighter.happiness + 4)
        console.good("Time with %s. Friends +6." % (fighter.teammate or "the gym"))
    else:
        fighter.opponent_read = min(20, fighter.opponent_read + 4)
        _bump_rival_heat(fighter, 4)
        console.good(f"Film on {fighter.rival}. Read +4, heat ticks up.")
    console.pause(0.4)
    return True

def context_label(fighter, opponent, is_title: bool = False) -> str:
    if is_title:
        return "TITLE FIGHT"
    if fighter.rival and opponent and opponent.name == fighter.rival:
        return "RIVALRY FIGHT"
    if getattr(opponent, "organization", None) == "UFC" and fighter.pro_debut:
        return "UFC BOUT"
    if fighter.pro_debut:
        return "PRO BOUT"
    return "AMATEUR BOUT"


def purse_multiplier(fighter, opponent, is_title: bool = False) -> float:
    m = 1.0
    if is_title:
        m *= 2.2
    if fighter.rival and opponent and opponent.name == fighter.rival:
        m *= 1.25 + rival_heat(fighter) / 400
    if "villain" in (fighter.narrative_tags or []):
        m *= 1.08
    if "fan_favorite" in (fighter.narrative_tags or []):
        m *= 1.06
    if fighter.pro_debut and getattr(opponent, "organization", None) == "UFC":
        m *= 1.35
    return m
