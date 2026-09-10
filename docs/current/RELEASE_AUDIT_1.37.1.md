# MMA Legend 1.37.1 Release Audit

## Scope
Focused UI cleanup only. No simulation/balance redesign.

## Changes
- Removed Train and Amateur emojis from the weekly menu.
- Replaced the dense Training focus grid with one aligned vertical option per line.
- Replaced inline intensity choices with aligned vertical Light / Normal / Heavy rows.
- Kept Repeat Last Session and Back visually separate from training focus.

## Correctness
- Cancelling Training at focus selection returns False, consumes no energy and does not spend a week.
- Cancelling at intensity selection has the same no-time behavior.
- Existing training costs, gains and injury risks are unchanged.
- Save version remains JSON v17.

## Validation
- `tests/tests_1371.py` PASS.
- `tests/tests_137.py` PASS.
- `tests/tests_1361.py` PASS with updated visual expectation.
- `tests/tests_136.py` PASS.
- `tests/tests_130_release.py` PASS.
- `python -m mma_legend.diagnostics`: ALL SYSTEMS OK.
