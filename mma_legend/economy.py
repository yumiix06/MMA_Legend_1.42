"""Weekly ledger."""
from __future__ import annotations


def snapshot(fighter) -> dict:
    return dict(getattr(fighter, "last_ledger", None) or {})


def record(fighter, income: dict, expenses: dict) -> dict:
    inc = sum(int(v) for v in income.values())
    exp = sum(int(v) for v in expenses.values())
    led = {"income": income, "expenses": expenses, "net": inc - exp}
    fighter.last_ledger = led
    return led


def render(console, fighter) -> None:
    led = snapshot(fighter)
    console.section("Money this week")
    if not led:
        console.print("  No ledger yet.")
        return
    for k, v in (led.get("income") or {}).items():
        console.print("  + $%s  %s" % (v, k))
    for k, v in (led.get("expenses") or {}).items():
        console.print("  - $%s  %s" % (v, k))
    console.print("  NET $%s" % led.get("net", 0))


def weekly_breakdown(fighter) -> tuple[dict, dict]:
    """The exact recurring cash flows for one ordinary week.

    Side jobs are *not* passive salary: they pay when the player works a shift.
    Manager cuts are taken from purses at payout, not charged again weekly.
    Sponsor retainers are real passive income and are actually credited.
    """
    pro = bool(getattr(fighter, "pro_debut", False))
    fame = int(getattr(fighter, "fame", 0) or 0)
    rent = 25 if not pro else 40 + min(60, fame)
    food = 18
    gym = 10 if not pro else 20
    travel = 15 if (pro and getattr(fighter, "booked_fight", None)
                    and str(getattr(fighter, "room", "") or "") not in ("", "local")) else 0
    sponsor = (15 if pro else 5) * min(3, len(getattr(fighter, "sponsors", None) or []))
    income = {}
    if sponsor:
        income["sponsor retainer"] = sponsor
    expenses = {"rent": rent, "food": food, "gym": gym}
    if travel:
        expenses["fight travel"] = travel
    return income, expenses


def apply_weekly(fighter, apply_cash: bool = False) -> dict:
    income, expenses = weekly_breakdown(fighter)
    led = record(fighter, income, expenses)
    if apply_cash:
        fighter.money = int(getattr(fighter, "money", 0) or 0) + int(led.get("net", 0) or 0)
    return led

