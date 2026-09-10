# Release Audit — MMA Legend 1.42.0

## Scope
Full release combining v1.40 Performance & Education, v1.41 Promotion Rankings & Gym Life, and v1.42 Taekwondo & Kicking.

## Playtest-driven fixes
- The supplied v1.39 reference save is an unsigned 17-year-old amateur and exposed that only UFC boards were obvious in the rankings UI; v1.41+ exposes every promotion board directly.
- The reference save has an active Riverside Gi BJJ membership with white belt/stripes; specialist membership now develops automatically instead of requiring repeated manual menu actions.
- Under-18 debt in the old reference state is no longer allowed in fresh v1.40+ careers.

## v1.42 content and mechanics
- Taekwondo is an Olympic side sport with dedicated kyorugi rules, seven capped weight categories plus open class, round points and legal kicking actions.
- Three Taekwondo dojangs, automatic belt development and nine named Taekwondo techniques.
- New kicking actions and setups work in MMA/kickboxing only when rules/knowledge allow them.
- 18 new Taekwondo/kicking events; 565 total authored events.
- Taekwondo background/NPC generation/gameplan support.

## Validation
- `python3 -m mma_legend.diagnostics`: ALL SYSTEMS OK.
- v1.40, v1.41 and v1.42 dedicated regression suites pass.
- v1.30 release milestone suite passes.
- Historical combat legality, damage/injury, phone-width, sport/calendar, economy/contract and engine integration suites pass in targeted runs.
- Seeded 400-fight mixed-style pro MMA audit: ~50% decisions / ~50% finishes after tightening unlearned advanced-kick usage.
- Event pack validation: zero errors.

## Release hygiene
The release builder excludes runtime saves, playtest bundles/traces, debug logs, caches and bytecode. The finished archive is verified from a fresh extraction.
