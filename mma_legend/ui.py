"""Simple mobile-friendly console UI — plain text, no external deps."""
from __future__ import annotations

import os
import re
import sys
import time
from typing import Optional, Sequence


def _ascii_bar(value: int, width: int = 8) -> str:
    """Phone-safe meters. Block chars render as garbage on many iOS terminals."""
    value = max(0, min(100, int(value)))
    filled = round(value / 100 * width)
    return "#" * filled + "-" * (width - filled)


def wrap_text(text: str, width: int = 42) -> list:
    text = " ".join(str(text).split())
    width = max(4, int(width or 42))
    if len(text) <= width:
        return [text]
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        # URLs/ids/compound labels can be longer than a phone line.  The old
        # wrapper emitted them untouched, defeating every caller's width
        # guarantee. Split only when necessary; normal words are unchanged.
        if len(w) > width:
            if cur:
                lines.append(cur)
                cur = ""
            while len(w) > width:
                lines.append(w[:width])
                w = w[width:]
            cur = w
            continue
        trial = (cur + " " + w).strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


# ANSI SGR codes only — no extended/truecolor, no box-drawing glyphs.
# Basic 16-color ANSI is supported by essentially every terminal app people
# run this in (Termux, a-Shell, iSH, Pythonista's console), unlike the
# Unicode block characters that caused the 0.5.7 "looked like static" bug.
_ANSI = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "green": "\033[32m", "red": "\033[31m", "yellow": "\033[33m",
    "cyan": "\033[36m", "magenta": "\033[35m", "blue": "\033[34m",
    "gray": "\033[90m",
    # Bright variants — still basic 16-colour, safe on iOS terminals.
    "bgreen": "\033[92m", "bred": "\033[91m", "byellow": "\033[93m",
    "bcyan": "\033[96m", "bmagenta": "\033[95m", "bblue": "\033[94m",
    "white": "\033[97m",
    "inv": "\033[7m",
}

# Semantic colours, so screens stay consistent instead of each picking its own.
ROLE_COLOR = {
    "fighter": "bcyan", "coach": "bgreen", "manager": "byellow",
    "promoter": "bmagenta", "matchmaker": "bblue", "media": "gray",
}
TAG_COLOR = {
    "trap": "bred", "tune-up": "bgreen", "short notice": "byellow",
    "catchweight": "magenta", "rematch": "bmagenta", "even": "bcyan",
    "contender series": "byellow",
}


def _bar_color(value: int) -> str:
    if value >= 66:
        return "green"
    if value >= 33:
        return "yellow"
    return "red"


class GameConsole:
    """Plain console UI tuned for phones/small screens."""

    def __init__(self, width: int = 44, fast: bool = True, color: Optional[bool] = None):
        self.width = max(32, min(width, 60))
        self.fast = fast
        if color is None:
            # iOS consoles (Pythonista/Pyto) may report a non-TTY even though ANSI
            # colours render correctly. Prefer colour there; NO_COLOR/--no-color wins.
            ios_console = sys.platform == "ios" or bool(os.environ.get("PYTHONISTA"))
            color = (sys.stdout.isatty() or ios_console) and not os.environ.get("NO_COLOR")
        self.color = bool(color)

    def _c(self, text: str, *styles: str) -> str:
        if not self.color:
            return text
        codes = "".join(_ANSI.get(s, "") for s in styles)
        return f"{codes}{text}{_ANSI['reset']}" if codes else text

    def print(self, msg: str = "", style: Optional[str] = None) -> None:
        clean = re.sub(r"\[/?[a-zA-Z]+(?: [^]]+)?\]", "", str(msg))
        if style and self.color:
            clean = self._c(clean, style)
        try:
            from . import telemetry
            telemetry.ui_output(clean)
        except Exception:
            pass
        print(clean)

    def good(self, msg: str) -> None:
        self._status("✅ ", msg, "green")

    def warn(self, msg: str) -> None:
        self._status("⚠️ ", msg, "yellow")

    def info(self, msg: str) -> None:
        self._status("ℹ️ ", msg, "cyan")

    def gold(self, msg: str) -> None:
        self._status("⭐ ", msg, "yellow", bold=True)

    def milestone(self, msg: str) -> None:
        self._status("🏆 ", msg, "magenta", bold=True)

    def _status(self, prefix: str, msg: str, style: str, bold: bool = False) -> None:
        """Width-safe semantic status line with aligned continuations."""
        plain_prefix = str(prefix)
        room = max(12, self.width - len(plain_prefix))
        chunks = wrap_text(str(msg), room)
        styles = ("bold", style) if bold else (style,)
        for i, chunk in enumerate(chunks):
            lead = plain_prefix if i == 0 else " " * len(plain_prefix)
            self.print(self._c(lead + chunk, *styles))

    def title_line(self, msg: str) -> None:
        self.print(self._c(f"=== {msg} ===", "bold"))

    def rule(self, title: str = "") -> None:
        self.print(self._c("-" * self.width, "gray"))
        if title:
            self.print(self._c(title, "bold"))

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        try:
            from . import telemetry
            telemetry.set_screen(title, subtitle or "")
        except Exception:
            pass
        self.print()
        self.print(self._c("=" * self.width, "bcyan"))
        self.print(self._c(title.center(self.width), "bold", "bcyan"))
        if subtitle:
            self.print(self._c(subtitle.center(self.width), "dim"))
        self.print(self._c("=" * self.width, "bcyan"))

    def banner(self, title: str, style: str = "bmagenta") -> None:
        """A heavier, attention-grabbing header for real moments."""
        try:
            from . import telemetry
            telemetry.set_screen(title, "")
        except Exception:
            pass
        pad = " %s " % title.strip().upper()
        line = pad.center(self.width, "*")
        self.print()
        self.print(self._c("*" * self.width, style))
        self.print(self._c(line, "bold", style))
        self.print(self._c("*" * self.width, style))

    def box(self, lines: Sequence[str], style: str = "gray") -> None:
        """ASCII-framed block. No Unicode box glyphs — they render as static
        on some iOS terminals."""
        inner = self.width - 4
        self.print(self._c("+" + "-" * (self.width - 2) + "+", style))
        for raw in lines:
            for ln in wrap_text(str(raw), inner):
                self.print(self._c("| ", style) + ln.ljust(inner) + self._c(" |", style))
        self.print(self._c("+" + "-" * (self.width - 2) + "+", style))

    def kv(self, label: str, value, style: Optional[str] = None,
           label_w: int = 14) -> None:
        """Aligned label/value row — the workhorse for stat screens."""
        lab = self._c(str(label)[:label_w].ljust(label_w), "dim")
        val = str(value)
        self.print(lab + (self._c(val, style) if style else val))

    def badge(self, text: str, style: str = "bcyan") -> str:
        """Inline highlighted chip, e.g. a fight tag."""
        return self._c(" %s " % str(text).upper(), "bold", "inv", style)

    def tag(self, name: str) -> str:
        return self.badge(name, TAG_COLOR.get(str(name).lower(), "bcyan"))

    def money(self, amount) -> str:
        try:
            n = int(amount)
        except (TypeError, ValueError):
            return str(amount)
        if n < 0:
            return self._c("-$%s" % format(abs(n), ","), "bold", "bred")
        return self._c("$%s" % format(n, ","), "bgreen")

    def npc_line(self, obj, show_traits: bool = True) -> None:
        """One consistent line for any NPC — fighter, coach, manager, promoter."""
        try:
            from . import npc as _npc
            p = _npc.profile(obj)
        except Exception:
            self.print("  %s" % getattr(obj, "name", "?"))
            return
        head = "%s  %s" % (
            self._c(p["name"], "bold", ROLE_COLOR.get(p["role"], "bcyan")),
            self._c(p["role_label"], "dim"),
        )
        extra = p.get("archetype") or p.get("org") or ""
        if extra:
            head += self._c(" · %s" % extra, "dim")
        self.print("  " + head)
        if show_traits and p.get("traits"):
            self.print("    " + self._c(", ".join(p["traits"]), "gray"))


    # ---------------- fight HUD ----------------

    def fight_bar(self, label: str, dmg: int, gas: int, width: int = 10,
                  mine: bool = False) -> None:
        """One fighter's line in the live HUD: health bar + gas."""
        hp = max(0, min(100, 100 - int(dmg) * 4))
        filled = int(round(hp / 100.0 * width))
        bar = "#" * filled + "." * (width - filled)
        style = "bcyan" if mine else "bred"
        if hp <= 30:
            style = "bred" if mine else "byellow"
        self.print("%s %s %s" % (
            self._c(str(label)[:6].ljust(6), "bold", style),
            self._c(bar, style),
            self._c("gas %3d" % int(gas), "dim"),
        ))

    def fight_head(self, period: int, clock: str, position: str,
                   me: str, him: str, f_dmg: int, o_dmg: int,
                   f_gas: int, o_gas: int, f_body=None, o_body=None) -> None:
        """Compact round header. Replaces the old three-line banner that
        repeated both gas numbers and burned four lines of a phone screen."""
        self.print("")
        self.print(self._c("-- R%s  %s  %s" % (period, clock, position), "bold", "byellow"))
        self.fight_bar(me, f_dmg, f_gas, mine=True)
        self.fight_damage_line(f_body, mine=True)
        self.fight_bar(him, o_dmg, o_gas, mine=False)
        self.fight_damage_line(o_body, mine=False)

    def fight_damage_line(self, body, mine: bool = False) -> None:
        """Compact live body map: head, body, both legs and worst cut."""
        if body is None:
            return
        try:
            loc = body.loc
            _zone, cut = body.worst_cut()
            vals = (
                int(loc.get("head", 0)), int(loc.get("body", 0)),
                int(loc.get("lead_leg", 0)), int(loc.get("rear_leg", 0)),
                int(cut),
            )
        except (AttributeError, TypeError, ValueError):
            return
        style = "bcyan" if mine else "bred"
        head, body_d, lead, rear, cut = vals
        worst = max(lead, rear)
        # Keep the established H/B/L/C scan order while exposing both leg
        # sides after it.  Existing players can still read L as "worst leg".
        text = "H%02d B%02d L%02d C%02d · L/R%02d/%02d" % (
            head, body_d, worst, cut, lead, rear)
        self.print("       " + self._c(text, style))

    def feed(self, text: str, mine: bool = None, tag: str = "") -> None:
        """One exchange in the fight feed.

        Prefixed and coloured by who acted, so the fight can be scanned rather
        than read. `tag` is a short right-hand marker (KD, SUB, TD).
        """
        if mine is True:
            pre, style = ">", "bcyan"
        elif mine is False:
            pre, style = "<", "bred"
        else:
            pre, style = " ", "dim"
        text = " ".join(str(text).split())
        reserve = (len(tag) + 1) if tag else 0
        body_w = max(12, self.width - 2 - reserve)
        chunks = wrap_text(text, body_w)
        for i, chunk in enumerate(chunks):
            marker = pre if i == 0 else " "
            plain = "%s %s" % (marker, chunk)
            if i == 0 and tag:
                room = max(1, self.width - len(plain) - len(tag))
                self.print(self._c(plain, style) + " " * room
                           + self._c(tag, "bold", "byellow"))
            else:
                self.print(self._c(plain, style))

    def moment(self, period: int, position: str, options) -> None:
        """The player's choice prompt, on its own lines and compact."""
        self.print("")
        self.print(self._c("YOUR MOVE  R%s  %s" % (period, position), "bold", "bmagenta"))
        letters = "ABCDEF"
        # Wrap the plain text first. ANSI escape sequences used to count as
        # visible characters and caused needless wrapping in color terminals.
        row = "   ".join("%s %s" % (letters[i], o)
                         for i, o in enumerate(options))
        for chunk in wrap_text(row, self.width):
            self.print(chunk)

    def section(self, title: str) -> None:
        """Lightweight section heading for phone screens."""
        self.print()
        self.print(self._c(str(title).upper(), "bold", "byellow"))

    def panel(self, title: str, lines: Sequence[str]) -> None:
        """Compact information block; intentionally lighter than a full box."""
        self.print(self._c(str(title).upper(), "bold", "bcyan"))
        for raw in lines:
            for line in wrap_text(str(raw), max(12, self.width - 3)):
                self.print("  " + line)

    def bar_line(self, label: str, value: int, width: int = 8, suffix: str = "") -> str:
        value = max(0, min(100, int(value)))
        bar = _ascii_bar(value, width)
        bar = self._c(bar, _bar_color(value))
        return "%-10s %s %3d%s" % (label[:10], bar, value, suffix)

    def person_card(self, role: str, name: str, quirk: str = "", rapport: int = 50, memory: str = "") -> None:
        """Shared 1.3 header: ROLE · NAME · QUIRK / bar / last memory."""
        line1 = "%s · %s" % ((role or "PERSON").upper(), name or "?")
        if quirk:
            line1 += " · %s" % quirk.replace("_", " ")
        self.print(self._c(line1, "bold"))
        self.print(self.bar_line("Rapport", int(rapport or 0)))
        if memory:
            for ln in wrap_text(memory, min(42, self.width)):
                self.print(self._c(ln, "dim"))

    def stat_grid(self, pairs: Sequence[tuple], width: int = 10) -> None:
        for i in range(0, len(pairs), 2):
            left = self.bar_line(pairs[i][0], pairs[i][1], width)
            right = (
                self.bar_line(pairs[i + 1][0], pairs[i + 1][1], width)
                if i + 1 < len(pairs)
                else ""
            )
            if right:
                self.print(f"  {left}")
                self.print(f"  {right}")
            else:
                self.print(f"  {left}")

    def menu_table(self, rows: Sequence[tuple]) -> None:
        """Consistent compact menu rows with restrained semantic colour."""
        for row in rows:
            key, icon, name, desc = (list(row) + ["", "", ""])[:4]
            key = str(key); icon = str(icon or "").strip(); name = str(name); desc = str(desc or "")
            icon_txt = (icon + " ") if icon else ""
            plain_head = "  %s) %s%s" % (key, icon_txt, name)
            key_txt = self._c(key, "bold", "bcyan")
            name_txt = self._c(name, "bold")
            styled_head = "  %s) %s%s" % (key_txt, icon_txt, name_txt)
            if not desc:
                self.print(styled_head)
                continue
            dlow = desc.lower()
            if "1 week" in dlow or "half week" in dlow or "1/2 week" in dlow:
                dstyle = "byellow"
            elif "no time" in dlow:
                dstyle = "green"
            else:
                dstyle = "gray"
            if len(plain_head) + 2 + len(desc) <= self.width:
                self.print(styled_head + "  " + self._c(desc, dstyle))
                continue
            self.print(styled_head)
            indent = "     "
            for line in wrap_text(desc, max(12, self.width - len(indent))):
                self.print(indent + self._c(line, dstyle))


    def nav_footer(self, help_key: bool = False, home: bool = False) -> None:
        """One quiet navigation footer used by management screens."""
        parts = ["X Back"]
        if home:
            parts.append("0 Home")
        if help_key:
            parts.append("? Help")
        self.print("  " + "   ".join(parts), style="dim")

    def table(self, title: str, columns: Sequence[str], rows: Sequence[Sequence]) -> None:
        self.print(self._c(title, "bold", "bcyan"))
        widths = []
        for i, col in enumerate(columns):
            w = len(str(col))
            for r in rows:
                if i < len(r):
                    w = max(w, len(str(r[i])))
            widths.append(min(w, 18))
        head = "  ".join(str(c)[:widths[i]].ljust(widths[i]) for i, c in enumerate(columns))
        self.print(self._c(head, "dim"))
        self.print(self._c("-" * min(self.width, len(head)), "gray"))
        for r in rows:
            cells = []
            for i, x in enumerate(r):
                w = widths[i] if i < len(widths) else 10
                cells.append(str(x)[:w].ljust(w))
            self.print("  ".join(cells))

    def ask(self, prompt: str) -> str:
        shown = self._c(prompt, "cyan") if self.color else prompt
        try:
            from . import telemetry
            telemetry.prompt(shown)
        except Exception:
            pass
        value = input(shown)
        try:
            from . import telemetry
            telemetry.answer(value)
        except Exception:
            pass
        return value

    def pause(self, seconds: float = 0.6) -> None:
        time.sleep(0.15 if self.fast else seconds)

    def auto_pause(self, text: str = "") -> None:
        time.sleep(0.25 if self.fast else 0.6)

    def read_pause(self, text: str = "", extra: float = 0.0) -> None:
        """Legacy timed reading pause. Use ``continue_prompt`` for screens
        where the player must control when the text disappears.
        """
        n = len(text or "")
        seconds = 0.5 + (n / 28.0) + extra
        seconds = max(0.6, min(3.2, seconds))
        if self.fast:
            seconds = max(0.5, seconds * 0.75)
        time.sleep(seconds)

    def continue_prompt(self, label: str = "Press Enter to continue") -> None:
        """Player-controlled pacing for long/new information screens.

        Do not rely on ``stdin.isatty()`` here: iOS/Pythonista-style consoles
        can provide working ``input()`` while reporting a non-TTY stream.
        We attempt the prompt directly and only fall back to a tiny pause when
        stdin is genuinely unavailable (CI/headless subprocesses).
        """
        if os.environ.get("MMA_LEGEND_NONINTERACTIVE") == "1":
            self.pause(0.05)
            return
        try:
            self.ask("\n  %s > " % label)
        except (EOFError, OSError):
            self.pause(0.05)


def status_strip(console: GameConsole, fighter) -> None:
    """One short context line carried into frequently-used submenus."""
    booked = getattr(fighter, "booked_fight", None)
    next_bit = ""
    if isinstance(booked, dict) and booked.get("date_week"):
        left = max(0, int(booked.get("date_week") or 0) - int(getattr(fighter, "week", 0) or 0))
        next_bit = "  •  fight %sw" % left
    elif getattr(fighter, "competition_signup", None):
        next_bit = "  •  %s" % str(fighter.competition_signup)[:18]
    line = "W%s  $%s  EN %s  HP %s%s" % (
        int(getattr(fighter, "week", 1) or 1),
        format(int(getattr(fighter, "money", 0) or 0), ","),
        int(getattr(fighter, "energy", 0) or 0),
        int(getattr(fighter, "health", 0) or 0), next_bit)
    console.print("  " + line, style="dim")


def render_dashboard(console: GameConsole, fighter) -> None:
    """Weekly summary. Standard mode is informative; Compact keeps only decisions."""
    flag = getattr(fighter, "country_flag", "") or "🌍"
    is_pro = bool(getattr(fighter, "pro_debut", False))
    pr = list(getattr(fighter, "pro_record", [0, 0, 0]) or [0, 0, 0])
    am = list(getattr(fighter, "amateur_record", [0, 0, 0]) or [0, 0, 0])
    try:
        from . import identity as _id
        org = _id.display_org(fighter)
        rank = _id.rank_line(fighter)
    except Exception:
        org = getattr(fighter, "organization", None) or ("Free Agent" if is_pro else "Amateur")
        rank = ""
    try:
        from .nicknames import display_name
        public_name = display_name(fighter)
    except Exception:
        public_name = fighter.name

    record = ("Pro %s-%s-%s" % tuple(pr)) if is_pro else ("Amateur %s-%s-%s" % tuple(am))
    if is_pro and any(am):
        record += "   Amateur %s-%s-%s" % tuple(am)
    console.print("  " + console._c("%s %s" % (flag, public_name), "bold", "bcyan"))
    career_line = "%s   %s" % (record, org)
    for part in wrap_text(career_line, max(16, console.width - 2)):
        console.print("  " + part)
    informative_rank = bool(rank and (rank.startswith("#") or rank.startswith("C ") or rank.startswith("UFC #") or "roster" in rank.lower()))
    if informative_rank:
        for part in wrap_text(rank, max(16, console.width - 2)):
            console.print("  " + part, style="dim")

    walk = float(getattr(fighter, "walking_weight", getattr(fighter, "weight", 0)) or 0)
    _wc_short = {"Flyweight":"FLW", "Bantamweight":"BW", "Featherweight":"FW", "Lightweight":"LW", "Welterweight":"WW", "Middleweight":"MW", "Light Heavyweight":"LHW", "Heavyweight":"HW"}
    wc_short = _wc_short.get(getattr(fighter, "weight_class", "?"), getattr(fighter, "weight_class", "?"))
    console.print("  " + console._c("Energy %s" % int(getattr(fighter, "energy", 0) or 0), _bar_color(int(getattr(fighter, "energy", 0) or 0))) +
                  "   " + console._c("Health %s" % int(getattr(fighter, "health", 0) or 0), _bar_color(int(getattr(fighter, "health", 0) or 0))) +
                  "   $%s" % format(int(getattr(fighter, "money", 0) or 0), ","))
    if not bool(getattr(fighter, "ui_compact", False)):
        cond = "Weight %.1f kg   %s   Nutrition %s   Fame %s" % (walk, wc_short, int(getattr(fighter, "nutrition", 0) or 0), int(getattr(fighter, "fame", 0) or 0))
        for part in wrap_text(cond, max(16, console.width - 2)):
            console.print("  " + part, style="dim")

    next_lines = []
    booked = getattr(fighter, "booked_fight", None)
    if isinstance(booked, dict) and booked.get("date_week"):
        left = max(0, int(booked.get("date_week") or 0) - int(getattr(fighter, "week", 0) or 0))
        opp = booked.get("opponent")
        opp_name = getattr(opp, "name", "") if opp is not None and not isinstance(opp, dict) else ""
        if not opp_name:
            snap = booked.get("opponent_snap") or booked.get("opponent_snapshot")
            if isinstance(snap, dict):
                opp_name = str(snap.get("name") or "")
        event_name = booked.get("event_name") or booked.get("org") or "Fight"
        flags = []
        if booked.get("title"):
            flags.append("TITLE")
        if booked.get("short_notice"):
            flags.append("SHORT NOTICE")
        prefix = ((" ".join(flags) + "  ") if flags else "")
        next_lines.append("🥊 %s%s vs %s   %sw" % (prefix, event_name, opp_name or "TBA", left))
        if not bool(getattr(fighter, "ui_compact", False)):
            try:
                from . import cut as _cut
                prog = _cut.weight_campaign_summary(fighter)
                next_lines.append("Weight: %.1f kg   target %.1f kg   %s" % (prog["current"], prog["target"], prog.get("pace", "on track")))
            except Exception:
                pass
            try:
                from . import contracts as _contracts
                deal = _contracts.active(fighter)
                if deal:
                    left_fights = int(deal.get("fights_left", 0) or 0)
                    next_lines.append("Contract: %s   %s fight%s remaining" % (deal.get("org") or getattr(fighter, "organization", "Promotion"), left_fights, "" if left_fights == 1 else "s"))
                    clauses = list(deal.get("clauses") or [])
                    if not deal.get("exclusive", True):
                        clauses.append("non-exclusive")
                    labels = {"short_notice":"short-notice +25%", "title_escalator":"title step-up", "rematch_option":"rematch option", "non-exclusive":"non-exclusive"}
                    if clauses:
                        next_lines.append("Terms: " + ", ".join(labels.get(x, str(x).replace("_", " ")) for x in clauses))
            except Exception:
                pass
    elif getattr(fighter, "competition_signup", None):
        next_lines.append("🏅 %s" % fighter.competition_signup)
    elif getattr(fighter, "intl_camp", None) and int(getattr(fighter, "intl_camp_weeks", 0) or 0) > 0:
        next_lines.append("Abroad: international camp   %sw left" % int(fighter.intl_camp_weeks))

    if int(getattr(fighter, "suspension_weeks", 0) or 0) > 0:
        next_lines.append("Suspended   %sw" % int(fighter.suspension_weeks))
    elif int(getattr(fighter, "fight_cooldown", 0) or 0) > 0:
        next_lines.append("Fight recovery   %sw" % int(fighter.fight_cooldown))

    limit = 1 if bool(getattr(fighter, "ui_compact", False)) else 4
    for line in next_lines[:limit]:
        for part in wrap_text(line, max(16, console.width - 2)):
            console.print("  " + console._c(part, "byellow"))
    try:
        from .notify import render as _nr
        _nr(console, fighter)
    except (TypeError, ValueError, AttributeError, ImportError):
        pass
    console.print()

def render_fighter_stats(console: GameConsole, fighter, detailed: bool = False) -> None:
    from . import constants as C
    groups = [
        ("Striking", ("striking", "kicks", "ko_power", "striking_def", "distance_management")),
        ("Grappling", ("grappling", "submissions", "ground_control", "takedown_def", "submission_def")),
        ("Physical", ("cardio", "strength", "speed", "durability")),
        ("Fight IQ", ("fight_iq",)),
    ]
    for title, keys in groups:
        console.section(title)
        for key in keys:
            if hasattr(fighter, key):
                console.print("  " + console.bar_line(C.SKILL_LABELS.get(key, key), getattr(fighter, key)))
    if not detailed:
        return
    console.section("Mental & Career")
    console.stat_grid([
        ("Discipline", fighter.discipline), ("Mental Tough", fighter.mental_toughness),
        ("Happiness", fighter.happiness), ("Reputation", fighter.reputation),
        ("Legacy", fighter.legacy_score), ("Press Hype", fighter.press_hype),
    ])
    console.section("Techniques")
    fighter.sync_techniques()
    if fighter.technique_levels:
        for tech, level in sorted(fighter.technique_levels.items(), key=lambda x: (-x[1], x[0])):
            console.print("  %-24s Lv%s" % (tech[:24], level))
    else:
        console.print("  None yet")
