# MMA Legend 1.29.0 — lead-developer release audit

## Decision

**Approved as the new stable baseline**, replacing 1.28.0. Save schema is JSON
v15. Keep the clean 1.28.0 ZIP as the rollback point.

Phase 1 was re-audited before Phase 2 integration. The old build had separate
sport records, but its menus, shortcuts and championship timing did not fully
respect the selected competition sport. Those gaps are fixed and covered by
regression tests.

## Implemented scope

- The selected amateur sport is now an exclusive competition focus. MMA menus,
  booking and turn-pro prompts are hidden during a side-sport career; side-
  sport entries are hidden during MMA focus.
- Side-sport championships are registered on an absolute career calendar and
  resolve only when their event week arrives. Each sport receives two Regional
  Opens, two Nationals, two Europeans and one World Championships per year.
- Boxing, Wrestling and Judo receive a four-year Olympic calendar with
  sport-specific qualification.
- BJJ / No-Gi, Boxing, Kickboxing, Wrestling, Judo and Combat Sambo bouts all
  support Play, Live Sim and Instant modes. A tournament uses one selected mode
  through its entire bracket.
- Side-sport history stores the date, opponent, event, sport, ruleset,
  competition level, fight mode and match statistics. Recent results are
  visible in the active sport hub, its calendar and Career Statistics.
- Save v15 persists the registered sport, competition level and absolute due
  week while safely defaulting older registrations to MMA.

## Defects found and fixed

1. **Competition focus was cosmetic.** The Amateur hub and weekly Fight
   shortcut could still expose or book MMA while another sport was selected.
   Both now route through the active sport.
2. **Side championships happened immediately.** Menu selection launched the
   bracket without a real future date. Registration now binds the event to its
   sport and absolute career week, survives saving, and resolves on or after
   that date.
3. **Calendars leaked across sports.** MMA displayed legacy ADCC entries and
   side-sport focus still displayed MMA competition. New entries are exclusive
   to the selected sport; legacy ADCC registrations remain resolvable.
4. **Side fights lacked a simulation choice.** Every non-MMA ruleset now offers
   Play, Live Sim and Instant, including championship brackets.
5. **Side-sport history was incomplete.** Records existed, but did not provide
   a useful dated career ledger. Event, opponent, week, mode and statistics are
   now retained and surfaced.
6. **National-team assignment could silently fail.** Championship qualification
   refreshed the sport-state dictionary after local references were captured.
   A National medal could therefore persist without its team selection. The
   references are now captured after normalization and the behavior is tested.
7. **Year-wrap registration was fragile.** Absolute due weeks now supplement
   the season-week value, preventing a registered event from being lost after
   calendar rollover or delayed save loading.

## Release gates

- `python3 -m compileall -q mma_legend`
- `python3 -m mma_legend.tests` — every discovered historical/current module
  passes with `FAILED MODULES 0`, including 2,400-fight fairness at Boxing 50 /
  Wrestling 50 / BJJ 49 / Muay Thai 51.
- `python3 -m mma_legend.tests_129` — exclusive focus, all-sport calendar
  cadence, Olympics, registration, scheduled resolution, modes, history and
  save-v15 persistence pass.
- Six real, non-mocked Instant bouts completed successfully under BJJ / No-Gi,
  Boxing, Kickboxing, Wrestling, Judo and Combat Sambo rulesets.
- `python3 -m mma_legend.diagnostics` — v1.29.0, 58 countries, 194 authored
  opponents, 42 combat moments and 511 events; `ALL SYSTEMS OK`.

## Deterministic five-year world audit

Seed 12801, 840 amateur + 560 professional starting world, 260 simulated weeks:

- 835 active amateurs and 620 active professionals; all seven sports remain
  populated, including 204 active lifelong side-sport athletes.
- All 12 organizations remain populated.
- Professional inactivity: median 15 weeks, p90 39, p99 54 and maximum 69.
- 495 title fights across all 96 organization/division combinations.
- Zero duplicate booking weeks, invalid title slots or UFC champion/belt
  mismatches.
- 669 original NPCs changed recent form and 645 changed streak state, proving
  scheduled fight results continue to feed career logic.

## Packaging boundary

Player saves, autosaves, playtest traces, debug logs, bytecode caches and prior
ZIPs are excluded. Supplied saves remain read-only balancing/debug references;
this release does not promise permanent compatibility with them.
