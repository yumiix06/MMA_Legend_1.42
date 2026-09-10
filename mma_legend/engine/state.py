"""Round-side stats used by the 0.8.1 scorer."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SideStats:
    strikes_landed: int = 0
    strikes_attempted: int = 0
    head_landed: int = 0
    body_landed: int = 0
    leg_landed: int = 0
    takedowns_landed: int = 0
    knockdowns: int = 0
    control: int = 0
