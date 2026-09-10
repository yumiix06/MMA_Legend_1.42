"""v1.37.1 focused menu/training layout regression checks."""
import contextlib
import io

from mma_legend import app, constants, career
from mma_legend.models import Fighter


def _f():
    return Fighter.new_player(
        "UI Tester", "B", {"name": "Bulgaria", "flag": "BG", "bonus": {}},
        "Judo", height=180, weight=77,
    )


class CaptureConsole:
    def __init__(self, answers):
        self.answers = list(answers)
        self.out = []
        self.width = 44
        self.color = False

    def ask(self, prompt=""):
        self.out.append(str(prompt))
        return self.answers.pop(0) if self.answers else "X"

    def print(self, msg="", style=None):
        self.out.append(str(msg))

    def header(self, *args, **kwargs):
        self.out.append(" ".join(map(str, args)))

    def section(self, *args, **kwargs):
        self.out.append(" ".join(map(str, args)))

    def warn(self, msg): self.out.append(str(msg))
    def info(self, msg): self.out.append(str(msg))
    def good(self, msg): self.out.append(str(msg))
    def gold(self, msg): self.out.append(str(msg))
    def pause(self, *args, **kwargs): pass
    def continue_prompt(self, *args, **kwargs): pass


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1, 37, 1)

    # Train and Amateur are deliberately plain text in the weekly menu.
    f = _f()
    rows = {row[0]: row for row in app._actions_for(f)}
    assert rows["A"][1] == ""
    assert rows["D"][1] == ""

    # Training focus is a true vertical list: one option per rendered line.
    c = CaptureConsole(["X"])
    before_energy = f.energy
    assert career.do_training(c, f) is False
    assert f.energy == before_energy
    expected = [
        "A) Striking", "B) Kicks", "C) Grappling", "D) Submissions",
        "E) Takedown Defense", "F) Ground Control", "G) Cardio", "H) Strength",
        "I) Speed", "J) Fight IQ", "K) Striking Defense", "L) Submission Defense",
        "M) Distance Management", "N) Balanced", "R) Repeat last session", "X) Back",
    ]
    text = "\n".join(c.out)
    for item in expected:
        assert item in text, item
    option_lines = [line.strip() for line in c.out if line.strip()[:2] in {f"{x})" for x in "ABCDEFGHIJKLMNRX"}]
    assert len(option_lines) >= 16
    assert all(sum(marker in line for marker in expected) <= 1 for line in option_lines)

    # Intensity choices are also vertical and backing out spends nothing.
    c2 = CaptureConsole(["A", "X"])
    before_energy = f.energy
    assert career.do_training(c2, f) is False
    assert f.energy == before_energy
    text2 = "\n".join(c2.out)
    assert "A) Light    10 EN    2% injury risk" in text2
    assert "B) Normal   20 EN    5% injury risk" in text2
    assert "C) Heavy    30 EN   12% injury risk" in text2

    print("v1.37.1 training/menu cleanup checks: PASS")
    return True


if __name__ == "__main__":
    run()
