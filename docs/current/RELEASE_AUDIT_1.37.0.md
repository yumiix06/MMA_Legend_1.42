# MMA Legend 1.37.0 Release Audit

## Scope
UI freeze/polish pass on v1.36.1. No combat, world, economy or career-progression redesign. Save format remains v17.

## Player-facing changes
- Flat weekly navigation retained as the committed direction.
- Restrained weekly emoji set; deep management headers use plain text.
- Core choice prompts normalized to the same `>` style.
- Compact Dashboard now changes output density.
- Per-career Color preference added alongside Compact Dashboard, Week Report and Fight View.
- Fighter sheet reorganized into Career, Condition, Belts, Striking, Grappling, Physical, Fight IQ, Amateur Sports and Best Techniques.
- BJJ/Judo show progress toward the next belt.
- Fight-week dashboard keeps title/short-notice, weight target, contract fights remaining and important clauses while using shorter lines.
- Main-menu/tutorial labels updated to the final navigation.

## Correctness / compatibility
- Team and Life browse-only exits remain no-time actions.
- `--no-color` still overrides saved career color.
- Save v17 remains backward compatible; all three supplied v1.30 playtester saves load with 1,532 world fighters.

## Validation
- `tests.tests_137`: PASS
- `tests.tests_1361`: PASS
- `tests.tests_136`: PASS
- `tests.tests_135`: PASS
- `tests.tests_134`: PASS
- `tests.tests_133`: PASS
- `tests.tests_132`: PASS
- `tests.tests_130_release`: PASS
- `tests.tests_122` phone-width/dashboard checks: PASS
- `python -m mma_legend.diagnostics`: ALL SYSTEMS OK
- supplied playtester save load checks: PASS
