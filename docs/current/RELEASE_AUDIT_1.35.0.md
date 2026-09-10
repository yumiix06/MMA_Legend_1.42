# MMA Legend 1.35.0 — UI/QoL Part 2 Release Audit

## Scope
Second half of the two-part UI/QoL milestone on top of v1.34.0 Part 1. No save-version bump and no replacement of the canonical combat/world systems.

## Implemented
- Continue-first main menu and quieter title screen.
- Topic-based tutorial plus optional contextual guided start.
- Career overview, fighter sheet and unified calendar.
- Fight Prep hub for booked bouts.
- Matchup-aware gameplan recommendation and tactical card.
- Saved gameplan/watch/UI preferences.
- Timeline overview with filters/paging.
- Consolidated post-fight summary.

## Validation
- `python -m mma_legend.diagnostics`: ALL SYSTEMS OK on v1.35.0.
- `tests_135`: PASS.
- `tests_134`: PASS.
- `tests_133`: PASS.
- `tests_132`: PASS after preserving the quick amateur/pro timeline overview expected by older UI consumers.
- `tests_130_release`: PASS (all 19 release milestones).
- `tests_127`, `tests_128`, `tests_129`: PASS.
- `tests_193`: PASS.
- `tests_194`: PASS, including wrestler-vs-striker fairness at 49% in that seeded suite.
- All three supplied v1.30 playtester saves load under v1.35 with the full 1,532-fighter worlds and default the new UI fields safely.

## Compatibility
Save format remains JSON v17. Existing saves default to Standard dashboard, Week Report ON, guided tutorial OFF and Balanced preferred gameplan. New careers are offered guided start explicitly.
