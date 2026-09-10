"""Persistent, low-noise career alerts."""
from __future__ import annotations


def push(fighter, kind: str, text: str) -> None:
    inbox = list(getattr(fighter, "notes", None) or [])
    # Do not stack the same unresolved alert every week.
    for row in reversed(inbox[-8:]):
        if row.get("text") == text and not row.get("read", False):
            return
    inbox.append({
        "kind": kind, "text": text,
        "week": int(getattr(fighter, "week", 0) or 0),
        "read": False,
    })
    fighter.notes = inbox[-24:]


def unread(fighter) -> list:
    return [n for n in list(getattr(fighter, "notes", None) or []) if not n.get("read", False)]


def render(console, fighter) -> None:
    rows = unread(fighter)
    if not rows:
        return
    mark = {"CRITICAL": "!", "IMPORTANT": "*", "PROGRESSION": "+", "WORLD": "~", "FINANCIAL": "$"}
    console.section("ALERTS · %s unread" % len(rows))
    for n in rows[-2:]:
        console.print("  %s %s" % (mark.get(n.get("kind"), "-"), n.get("text")))
    if len(rows) > 2:
        console.print("  ... %s more · Career > Alerts" % (len(rows) - 2), style="dim")


def inbox_menu(console, fighter) -> None:
    rows = list(getattr(fighter, "notes", None) or [])
    console.header("ALERTS / INBOX", "Career information that needs your attention")
    if not rows:
        console.info("No alerts.")
        return
    mark = {"CRITICAL": "!", "IMPORTANT": "*", "PROGRESSION": "+", "WORLD": "~", "FINANCIAL": "$"}
    for n in rows[-12:]:
        state = "" if n.get("read", False) else "NEW "
        console.print("  %s%s W%s · %s" % (state, mark.get(n.get("kind"), "-"), n.get("week", "?"), n.get("text", "")))
    for n in rows:
        n["read"] = True
    fighter.notes = rows[-24:]
    console.print("  X) Back")
    console.ask("Back > ")
