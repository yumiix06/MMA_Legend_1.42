"""Combat facade. Real simulation lives in mma_legend.engine."""
from __future__ import annotations

from .engine import simulate_fight
from .engine.fight import _clock
from .engine.rules import MMARuleset, GrapplingRuleset
from .engine.commentary import describe
from . import diagnostics


def _fmt_ctrl(st) -> str:
    sec = int(getattr(st, "control_sec", 0) or 0)
    if sec <= 0:
        ticks = int(getattr(st, "control_ticks", 0) or 0)
        sec = ticks * 8
    return _clock(sec)


def get_gameplan_mod(gameplan: str) -> dict:
    if gameplan == "Aggressive":
        return {"offense": 8, "defense": -8, "sub": -2, "finish": 10, "energy_drain": 1.3}
    if gameplan == "Counter":
        return {"offense": -4, "defense": 8, "sub": 0, "finish": -5, "energy_drain": 0.8}
    if gameplan == "Wrestle-heavy":
        return {"offense": 2, "defense": 4, "sub": 5, "grapple": 8, "finish": 3, "energy_drain": 1.1}
    return {"offense": 2, "defense": 2, "sub": 2, "grapple": 2, "finish": 2, "energy_drain": 1.0}


def fight_mma(console, fighter, opponent, rounds=3, gameplan="Balanced", interactive=True):
    amateur = not bool(getattr(fighter, "pro_debut", False))
    title = bool(getattr(fighter, "_pending_title", False))
    rules = MMARuleset(amateur=amateur, title=title)
    if rounds and not title:
        rules.periods = max(1, int(rounds))
    # Quick = no player choices, but the engine still needs interactive=True
    # so it can print a live compact feed. The old gate set interactive=False
    # and the sim finished in silence.
    live = bool(interactive and console is not None)
    outcome = simulate_fight(fighter, opponent, rules, gameplan=gameplan, console=console, interactive=live)
    diagnostics.check_outcome_live(outcome, console, context="mma fight")
    fighter._last_outcome = outcome
    opponent._last_outcome = outcome
    return outcome.finish_label, outcome.f_score, outcome.o_score, outcome.technique


def fight_grappling(console, fighter, opponent, gameplan="Wrestle-heavy", interactive=True):
    rules = GrapplingRuleset()
    outcome = simulate_fight(fighter, opponent, rules, gameplan=gameplan, console=console, interactive=interactive)
    diagnostics.check_outcome_live(outcome, console, context="grappling match")
    fighter._last_outcome = outcome
    opponent._last_outcome = outcome
    return outcome


def post_fight_analysis(console, fighter, opponent, finish, rounds, fighter_score, opp_score, technique_used=None) -> None:
    outcome = getattr(fighter, "_last_outcome", None)
    console.print("\nPOST-FIGHT")
    if outcome is None:
        console.print("Result: %s" % (finish or "Decision"))
        return
    fs, os = outcome.f_stats, outcome.o_stats
    console.print("RESULT  %s — %s" % (outcome.result_word, outcome.method))
    why = []
    if fs.body_landed > os.body_landed + 2:
        why.append("Body work slowed him")
    if fs.leg_landed > os.leg_landed + 2:
        why.append("Calf kicks took the stance")
    if fs.takedowns_landed > os.takedowns_landed:
        why.append("Takedowns won the floor")
    if fs.knockdowns > os.knockdowns:
        why.append("Knockdowns %s-%s" % (fs.knockdowns, os.knockdowns))
    if fs.strikes_landed > os.strikes_landed + 6:
        why.append("Volume on the feet")
    if why:
        console.print("WHY  " + "; ".join(why[:3]))
    nice = [n for n in (outcome.notes or []) if n and str(n).lower() not in ("amateur", "pro")]
    if nice:
        console.print("MOMENTS  " + ", ".join(nice[-4:]))
    console.table(
        "Fight Stats",
        ["Metric", fighter.name, opponent.name],
        [
            ["Sig. Strikes", "%s/%s" % (fs.strikes_landed + fs.ground_strikes_landed, fs.strikes_attempted + fs.ground_strikes_attempted),
             "%s/%s" % (os.strikes_landed + os.ground_strikes_landed, os.strikes_attempted + os.ground_strikes_attempted)],
            ["Ground strikes", "%s/%s" % (fs.ground_strikes_landed, fs.ground_strikes_attempted),
             "%s/%s" % (os.ground_strikes_landed, os.ground_strikes_attempted)],
            ["Head / Body / Leg",
             "%s/%s/%s" % (fs.head_landed, fs.body_landed, fs.leg_landed),
             "%s/%s/%s" % (os.head_landed, os.body_landed, os.leg_landed)],
            ["Takedowns", "%s/%s" % (fs.takedowns_landed, fs.takedowns_attempted),
             "%s/%s" % (os.takedowns_landed, os.takedowns_attempted)],
            ["Sub Attempts", fs.submission_attempts, os.submission_attempts],
            ["Control time", _fmt_ctrl(fs), _fmt_ctrl(os)],
            ["Knockdowns", fs.knockdowns, os.knockdowns],
            ["Times down", fs.times_down, os.times_down],
            ["Damage taken", "%s%%" % fighter.damage.get("total", 0), "%s%%" % opponent.damage.get("total", 0)],
        ],
    )
    fighter.last_fight_stats = fs.as_dict()
    opponent.last_fight_stats = os.as_dict()
    if fighter.damage.get("body", 0) >= opponent.damage.get("body", 0) + 6:
        console.info("Body work showed up on the gas tank.")
    console.read_pause("post fight", extra=0.15)
