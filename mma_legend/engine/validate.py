"""Fight-log checker used by diagnostics and live fights.

Works with both the lightweight 1.1 stub engine and a full tick engine
if one is dropped in later. Never raises to the player.
"""
from __future__ import annotations

ILLEGAL_AMATEUR = frozenset({"heel_hook", "elbow", "knee_head", "ground_elbow"})
LEGAL_WINNERS = frozenset({"player", "opponent", "draw"})


def _action_id(event) -> str:
    if isinstance(event, dict):
        return str(event.get("action_id") or event.get("id") or "")
    return str(getattr(event, "action_id", "") or "")


def _is_amateur(outcome) -> bool:
    notes = getattr(outcome, "notes", None) or []
    if any(str(n).lower() == "amateur" for n in notes):
        return True
    sport = str(getattr(outcome, "sport", "") or "")
    # rules object is not always attached; default to amateur-safe if periods look amateur
    return bool(getattr(outcome, "amateur", False)) or sport.endswith("_am")


def validate_fight_log(outcome) -> list[str]:
    """Return a list of human-readable problems. Empty list = clean."""
    issues: list[str] = []
    if outcome is None:
        return ["outcome is None"]

    winner = getattr(outcome, "winner", None)
    if winner not in LEGAL_WINNERS:
        issues.append("bad winner value %r" % (winner,))

    method = getattr(outcome, "method", None)
    if not method:
        issues.append("missing method")

    log = list(getattr(outcome, "log", None) or [])
    if not log:
        issues.append("empty fight log")

    amateur = _is_amateur(outcome)
    rules = getattr(outcome, "rules", None)
    if rules is not None:
        amateur = bool(getattr(rules, "amateur", amateur))

    if amateur:
        bad = [_action_id(e) for e in log if _action_id(e) in ILLEGAL_AMATEUR]
        if bad:
            issues.append("amateur illegal actions: %s" % ", ".join(sorted(set(bad))))

    for who, stats_name in (("player", "f_stats"), ("opp", "o_stats")):
        stats = getattr(outcome, stats_name, None)
        if stats is None:
            continue
        for attr in (
            "strikes_landed", "strikes_attempted",
            "takedowns_landed", "takedowns_attempted",
            "head_landed", "body_landed", "leg_landed",
        ):
            val = getattr(stats, attr, 0) or 0
            try:
                if int(val) < 0:
                    issues.append("%s.%s is negative" % (who, attr))
            except (TypeError, ValueError):
                issues.append("%s.%s is not a number" % (who, attr))
        landed = int(getattr(stats, "strikes_landed", 0) or 0)
        attempted = int(getattr(stats, "strikes_attempted", 0) or 0)
        if landed > attempted:
            issues.append("%s strikes landed > attempted" % who)

    return issues
