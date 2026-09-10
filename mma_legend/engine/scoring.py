"""Round scoring for every ruleset (1.11).

Two separate jobs live here, because two different sports were previously
sharing one ad-hoc block of arithmetic inside the tick loop:

**MMA — the 10-Point Must System.** Judges are instructed to find a winner in
every round. A 10-10 round is a genuine rarity, not the default, and the old
engine produced them constantly (21% of decisions came back as equal cards,
and impossible three-round totals like 29-27 showed up regularly). Criteria
are applied in the real order of precedence: effective striking/grappling
*damage* first, then control/dominance, then volume.

**Submission grappling — ADCC-style points.** Points are awarded for position
advancement, and in the ADCC format the first half of a match is scored
without points (only negatives apply), which rewards the fighter who actually
tries to finish rather than the one who stalls to a lead.

Three judges score independently with small honest disagreements, so split and
majority decisions fall out naturally instead of every card being identical.
"""
from __future__ import annotations

import random

# --- MMA -------------------------------------------------------------

# Judges disagree at the margins. Each has a lean toward one criterion.
JUDGE_LEANS = ("damage", "control", "volume")


def round_edge(a, b, dmg_a: int, dmg_b: int, ctrl_a: int = 0, ctrl_b: int = 0,
               lean: str = "damage") -> float:
    """Signed advantage for fighter A this round, weighted by a judge's lean.

    `a` / `b` are per-round stat deltas, not fight totals.
    """
    kd_a = int(getattr(a, "knockdowns", 0) or 0)
    kd_b = int(getattr(b, "knockdowns", 0) or 0)
    sig_a = int(getattr(a, "strikes_landed", 0) or 0)
    sig_b = int(getattr(b, "strikes_landed", 0) or 0)
    sub_a = int(getattr(a, "submission_attempts", 0) or 0)
    sub_b = int(getattr(b, "submission_attempts", 0) or 0)

    # Damage is the primary criterion. Head shots weigh more than raw volume.
    head_a = int(getattr(a, "head_landed", 0) or 0)
    head_b = int(getattr(b, "head_landed", 0) or 0)
    body_a = int(getattr(a, "body_landed", 0) or 0)
    body_b = int(getattr(b, "body_landed", 0) or 0)
    damage = ((int(dmg_a) - int(dmg_b)) * 1.0
              + (kd_a - kd_b) * 6.0
              + (head_a - head_b) * 0.45
              + (body_a - body_b) * 0.28)
    # Control and threatened finishes.
    # Judges reward control and position more heavily than this model used to
    # — a round spent on top is very hard to lose on the cards. Under the old
    # weight a grappler could dominate positionally and still lose the round.
    control = (int(ctrl_a) - int(ctrl_b)) * 1.0 + (sub_a - sub_b) * 2.0
    control += (int(getattr(a, "passes", 0) or 0) - int(getattr(b, "passes", 0) or 0)) * 1.5
    control += (int(getattr(a, "takedowns_landed", 0) or 0)
                - int(getattr(b, "takedowns_landed", 0) or 0)) * 1.2
    # Volume is the tiebreaker, deliberately the weakest input.
    volume = (sig_a - sig_b) * 0.35

    w = {"damage": (1.25, 0.85, 0.7), "control": (0.9, 1.35, 0.7),
         "volume": (0.95, 0.8, 1.25)}.get(lean, (1.0, 1.0, 1.0))
    return damage * w[0] + control * w[1] + volume * w[2]


def score_round(a, b, dmg_a: int, dmg_b: int, ctrl_a: int = 0, ctrl_b: int = 0,
                lean: str = "damage") -> tuple:
    """Return (score_a, score_b) under the 10-Point Must System.

    10-9  the normal round
    10-8  clear dominance: a knockdown plus control, or overwhelming damage
    10-7  exceptional, near-stoppage
    10-10 only when the round is genuinely indistinguishable
    """
    edge = round_edge(a, b, dmg_a, dmg_b, ctrl_a, ctrl_b, lean)
    jitter = {"damage": 0.32, "control": 0.48, "volume": 0.58}.get(lean, 0.4)
    edge += random.uniform(-jitter, jitter)
    kd_a = int(getattr(a, "knockdowns", 0) or 0)
    kd_b = int(getattr(b, "knockdowns", 0) or 0)

    # Judges must find a winner. Only a virtually dead-even round is 10-10.
    if abs(edge) < 0.12 and kd_a == kd_b:
        return (10, 10)

    win_a = edge > 0
    margin = abs(edge)
    kd_win = kd_a if win_a else kd_b
    kd_lose = kd_b if win_a else kd_a

    loser = 9
    # 10-8 needs real dominance, not merely a single knockdown.
    if margin >= 16 or (kd_win >= 1 and margin >= 9) or kd_win >= 2:
        loser = 8
    # 10-7 is reserved for a round the referee nearly stopped.
    if margin >= 28 and kd_win >= 2 and kd_lose == 0:
        loser = 7
    return (10, loser) if win_a else (loser, 10)


class Scorecard:
    """One judge's card across a fight."""

    def __init__(self, name: str, lean: str = "damage"):
        self.name = name
        self.lean = lean
        self.rounds = []

    def add(self, sa: int, sb: int) -> None:
        self.rounds.append((int(sa), int(sb)))

    @property
    def totals(self) -> tuple:
        return (sum(r[0] for r in self.rounds), sum(r[1] for r in self.rounds))

    def winner(self) -> str:
        a, b = self.totals
        if a > b:
            return "a"
        if b > a:
            return "b"
        return "draw"

    def line(self) -> str:
        a, b = self.totals
        return "%s: %s-%s" % (self.name, a, b)


JUDGE_NAMES = (
    "D. Vance", "R. Okafor", "M. Sciarra", "L. Petrov", "A. Tanaka",
    "J. Whitfield", "C. Moreau", "S. Halvorsen",
)


def make_judges(rng=None) -> list:
    """Three judges with different leanings."""
    rng = rng or random
    names = list(JUDGE_NAMES)
    rng.shuffle(names)
    leans = list(JUDGE_LEANS)
    rng.shuffle(leans)
    return [Scorecard(names[i], leans[i]) for i in range(3)]


def decision(cards: list) -> tuple:
    """Resolve three cards into (winner, label)."""
    votes = [c.winner() for c in cards]
    a = votes.count("a")
    b = votes.count("b")
    d = votes.count("draw")
    if a == 3:
        return ("a", "Unanimous Decision")
    if b == 3:
        return ("b", "Unanimous Decision")
    if a == 2 and d == 1:
        return ("a", "Majority Decision")
    if b == 2 and d == 1:
        return ("b", "Majority Decision")
    if a == 2:
        return ("a", "Split Decision")
    if b == 2:
        return ("b", "Split Decision")
    if a == 1 and b == 1 and d == 1:
        ta = sum(c.totals[0] for c in cards)
        tb = sum(c.totals[1] for c in cards)
        if ta != tb:
            return (("a" if ta > tb else "b"), "Split Decision")
        return ("draw", "Majority Draw")
    if d >= 2:
        return ("draw", "Draw")
    return ("draw", "Split Draw")


def mma_round_score(a, b, dmg_a: int, dmg_b: int, ctrl_a: int = 0, ctrl_b: int = 0) -> tuple:
    return score_round(a, b, dmg_a, dmg_b, ctrl_a, ctrl_b)


ADCC_POINTS = {
    "takedown": 2, "clean_takedown": 4, "guard_pass": 3, "mount": 2,
    "back_control": 3, "knee_on_belly": 2, "sweep": 2, "clean_sweep": 4,
}
PAST_GUARD = frozenset({"side", "mount", "back"})
ADCC_PENALTIES = {"pull_guard": -1, "flee_position": -1, "stalling": -1}


def adcc_points_active(period: int, periods: int) -> bool:
    if periods <= 1:
        return True
    return period > (periods // 2)


def grappling_result(a_points: int, b_points: int, a_ctrl: int, b_ctrl: int,
                     a_subs: int, b_subs: int) -> tuple:
    if a_points != b_points:
        return (("a" if a_points > b_points else "b"), "Points")
    if a_subs != b_subs:
        return (("a" if a_subs > b_subs else "b"), "Referee Decision")
    if a_ctrl != b_ctrl:
        return (("a" if a_ctrl > b_ctrl else "b"), "Referee Decision")
    return ("a" if random.random() < 0.5 else "b", "Referee Decision")
