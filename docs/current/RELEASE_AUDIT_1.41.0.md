# Release Audit — MMA Legend 1.41.0

## Scope
Full release combining v1.40 Performance & Education with v1.41 promotion-ranking visibility, specialist-gym persistence, automatic belt/technique development, new contextual content, QoL and bug fixes.

## Playtest-driven findings
- Latest v1.39 reference save was an unsigned 17-year-old amateur while the world still contained persistent named-promotion ranks; rankings UI therefore needed a world browser rather than only current-org/UFC views.
- The same save had an active Riverside Gi BJJ membership, white belt/stripes and mat progress, providing a concrete fixture for persistent gym progression.
- v1.39 reference state also contained under-18 debt; v1.40+ now hard-clamps minors to zero debt.

## Validation gates
- `python3 -m mma_legend.diagnostics`: ALL SYSTEMS OK.
- Event pack validation: zero errors; 547 authored events, 36 new in v1.41.
- v1.30 release milestone suite passes.
- v1.32 through v1.41 modern regression suites pass.
- Historical economy/education/save compatibility-contract tests updated for intentional v1.40+ rules and pass.
- v1.41 tests cover promotion-board browsing, passive BJJ growth, automatic belts, international-camp exclusion, kickboxing technique legality, gym-leaving persistence, event gating and save v19.

## Release hygiene
ZIP builder excludes runtime saves, playtest bundles/traces, debug logs, caches and bytecode. Final archive is verified after fresh extraction.
