# MMA Legend 1.26.0 — lead developer release audit

## Decision

**Approved as the new stable baseline.** This release was built from the
senior-approved 1.25.1 archive. The untouched 1.25.1 ZIP remains the rollback
point. Diagnostic player saves were not modified or packaged.

## What changed

- Added persistent reach/stance and real Striking Defense, Submission Defense
  and Distance Management skills across generation, training, saves and UI.
- Reclassified broad combat concepts out of the technique pool, added a
  one-time save migration and gave all 117 playable technique rows structured
  combat metadata.
- Implemented four standing range bands, preferred-range tactics, active
  movement/guard/counter defence and bounded counter windows. Reach controls
  distance/accuracy only and never damage.
- Expanded the ground graph with open guard, front headlock, north-south and
  leg entanglement, including connected setups and position-specific finishes.
- Enforced separate legal actions for MMA, grappling, boxing, kickboxing and
  wrestling in every selection/resolution path.

## Defects caught during integration

1. Seeded combat results changed across Python processes because weighted AI
   choices inherited randomized set order. Legal actions are sorted now.
2. The equal balance fixture did not equalize the new reach and stance fields.
   It now does, so fairness results measure equal fighters again.
3. A historical stochastic cut test inherited random state from preceding
   suites. It now owns and restores a deterministic local seed.

## Release gates

- `python3 -m mma_legend.tests` → all 31 discovered modules pass,
  `FAILED MODULES 0`.
- `python3 -m mma_legend.tests_126` → all reconstruction checks pass.
- `python3 -m mma_legend.tests_194` → 2,400 strict clone fights: Boxing 50%,
  Wrestling 50%, BJJ 49%, Muay Thai 51%; wrestler vs striker 57%.
- `python3 -m mma_legend.diagnostics` → version 1.26.0, 487 events,
  `RESULT: ALL SYSTEMS OK`.
- `python3 -m mma_legend.balance` → pro equal 47%, elite equal 52%; varied NPC
  damage calibration remains within the established decision/finish gate.
- `python3 -m compileall -q mma_legend` → pass.

## Known balance note

The equal basic-kit amateur/pro fixture remains more decision-heavy than the
varied-style NPC population because it deliberately gives both fighters a
narrow starting move set. Elite and varied-style samples produce materially
more finishes. No finish constant was inflated merely to make that synthetic
fixture resemble a full career roster.

## Next playtest focus

Use a fresh 1.26 career and watch whether preferred range is understandable on
phone, whether defence training competes fairly with offense, whether long
fighters can be crowded without feeling helpless, and whether the new ground
positions occur often enough without slowing decisions. Export the next
playtest bundle after several MMA bouts and at least one side-sport match.
