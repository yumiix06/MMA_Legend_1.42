"""Fight intelligence, opponent preparation and adaptive tactics (v1.39).

This module deliberately does not own the fight state machine.  engine.fight
still owns legal actions, positions, scoring and damage.  What lives here is
*decision quality*: what a fighter notices, how quickly they adjust, and which
legal choices become attractive after new information appears.

The design rule is bounded influence.  Intelligence can turn a 50/50 decision
into a better decision, but it cannot make a poor wrestler out-wrestle an elite
one or let a camp erase a large skill gap.
"""
from __future__ import annotations

import random
from collections import Counter

TAKEDOWNS = frozenset({"double_leg", "single_leg", "trip", "throw", "snap_down"})
SHOT_TAKEDOWNS = frozenset({"double_leg", "single_leg"})
BOXING = frozenset({"jab", "cross", "hook", "uppercut", "liver"})
KICKS = frozenset({"low_kick", "body_kick", "head_kick", "teep", "side_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick"})
STRIKES = BOXING | KICKS | frozenset({"dirty_box", "knee_body", "gnp"})
SUBMISSIONS = frozenset({
    "rear_naked", "armbar", "triangle", "kimura", "guillotine", "anaconda",
    "heel_hook", "kneebar", "north_south_choke",
})
CONTROL = frozenset({"guard_pass", "mount_up", "take_back", "ride", "clinch_entry"})
EXPENSIVE = frozenset({"head_kick", "spin_back_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "double_leg", "single_leg", "throw", "gnp"}) | SUBMISSIONS
FINISHERS = frozenset({"cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "gnp"}) | SUBMISSIONS
SAFE_ACTIONS = frozenset({"jab", "teep", "side_kick", "break", "sprawl", "ride", "guard_pass", "stand_up"})


def _n(f, key, default=50):
    try:
        value = getattr(f, key, default)
        if value is None:
            value = default
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(lo, hi, x):
    return max(lo, min(hi, x))


def fighter_profile(fighter) -> dict:
    """Stable behavioral profile derived from existing fighter psychology."""
    iq = _n(fighter, "fight_iq")
    adapt = _n(fighter, "adaptability")
    discipline = _n(fighter, "discipline")
    tough = _n(fighter, "mental_toughness")
    confidence = _n(fighter, "confidence")
    cardio = _n(fighter, "cardio")
    power = _n(fighter, "ko_power")
    personality = str(getattr(fighter, "career_personality", "") or "").lower()
    risk = 0.48 + (confidence - 50) / 260.0 + (power - 50) / 420.0
    if personality in ("action-oriented", "ambitious"):
        risk += 0.08
    elif personality in ("cautious", "professional"):
        risk -= 0.06
    return {
        "read": _clamp(0.18, 0.95, (iq * 0.62 + adapt * 0.38) / 100.0),
        "adjust": _clamp(0.15, 0.95, (iq * 0.48 + adapt * 0.40 + discipline * 0.12) / 100.0),
        "composure": _clamp(0.20, 0.95, (tough * 0.45 + iq * 0.30 + discipline * 0.25) / 100.0),
        "risk": _clamp(0.22, 0.82, risk),
        "pace_capacity": _clamp(0.30, 0.95, (cardio * 0.75 + discipline * 0.25) / 100.0),
    }


def _prep_dict(fighter) -> dict:
    raw = getattr(fighter, "camp_preparation", None)
    return dict(raw) if isinstance(raw, dict) else {}


def _recent_tendencies(opponent) -> dict:
    rows = list(getattr(opponent, "fight_history", None) or [])[-6:]
    agg = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        st = row.get("stats") or {}
        if not isinstance(st, dict):
            st = {}
        agg["td"] += int(st.get("takedowns_attempted", 0) or 0)
        agg["td_land"] += int(st.get("takedowns_landed", 0) or 0)
        agg["sub"] += int(st.get("submission_attempts", 0) or 0)
        agg["head"] += int(st.get("head_landed", 0) or 0)
        agg["body"] += int(st.get("body_landed", 0) or 0)
        agg["leg"] += int(st.get("leg_landed", 0) or 0)
        agg["ctrl"] += int(st.get("control_sec", 0) or 0)
        agg["kd"] += int(st.get("knockdowns", 0) or 0)
    agg["fights"] = len(rows)
    return dict(agg)


def preparation_blueprint(fighter, opponent, focus: str = "Complete") -> dict:
    """Opponent-specific camp plan.  Values are preparation points, not stats."""
    focus_l = str(focus or "Complete").lower()
    out = {
        "opponent_id": getattr(opponent, "fid", None) if opponent is not None else None,
        "opponent_name": getattr(opponent, "name", "") if opponent is not None else "",
        "focus": str(focus or "Complete"),
        "weeks": 0,
        "readiness": 0,
        "anti_wrestling": 0,
        "close_distance": 0,
        "range_defense": 0,
        "submission_safety": 0,
        "pace_plan": 0,
        "damage_plan": 0,
    }
    if opponent is None:
        out["pace_plan"] = 1 if "cardio" in focus_l else 0
        return out

    og = _n(opponent, "grappling") + _n(opponent, "ground_control") * 0.45
    os = _n(opponent, "striking") + _n(opponent, "kicks") * 0.45
    subs = _n(opponent, "submissions") + _n(opponent, "ground_control") * 0.25
    reach_edge = _n(opponent, "reach", 177) - _n(fighter, "reach", 177)

    # The camp focus is tactical, not just a stat label.  Separate attacking
    # wrestling from anti-wrestling so a player can deliberately prepare to
    # impose grappling OR deny it.
    if "anti" in focus_l and "wrest" in focus_l:
        out["anti_wrestling"] += 4
        out["range_defense"] += 1
    elif "submission" in focus_l or "grappling defense" in focus_l:
        out["submission_safety"] += 4
        out["anti_wrestling"] += 1
    elif "entry" in focus_l or "pressure" in focus_l:
        out["close_distance"] += 4
        out["pace_plan"] += 1
    elif "wrest" in focus_l:
        out["close_distance"] += 3
        out["anti_wrestling"] += 1
    elif "strik" in focus_l:
        out["range_defense"] += 2
        out["damage_plan"] += 2
    elif "cardio" in focus_l or "pace" in focus_l:
        out["pace_plan"] += 4
    else:
        out["anti_wrestling"] += 1
        out["range_defense"] += 1
        out["pace_plan"] += 1
        out["submission_safety"] += 1

    if og >= os + 8:
        out["anti_wrestling"] += 2
    if subs >= 75:
        out["submission_safety"] += 2
    if os >= og + 10 or reach_edge >= 6:
        out["range_defense"] += 2
        out["close_distance"] += 1
    if _n(opponent, "cardio") >= 72:
        out["pace_plan"] += 1
    recent = _recent_tendencies(opponent)
    if recent.get("td", 0) >= 8:
        out["anti_wrestling"] += 1
    if recent.get("leg", 0) > max(recent.get("body", 0), recent.get("head", 0)):
        out["range_defense"] += 1
    if recent.get("kd", 0) >= 2:
        out["damage_plan"] += 1
    for k in ("anti_wrestling", "close_distance", "range_defense", "submission_safety", "pace_plan", "damage_plan"):
        out[k] = int(_clamp(0, 5, out[k]))
    return out


def advance_preparation(fighter) -> None:
    prep = _prep_dict(fighter)
    if not prep:
        return
    prep["weeks"] = int(prep.get("weeks", 0) or 0) + 1
    prep["readiness"] = int(_clamp(0, 12, int(prep.get("readiness", 0) or 0) + 2))
    # The chosen strengths get rehearsed each week, capped so camps cannot
    # replace actual skill.
    candidates = [k for k in ("anti_wrestling", "close_distance", "range_defense", "submission_safety", "pace_plan", "damage_plan") if int(prep.get(k, 0) or 0) > 0]
    if candidates:
        key = max(candidates, key=lambda k: (int(prep.get(k, 0) or 0), k))
        prep[key] = int(_clamp(0, 6, int(prep.get(key, 0) or 0) + 1))
    fighter.camp_preparation = prep


def virtual_preparation(fighter, opponent) -> dict:
    """NPCs prepare too.  They get a modest matchup-specific plan automatically."""
    prep = _prep_dict(fighter)
    if prep and (not prep.get("opponent_id") or prep.get("opponent_id") == getattr(opponent, "fid", None)):
        return prep
    if bool(getattr(fighter, "is_player", False)):
        return {}
    plan = preparation_blueprint(fighter, opponent, "Complete")
    iq = int(_n(fighter, "fight_iq"))
    plan["readiness"] = int(_clamp(1, 8, 2 + iq // 20))
    # NPC preparation is useful but not equivalent to a full player camp.
    for k in ("anti_wrestling", "close_distance", "range_defense", "submission_safety", "pace_plan", "damage_plan"):
        plan[k] = min(4, int(plan.get(k, 0) or 0))
    return plan


def make_state(fighter, opponent) -> dict:
    prep = virtual_preparation(fighter, opponent)
    read = int(getattr(fighter, "opponent_read", 0) or 0)
    if not getattr(fighter, "is_player", False):
        read = max(read, int(_n(fighter, "fight_iq") // 8))
    return {
        "profile": fighter_profile(fighter),
        "prep": prep,
        "pre_read": int(_clamp(0, 20, read)),
        "self": Counter(),
        "opp": Counter(),
        "self_result": Counter(),
        "opp_result": Counter(),
        "adjustments": [],
        "last_reason": "",
    }


def observe(state: dict, *, self_action: bool, action: str, result: str, damage: int = 0, target: str = "") -> None:
    side = "self" if self_action else "opp"
    bucket = state[side]
    bucket[action] += 1
    if action in TAKEDOWNS:
        bucket["takedowns"] += 1
    if action in STRIKES:
        bucket["strikes"] += 1
    if action in KICKS:
        bucket["kicks"] += 1
    if action in SUBMISSIONS:
        bucket["submissions"] += 1
    if target:
        bucket["target:" + str(target).split(":", 1)[0]] += 1
    result_bucket = state["self_result" if self_action else "opp_result"]
    result_bucket[action + ":" + result] += 1
    if result == "land":
        result_bucket["damage"] += max(0, int(damage or 0))


def _knowledge(state: dict) -> float:
    p = state.get("profile", {})
    pre = int(state.get("pre_read", 0) or 0) / 20.0
    observed = sum(int(v or 0) for k, v in state.get("opp", {}).items() if k in STRIKES or k in TAKEDOWNS or k in SUBMISSIONS)
    live = min(1.0, observed / 8.0) * float(p.get("read", 0.5))
    readiness = int((state.get("prep") or {}).get("readiness", 0) or 0) / 12.0
    return _clamp(0.12, 1.0, 0.15 + pre * 0.45 + live * 0.35 + readiness * 0.20)


def action_multiplier(state: dict, action: str, *, gas: int, opponent_gas: int,
                      my_damage: dict, opponent_damage: dict, round_no: int,
                      total_rounds: int, score_margin: float = 0.0) -> float:
    """Bounded tactical weight for a legal action."""
    prof = state.get("profile", {})
    prep = state.get("prep", {}) or {}
    know = _knowledge(state)
    adjust = float(prof.get("adjust", 0.5))
    composure = float(prof.get("composure", 0.5))
    risk = float(prof.get("risk", 0.5))
    opp = state.get("opp", {})
    own_results = state.get("self_result", {})
    mult = 1.0

    # Read the opponent's repeated behavior.  High-IQ/prepared fighters react
    # sooner; low-IQ fighters need much more evidence.
    shots = int(opp.get("takedowns", 0) or 0)
    if shots >= 2 and action in ("sprawl", "guillotine", "clinch_entry", "stand_up"):
        mult *= 1.0 + min(0.85, (0.18 + 0.10 * shots) * know * adjust)
    jabs = int(opp.get("jab", 0) or 0) + int(opp.get("teep", 0) or 0)
    if jabs >= 3 and action in ("cross", "clinch_entry", "double_leg", "single_leg"):
        mult *= 1.0 + min(0.55, (0.10 + 0.06 * jabs) * know * adjust)
    kicks = int(opp.get("kicks", 0) or 0)
    if kicks >= 3 and action in ("cross", "double_leg", "single_leg", "clinch_entry"):
        mult *= 1.0 + min(0.45, (0.08 + 0.05 * kicks) * know * adjust)

    # Camp preparation is specific, not a universal accuracy potion.
    if action in ("sprawl", "guillotine", "stand_up"):
        mult *= 1.0 + 0.035 * int(prep.get("anti_wrestling", 0) or 0)
    if action in ("double_leg", "single_leg", "clinch_entry", "trip"):
        mult *= 1.0 + 0.028 * int(prep.get("close_distance", 0) or 0)
    if action in ("jab", "teep", "break", "sprawl"):
        mult *= 1.0 + 0.020 * int(prep.get("range_defense", 0) or 0)
    if action in ("escape", "stand_up", "guard_pass"):
        mult *= 1.0 + 0.022 * int(prep.get("submission_safety", 0) or 0)

    # Damage-aware self preservation.  Composed fighters alter phase selection
    # rather than blindly attacking with the compromised weapon.
    legs = int(my_damage.get("legs", 0) or 0)
    body = int(my_damage.get("body", 0) or 0)
    head = int(my_damage.get("head", 0) or 0)
    cuts = int(my_damage.get("cuts", 0) or 0)
    if legs >= 10 and action in KICKS | SHOT_TAKEDOWNS:
        mult *= max(0.28, 1.0 - (0.25 + legs / 90.0) * composure)
    if body >= 12 and action in EXPENSIVE:
        mult *= max(0.40, 1.0 - (0.20 + body / 120.0) * composure)
    if (head >= 18 or cuts >= 8) and action in ("clinch_entry", "double_leg", "single_leg", "ride", "break"):
        mult *= 1.0 + 0.35 * composure
    if (head >= 18 or cuts >= 8) and action in ("hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick"):
        mult *= max(0.55, 1.0 - 0.32 * composure)

    # Score awareness.  The final round is where intelligent fighters clearly
    # separate: behind means variance; ahead means bank the fight.
    late = round_no >= total_rounds
    if late and score_margin <= -1:
        if action in FINISHERS:
            mult *= 1.18 + 0.55 * adjust * risk
        if action in SAFE_ACTIONS:
            mult *= max(0.58, 1.0 - 0.28 * adjust)
    elif late and score_margin >= 1:
        if action in SAFE_ACTIONS | CONTROL:
            mult *= 1.12 + 0.34 * adjust * composure
        if action in ("head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "hook", "uppercut", "heel_hook"):
            mult *= max(0.62, 1.0 - 0.24 * composure)

    # Gas intelligence: exhausted fighters stop selecting repeated expensive
    # actions unless they are desperate on the scorecards.
    if gas <= 25 and action in EXPENSIVE:
        desperation = late and score_margin < 0
        mult *= 0.68 if desperation else max(0.34, 0.72 - 0.28 * adjust)
    if gas <= 25 and action in ("jab", "teep", "side_kick", "ride", "break"):
        mult *= 1.0 + 0.30 * composure
    if opponent_gas <= 22 and action in FINISHERS | frozenset({"clinch_entry", "gnp"}):
        mult *= 1.0 + 0.30 * adjust * risk

    # Intelligent damage exploitation. Preparation makes the read cleaner,
    # but the damage must actually exist in the bout before the AI targets it.
    dmg_prep = int(prep.get("damage_plan", 0) or 0)
    hunt = _clamp(0.0, 1.0, 0.38 + adjust * 0.42 + dmg_prep * 0.04)
    opp_legs = int(opponent_damage.get("legs", 0) or 0)
    opp_body = int(opponent_damage.get("body", 0) or 0)
    opp_head = int(opponent_damage.get("head", 0) or 0)
    opp_cuts = int(opponent_damage.get("cuts", 0) or 0)
    if opp_legs >= 14:
        if action == "low_kick": mult *= 1.0 + min(0.58, (0.16 + opp_legs / 120.0) * hunt)
        if action in TAKEDOWNS: mult *= 1.0 + min(0.32, (0.08 + opp_legs / 180.0) * hunt)
    if opp_body >= 14 and action in ("liver", "body_kick", "spin_back_kick", "side_kick", "knee_body", "teep", "gnp"):
        mult *= 1.0 + min(0.50, (0.14 + opp_body / 140.0) * hunt)
    if opp_head >= 18 and action in ("cross", "hook", "uppercut", "head_kick", "spin_hook_kick", "axe_kick", "tornado_kick", "gnp"):
        mult *= 1.0 + min(0.45, (0.10 + opp_head / 170.0) * hunt)
    if opp_cuts >= 7 and action in ("jab", "cross", "hook", "gnp"):
        mult *= 1.0 + min(0.32, (0.08 + opp_cuts / 90.0) * hunt)

    # Working techniques are reinforced, but not enough to create one-button
    # spam. Failure history is handled by engine.fight's stuffed counters.
    lands = int(own_results.get(action + ":land", 0) or 0)
    misses = int(own_results.get(action + ":miss", 0) or 0)
    if lands >= 2 and lands > misses:
        mult *= 1.0 + min(0.22, lands * 0.035 * adjust)

    return _clamp(0.30, 2.35, mult)


def takedown_entry_bonus(attacker, defender, action: str, prep=None) -> float:
    """Specific camp preparation effect on an attacking entry, max ~4%."""
    prep = dict(prep) if isinstance(prep, dict) else virtual_preparation(attacker, defender)
    pts = int(prep.get("close_distance", 0) or 0)
    if action in TAKEDOWNS:
        return min(0.04, pts * 0.007)
    return 0.0


def takedown_defense_bonus(defender, attacker, action: str, prep=None) -> float:
    """Specific anti-wrestling preparation, max ~5% on the contest."""
    prep = dict(prep) if isinstance(prep, dict) else virtual_preparation(defender, attacker)
    pts = int(prep.get("anti_wrestling", 0) or 0)
    if action in TAKEDOWNS:
        return min(0.05, pts * 0.008)
    return 0.0


def striking_defense_bonus(defender, attacker, action: str, prep=None) -> float:
    prep = dict(prep) if isinstance(prep, dict) else virtual_preparation(defender, attacker)
    pts = int(prep.get("range_defense", 0) or 0)
    if action in STRIKES:
        return min(0.035, pts * 0.006)
    return 0.0


def submission_defense_bonus(defender, attacker, prep=None) -> float:
    prep = dict(prep) if isinstance(prep, dict) else virtual_preparation(defender, attacker)
    pts = int(prep.get("submission_safety", 0) or 0)
    return min(0.035, pts * 0.006)


def choose_mma_plan(fighter, opponent) -> dict:
    """Matchup-aware NPC opening plan using only information a camp could know."""
    style = str(getattr(fighter, "archetype", "") or getattr(fighter, "style", "") or "").lower()
    strike = _n(fighter, "striking") + _n(fighter, "kicks") * 0.60
    wrestle = _n(fighter, "grappling") + _n(fighter, "ground_control") * 0.50
    subs = _n(fighter, "submissions") + _n(fighter, "ground_control") * 0.30
    opp_tdd = _n(opponent, "takedown_def")
    opp_strdef = _n(opponent, "striking_def")
    opp_subdef = _n(opponent, "submission_def")
    reach_edge = _n(fighter, "reach", 177) - _n(opponent, "reach", 177)
    prof = fighter_profile(fighter)

    if ("bjj" in style or "submission" in style or subs >= strike + 12) and subs >= opp_subdef + 8:
        return {"name":"Submission Hunter","target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"guard"}
    if (any(x in style for x in ("wrest", "sambo", "judo")) or wrestle >= strike + 8) and wrestle >= opp_tdd + 4:
        return {"name":"Wrestle-heavy","target":"body","pace":"mid","td":"Aggressive","range":"pocket","defense":"movement"}
    if (any(x in style for x in ("muay", "kick", "karate", "taekwondo")) or _n(fighter, "kicks") >= _n(fighter, "striking") + 7) and reach_edge >= -3:
        return {"name":"Kickboxing Outside","target":"body","pace":"mid","td":"Safe","range":"kicking","defense":"movement"}
    if strike >= opp_strdef + 10 and prof["risk"] >= 0.52:
        return {"name":"Pressure","target":"head","pace":"high","td":"Opportunistic","range":"pocket","defense":"guard"}
    if _n(fighter, "striking_def") + _n(fighter, "fight_iq") >= _n(fighter, "ko_power") + _n(fighter, "striking") + 10:
        return {"name":"Counter","target":"head","pace":"low","td":"Safe","range":"boxing","defense":"counter"}
    return {"name":"Balanced","target":"body","pace":"mid","td":"Opportunistic","range":"boxing","defense":"guard"}


def between_round_adjustment(fighter, opponent, state: dict, plan: dict, *,
                             round_lost: bool, gas: int, opponent_gas: int,
                             score_margin: float, my_damage: dict,
                             opponent_damage: dict) -> tuple[dict, str]:
    """Return an adjusted plan and a short corner reason."""
    out = dict(plan or {})
    prof = state.get("profile", {})
    adjust = float(prof.get("adjust", 0.5))
    composure = float(prof.get("composure", 0.5))
    self_results = state.get("self_result", {})
    own = state.get("self", {})
    reason = "Stay with the plan."

    td_att = int(own.get("takedowns", 0) or 0)
    td_land = sum(int(self_results.get(a + ":land", 0) or 0) for a in TAKEDOWNS)
    strike_land = sum(int(self_results.get(a + ":land", 0) or 0) for a in STRIKES)
    strike_miss = sum(int(self_results.get(a + ":miss", 0) or 0) for a in STRIKES)

    # Low-adaptability fighters can recognize a problem and still fail to
    # change. Severe damage, exhaustion or a clearly losing score override
    # that stubbornness; otherwise elite Fight IQ is what separates early
    # adjustment from blindly repeating the opening plan.
    urgent = (gas <= 22 or int(my_damage.get("head", 0) or 0) >= 25
              or int(my_damage.get("cuts", 0) or 0) >= 12 or score_margin <= -3)
    if adjust < 0.38 and not urgent:
        return out, "Stay with the opening plan a little longer."

    if gas <= 28 and score_margin >= 0:
        out["pace"] = "low"
        reason = "Protect the gas tank and bank clean work."
    elif int(my_damage.get("legs", 0) or 0) >= 18:
        out["range"] = "boxing"
        out["defense"] = "guard"
        if out.get("target") == "legs": out["target"] = "body"
        reason = "Your leg is compromised; box more and stop loading it."
    elif int(my_damage.get("body", 0) or 0) >= 20 and gas <= 45:
        out["pace"] = "low"
        out["defense"] = "movement"
        reason = "The body damage is draining you; slow the exchanges and reset."
    elif int(my_damage.get("head", 0) or 0) >= 20 or int(my_damage.get("cuts", 0) or 0) >= 8:
        if _n(fighter, "grappling") >= _n(opponent, "takedown_def") - 8:
            out["td"] = "Aggressive"
            out["range"] = "pocket"
            reason = "You are getting hurt at range; close distance and control."
        else:
            out["defense"] = "movement"
            out["pace"] = "low"
            reason = "Protect the damaged head and make him reset."
    elif td_att >= 3 and td_land == 0 and adjust >= 0.45:
        out["td"] = "Safe"
        out["range"] = "boxing"
        reason = "The open shots are not there; stop forcing them."
    elif int(state.get("opp", {}).get("takedowns", 0) or 0) >= 4 and adjust >= 0.52:
        out["defense"] = "movement"
        out["range"] = "boxing"
        reason = "He keeps changing levels; deny clean entries and make him shoot long."
    elif int(state.get("opp", {}).get("kicks", 0) or 0) >= 5 and adjust >= 0.50 and _n(fighter, "grappling") >= _n(opponent, "takedown_def") - 5:
        out["td"] = "Aggressive"
        out["range"] = "pocket"
        reason = "He is committing to kicks; close behind them and wrestle."
    elif strike_miss >= 6 and strike_land * 2 < strike_miss and _n(fighter, "grappling") >= _n(opponent, "takedown_def") - 5:
        out["td"] = "Aggressive"
        out["range"] = "pocket"
        reason = "You are losing at range; connect the phases."
    elif round_lost or score_margin < 0:
        if _n(fighter, "grappling") >= _n(opponent, "takedown_def") + 3:
            out["td"] = "Aggressive"
            reason = "You need a different look; force the grappling exchanges."
        else:
            out["pace"] = "high" if gas >= 35 else "mid"
            out["target"] = "head"
            reason = "You are behind; raise the output and create damage."
    elif int(opponent_damage.get("legs", 0) or 0) >= 18 and adjust >= 0.48:
        out["target"] = "legs"
        reason = "His movement is compromised; keep attacking the damaged leg."
    elif int(opponent_damage.get("body", 0) or 0) >= 18 and adjust >= 0.48:
        out["target"] = "body"
        out["pace"] = "high" if gas >= 45 else "mid"
        reason = "The body work is paying off; make him carry the damage."
    elif int(opponent_damage.get("head", 0) or 0) >= 24 and adjust >= 0.52:
        out["target"] = "head"
        out["pace"] = "high" if gas >= 40 else "mid"
        reason = "He is hurt; pressure without abandoning position."
    elif opponent_gas <= 25:
        out["pace"] = "high" if gas >= 40 else "mid"
        reason = "His pace is breaking; make him work now."
    elif score_margin > 0 and composure >= 0.58:
        out["pace"] = "mid" if gas >= 35 else "low"
        reason = "You are ahead; stay disciplined and deny the swing."

    if out != dict(plan or {}):
        state.setdefault("adjustments", []).append(reason)
        state["last_reason"] = reason
    return out, reason


def chain_takedown_followup(attacker, defender, first_action: str, *, gas: int,
                            plan: dict | None = None, rng=None) -> str | None:
    """Choose a realistic secondary attack after a stuffed shot.

    A chain is never guaranteed.  It depends on grappling, Fight IQ,
    adaptability, gas and tactical intent.  The return value is a clinch-range
    follow-up that the canonical fight engine still resolves normally.
    """
    rng = rng or random.random
    plan = dict(plan or getattr(attacker, "_fight_plan", None) or {})
    grap = _n(attacker, "grappling")
    iq = _n(attacker, "fight_iq")
    adapt = _n(attacker, "adaptability")
    strength = _n(attacker, "strength")
    dfn = _n(defender, "takedown_def")
    intent = str(plan.get("td") or "Opportunistic").lower()
    p = 0.07 + grap / 520.0 + iq / 900.0 + adapt / 1200.0
    p += max(-0.05, min(0.07, (grap - dfn) / 500.0))
    p += 0.08 if intent == "aggressive" else (-0.05 if intent == "safe" else 0.0)
    p *= _clamp(0.45, 1.0, 0.48 + max(0, gas) / 190.0)
    if rng() >= _clamp(0.06, 0.58, p):
        return None

    # Secondary attacks reflect the first entry and physical profile.  This is
    # deliberately a small vocabulary of real chain-wrestling/clinch finishes,
    # not a generic "second takedown" action.
    candidates = []
    if first_action == "double_leg":
        candidates += ["single_leg", "trip"]
    else:
        candidates += ["trip", "double_leg"]
    if strength + grap >= 130:
        candidates.append("throw")
    # Prefer techniques the fighter actually knows, but allow a basic trip or
    # re-shot as an improvised continuation.
    levels = getattr(attacker, "technique_levels", {}) or {}
    names = " ".join(str(k).lower() for k in levels)
    def knows(action):
        tokens = {
            "single_leg": ("single leg", "single-leg"),
            "double_leg": ("double leg", "double-leg"),
            "trip": ("trip", "inside trip", "outside trip", "knee tap"),
            "throw": ("throw", "uchi mata", "osoto", "harai", "seoi", "suplex"),
        }[action]
        return any(t in names for t in tokens)
    learned = [a for a in candidates if knows(a)]
    pool = learned or candidates
    if not pool:
        return None
    pick = int(rng() * len(pool))
    return pool[min(len(pool) - 1, max(0, pick))]


def scramble_outcome(attacker, defender, current_pos: str, *, attacker_gas: int,
                     defender_gas: int, rng=None) -> tuple[str, str]:
    """Contested scramble result: (position, outcome).

    Scrambles now preserve the character of the starting position.  Turtle
    and front-headlock exchanges can become back control; leg entanglements
    often unwind to open guard; ordinary guard scrambles more often end in a
    half-guard top battle or on the feet.  Attributes still determine who wins.
    """
    rng = rng or random.random
    atk = (_n(attacker, "grappling") * 0.35 + _n(attacker, "speed") * 0.25 +
           _n(attacker, "fight_iq") * 0.22 + _n(attacker, "adaptability") * 0.10 +
           _n(attacker, "strength") * 0.08)
    dfn = (_n(defender, "ground_control") * 0.32 + _n(defender, "grappling") * 0.28 +
           _n(defender, "fight_iq") * 0.20 + _n(defender, "adaptability") * 0.10 +
           _n(defender, "strength") * 0.10)
    atk *= _clamp(0.52, 1.0, 0.52 + attacker_gas / 205.0)
    dfn *= _clamp(0.52, 1.0, 0.52 + defender_gas / 205.0)
    edge = atk - dfn

    # Escaping to the feet is easier from turtle/front headlock, harder from
    # mount/back, and strongly influenced by speed + gas.
    pos_bias = {
        "turtle": 0.10, "front_headlock": 0.08, "leg_entanglement": 0.05,
        "closed_guard": 0.01, "open_guard": 0.04, "half_guard": -0.02,
        "side": -0.08, "north_south": -0.08, "mount": -0.14, "back": -0.16,
    }.get(current_pos, 0.0)
    stand_p = 0.30 + pos_bias + (_n(attacker, "speed") - _n(defender, "speed")) / 500.0
    stand_p += (attacker_gas - defender_gas) / 700.0
    if rng() < _clamp(0.10, 0.58, stand_p):
        return "stand", "stand"

    attacker_top_p = _clamp(0.18, 0.82, 0.50 + edge / 155.0)
    attacker_wins = rng() < attacker_top_p
    winner_edge = edge if attacker_wins else -edge

    # Position-specific high-value outcomes.  A back take is uncommon and
    # requires a clear scrambling edge; side control is more common.
    high = _clamp(0.06, 0.38, 0.12 + winner_edge / 240.0)
    roll = rng()
    if current_pos in ("turtle", "front_headlock"):
        pos = "back" if roll < high else ("side" if roll < high + 0.28 else "half_guard")
    elif current_pos == "leg_entanglement":
        pos = "open_guard" if roll < 0.55 else "half_guard"
    elif current_pos in ("side", "north_south", "mount", "back"):
        pos = "side" if roll < high + 0.18 else "half_guard"
    else:
        pos = "side" if roll < high else "half_guard"
    return pos, "attacker_top" if attacker_wins else "defender_top"

def scouting_score(fighter, opponent) -> int:
    """0-20 information quality for this specific matchup."""
    prep = virtual_preparation(fighter, opponent)
    read = int(getattr(fighter, "opponent_read", 0) or 0)
    return int(_clamp(0, 20, read + int(prep.get("readiness", 0) or 0) // 2))


def coach_recommendation(fighter, opponent) -> str:
    """Recommend a gameplan using only information the player's camp knows.

    Low scouting never gets omniscient access to exact opponent attributes.
    As tape/camp readiness improves, the recommendation becomes matchup-
    specific and eventually approaches a full technical read.
    """
    if opponent is None:
        return "Balanced"
    score = scouting_score(fighter, opponent)
    style = str(getattr(opponent, "archetype", "") or getattr(opponent, "style", "") or "").lower()
    my_grap = _n(fighter, "grappling") + _n(fighter, "ground_control") * 0.5
    my_str = _n(fighter, "striking") + _n(fighter, "kicks") * 0.55

    if score < 4:
        if any(x in style for x in ("wrest", "sambo", "judo", "grappl", "bjj")):
            return "Anti-Wrestling"
        if any(x in style for x in ("kick", "muay", "karate", "taekwondo")):
            return "Counter"
        if my_grap >= my_str + 12:
            return "Wrestle-heavy"
        if _n(fighter, "kicks") >= _n(fighter, "striking") + 8:
            own_style = str(getattr(fighter, "amateur_discipline", "") or getattr(fighter, "style", "") or "").lower()
            return "Taekwondo Kicking" if "taekwondo" in own_style else "Kickboxing Outside"
        return "Balanced"

    # At medium scouting the coach can recognize broad strengths/weaknesses,
    # but still avoids pretending to know exact hidden numbers.
    if score < 10:
        recent = _recent_tendencies(opponent)
        if recent.get("td", 0) >= 8:
            return "Anti-Wrestling"
        if recent.get("sub", 0) >= 5 and _n(fighter, "submission_def") < 65:
            return "Wrestle-heavy" if my_grap >= my_str else "Anti-Wrestling"
        if recent.get("leg", 0) > max(recent.get("head", 0), recent.get("body", 0)):
            return "Counter"
        if recent.get("ctrl", 0) >= 120:
            return "Anti-Wrestling"
        return "Balanced" if abs(my_grap - my_str) < 10 else ("Wrestle-heavy" if my_grap > my_str else "Pressure")

    # Deep scouting earns the detailed matchup answer.
    fs=lambda key: _n(fighter,key,0)
    os=lambda key: _n(opponent,key,0)
    opp_grap=os("grappling") + os("ground_control")*.5
    my_grap=fs("grappling") + fs("ground_control")*.5
    my_str=fs("striking") + fs("kicks")*.55
    opp_str=os("striking") + os("kicks")*.55
    if my_grap >= opp_grap + 12 and fs("submissions") >= os("submission_def") + 8:
        return "Submission Hunter"
    if my_grap >= opp_grap + 10:
        return "Wrestle-heavy"
    if os("grappling") >= fs("takedown_def") + 10:
        return "Anti-Wrestling"
    if fs("kicks") >= os("striking_def") + 10 and fs("distance_management") >= os("distance_management"):
        own_style = str(getattr(fighter, "amateur_discipline", "") or getattr(fighter, "style", "") or "").lower()
        return "Taekwondo Kicking" if "taekwondo" in own_style else "Kickboxing Outside"
    if fs("ko_power") >= os("durability") + 10 and fs("cardio") >= 45:
        return "Pressure"
    if os("cardio") <= 40 and fs("cardio") >= os("cardio") + 8:
        return "Body Attack"
    if opp_str >= my_str + 12:
        return "Counter"
    return "Balanced"


def scout_lines(fighter, opponent) -> list[str]:
    """Layered report where information quality comes from actual preparation."""
    prep = virtual_preparation(fighter, opponent)
    score = scouting_score(fighter, opponent)
    recent = _recent_tendencies(opponent)
    style = getattr(opponent, "style", None) or "MMA"
    lines = ["Scout (%s/20):" % score]
    if score <= 1:
        return lines + ["  Very little reliable tape."]
    lines.append("  %s · %s · %scm · reach %scm." % (
        style, getattr(opponent, "stance", "Orthodox"), getattr(opponent, "height", "?"), getattr(opponent, "reach", "?")))
    if score >= 4:
        tags = []
        if recent.get("td", 0) >= 8: tags.append("frequent takedown entries")
        if recent.get("sub", 0) >= 5: tags.append("active submission chains")
        if recent.get("ctrl", 0) >= 120: tags.append("control-heavy grappling")
        target = max(("head", "body", "leg"), key=lambda k: recent.get(k, 0)) if recent.get("fights", 0) else None
        if target and recent.get(target, 0) >= 4: tags.append("often attacks the %s" % target)
        if tags:
            lines.append("  Tendencies: %s." % ", ".join(tags[:3]))
    if score >= 7:
        def band(v):
            return "high" if int(v) >= 70 else "solid" if int(v) >= 55 else "limited" if int(v) < 42 else "average"
        lines.append("  Gas %s · power %s · grappling %s." % (
            band(_n(opponent, "cardio")), band(_n(opponent, "ko_power")), band(_n(opponent, "grappling"))))
    if score >= 10:
        vals = {
            "hands": int(_n(opponent, "striking")), "kicks": int(_n(opponent, "kicks")),
            "wrestling": int(_n(opponent, "grappling")), "submissions": int(_n(opponent, "submissions")),
            "TDD": int(_n(opponent, "takedown_def")), "striking defense": int(_n(opponent, "striking_def")),
            "durability": int(_n(opponent, "durability")), "cardio": int(_n(opponent, "cardio")),
        }
        hi = sorted(vals.items(), key=lambda x: x[1], reverse=True)[:2]
        lo = sorted(vals.items(), key=lambda x: x[1])[:2]
        lines.append("  Strengths: %s." % ", ".join(k for k, _ in hi))
        lines.append("  Vulnerabilities: %s." % ", ".join(k for k, _ in lo))
    if score >= 14:
        predicted = choose_mma_plan(opponent, fighter)
        lines.append("  Likely approach: %s · %s pace." % (predicted.get("name", "Balanced"), predicted.get("pace", "mid")))
    if score >= 17:
        levels = getattr(opponent, "technique_levels", {}) or {}
        best = sorted(levels.items(), key=lambda x: x[1], reverse=True)[:3]
        if best:
            lines.append("  Best techniques: %s." % ", ".join("%s L%s" % (k, v) for k, v in best))
    if prep and score >= 8:
        strengths = sorted(
            ((k, int(prep.get(k, 0) or 0)) for k in ("anti_wrestling", "close_distance", "range_defense", "submission_safety", "pace_plan", "damage_plan")),
            key=lambda kv: kv[1], reverse=True,
        )
        labels = {
            "anti_wrestling":"anti-wrestling", "close_distance":"closing distance",
            "range_defense":"range defense", "submission_safety":"submission safety",
            "pace_plan":"pace", "damage_plan":"damage awareness",
        }
        good = [labels[k] for k, v in strengths if v >= 3][:2]
        if good:
            lines.append("  Camp prep: %s." % ", ".join(good))
    return lines


def preparation_summary(fighter) -> str:
    """Compact human-readable summary of the current opponent-specific camp."""
    prep = _prep_dict(fighter)
    if not prep:
        return ""
    labels = {
        "anti_wrestling":"anti-wrestling", "close_distance":"closing distance",
        "range_defense":"range defense", "submission_safety":"submission safety",
        "pace_plan":"pace", "damage_plan":"damage awareness",
    }
    ranked = sorted(
        ((k, int(prep.get(k, 0) or 0)) for k in labels),
        key=lambda kv: kv[1], reverse=True,
    )
    bits = ["%s %s" % (labels[k], v) for k, v in ranked if v > 0][:3]
    ready = int(prep.get("readiness", 0) or 0)
    return ("readiness %s/12" % ready) + ((" · " + " · ".join(bits)) if bits else "")
