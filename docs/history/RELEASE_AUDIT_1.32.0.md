# MMA Legend 1.32.0 — Part 2 Release Audit

## Scope
Part 2 of the playtest-driven overhaul, built directly on validated v1.31.0 Part 1: side-job/career-life depth, timeline and event-card presentation, UI pacing, contextual event cleanup, camp/fight-plan feedback, persistence repair and distribution cleanup.

## Implemented
- Ten-job side-employment system with pay, fatigue, risk, prerequisites, slow raises, shift history and contextual effects.
- Persistent `Fighter` fields for international-camp metadata, connections, side-job progression, timeline, notifications/ledger, injury history and mileage. This fixes old dynamic attributes being dropped by `from_dict()`.
- Amateur/pro timeline split with dated fight ledger, sport identity, developing record, performance rating and available strike/takedown/knockdown/control/submission stats.
- Persistent promotion event identities: numbered cards and Fight Night series, with event name/type/number saved into scheduled and completed card state.
- Larger card hierarchy: main event, co-main, main-card and prelim slots (up to 9 bouts at major promotions, 7 elsewhere).
- Player pro fight history records the actual event identity instead of only the promotion label.
- Choice events resolve without an immediate redundant Enter prompt; information-only events still pause. Spent weeks have one explicit week-complete/begin-next-week boundary.
- Narrow contradiction guards for impossible partner, renewal, title-defense and overseas-camp event text.
- Fight-plan selection shows expected behavioral effects; active international camp view shows location/focus/teachable techniques and home-system locks.
- Stabilized a legacy randomized test fixture that accidentally generated cross-division amateur opponents while expecting same-division matchmaking to pass.

## Validation performed
- `python3 -m compileall -q mma_legend` — PASS.
- `python3 -m mma_legend.diagnostics` — ALL SYSTEMS OK, v1.32.0; 58 countries, 194 authored opponents, 42 combat moments, 511 events.
- `python3 -m mma_legend.tests_132` — all 7 Part-2 gates PASS.
- Historical suites through v1.30 release gates were exercised; the 1.25–1.30 release suites remain green.
- `tests_192`, `tests_193`, `tests_194` — PASS, including the 2,400-fight engine-fairness suite.
- Legacy `tests_12` was rerun repeatedly after stabilizing its randomized weight-class fixture — PASS.
- All three supplied v1.30 playtester saves load successfully under v1.32 with ~1,532-fighter worlds; career-life fields are present and scheduled cards migrate to named event series.
- Reduced deterministic long-world audit: 2 years, 300 amateurs + 240 pros. Result: 12 active promotions, 208 cards / 741 bouts, 0 duplicate-booking weeks, 0 invalid title slots, 560 unique matchups, lifetime maximum 3 meetings.

## Save compatibility
Save format remains JSON v17. New fields are optional/defaulted; existing v1.30/v1.31 saves migrate without requiring a schema bump. Event-series counters are stored in world state and derived for older unnamed cards.

## Packaging
The release ZIP excludes runtime saves, playtest traces/bundles, debug logs, caches and compiled bytecode. Historical audits/handoffs are kept under `docs/` rather than cluttering the runnable root.
