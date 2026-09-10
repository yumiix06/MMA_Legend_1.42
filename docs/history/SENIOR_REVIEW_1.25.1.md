# SENIOR REVIEW — MMA Legend 1.25.1

## Decision

The v1.25.0 junior handoff was **not accepted unchanged**. It contained two
release-blocking promotion-state integrations: a released contract could be
recreated automatically, and a DWCS/early-UFC player could receive an invalid
UFC rank (including P4P). Those faults are fixed and regression-tested.

With those corrections, v1.25.1 is approved as the new stable baseline.

## What was accepted from 1.25.0

- Real three-strategy weight campaigns, nutrition-driven mass change and one
  canonical weigh-in/cage-weight result.
- One applied weekly economy ledger, explicit debt repayment and single
  overdraft-to-debt conversion.
- 36 contextual events, lower event hunger, repeat-category damping and
  stage-aware effect limits.
- Player-controlled long-screen pacing, lifestyle-menu cleanup and useful
  supplement sponsorship.
- UFC title eligibility based on promotion-specific résumé and live form.

## Senior corrections

- Free agency now survives weekly sync and load.
- Corrupt-exclusive recovery no longer mistakes `{}` for a damaged contract.
- DWCS is excluded from UFC ranking experience.
- The three-bout UFC gate is enforced on divisional, promotion and P4P boards,
  with stale rank state cleared before rebuild.
- Supplement sponsor utility uses explicit content metadata.

## Release checks

- All dynamically discovered regression modules: pass.
- `tests_125`: pass (11 checks).
- `tests_1251`: pass (4 senior regressions).
- Standalone `tests_194`: pass (2,400 fairness/viability fights).
- Diagnostics: 487 events, save/load, booking, people and combat pass.
- Python byte-compilation: pass.
- Balance lab and 60-career headless batch: no invariant violations.
- Event/economy stress probes and phone-width render audit: pass.
- Clean archive extraction and rerun: pass.

## Known non-blocking follow-up

The simplified headless career probe remains much harder than real controlled
matchups because its progression and opponent assumptions are intentionally
crude. Do not add a global player combat advantage to improve that number.
Debt interest is also intentionally severe; tune it only after collecting
complete purse, job, sponsor and expense telemetry from real careers.
