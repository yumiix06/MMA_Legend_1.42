# MMA Legend 1.27.0 — Lead Developer Release Audit

## Decision

Approved as the new stable baseline. Preserve `MMA_Legend_1.26.0.zip` as the
rollback release. The user-supplied saves and playtest traces were diagnostic
inputs only and are excluded from this package.

## Delivered

- Seven isolated amateur sport careers with rules, records, weight labels,
  experience, championship medals and no MMA-record leakage.
- New Judo and Combat Sambo rulesets.
- Earned BJJ stripes/belts and Judo belts with persistent grade points, mat
  weeks, fees and bounded combat relevance.
- One Gym & Team hub under Coach; the duplicate Lifestyle gym route is gone.
- Central fame/media logic, rebalanced amateur recognition, contextual press
  and interview eligibility, plus 144 unlockable nicknames.
- Persistent cards for 12 promotions, real event dates/locations, scheduled NPC
  resolution, card display/history, withdrawals, replacements, short notice,
  no double booking and repaired title validity.
- UFC title introductions: challenger first, champion second.
- 24 additional validated context events, bringing the database to 511.
- Save schema v13 for the new sport/belt/identity/calendar state.

## Defects caught during release gating

1. `engine/scoring.py` was found truncated mid-constructor. It was restored
   from the untouched v1.26 ZIP before any release tests were accepted.
2. The first calendar stress run found future title flags that became stale
   after a champion changed or retired. Scheduled title validation now removes
   invalid flags. The repeated stress run recorded zero invalid title slots.
3. Old regression assertions hard-coded the previous 487-event total and the
   old Lifestyle gym route. They now verify the intended extensible event total
   and single Gym & Team route behavior.

## Evidence

- `python3 -m mma_legend.tests`: all 32 modules pass, `FAILED MODULES 0`.
- `python3 -m mma_legend.diagnostics`: `RESULT: ALL SYSTEMS OK`.
- `python3 -m compileall -q mma_legend`: pass.
- Existing strict fairness suite: 2,400 clone fights; 50/50/49/51 player-slot
  win rates across Boxing/Wrestling/BJJ/Muay Thai; wrestler-vs-striker 57%.
- Balance lab (~300/scenario): equal amateur 54%, pro 51%, elite 45%.
- 3,600 organization-week calendar stress: all 12 promotions active, zero open
  double bookings, zero invalid title slots.
- Event DSL: zero issues across 511 events; existing phone rendering gate maxes
  at 44 columns.
- Supplied career save loaded read-only at week 78 with its 4-4 MMA ledger
  intact; all v13 fields defaulted correctly.

## Next playtest targets

- Whether side-sport medals and belt pacing feel earned over a full amateur run.
- Whether card frequency produces enough rematches/rivalries without repetition.
- Player response to replacement/cancellation frequency and short-notice pay.
- Fame growth across 8-12 regional pro fights and the first UFC title path.
