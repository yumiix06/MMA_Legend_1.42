# MMA Legend 1.33.0 — Maintenance / Cleanup Release Audit

## Scope
Reorganize and clean the full 1.32.0 game without destabilizing gameplay, and fix concrete bugs encountered during the refactor.

## New layout
- `mma_legend/` — player/runtime package only.
- `tests/` — versioned regression suites and unified runner.
- `tools/` — save repair, batch-career simulation, long-world audit and release builder.
- `docs/current/` — current architecture, system map, changelog, version history and this release audit.
- `docs/history/` — historical release/playtest audits and senior handoffs.
- Root — only `START.py`, `main.py`, `README.md` plus the organized directories.

## Bugs fixed
1. The old aggregate test runner silently skipped `tests_132` because it looked only for `main()` while that suite exposed `run()`. The new runner accepts either and raises when a suite has no callable entry point.
2. The old save-repair write branch referenced a record module alias that existed only when the file was executed as `__main__`; imported write-mode calls could fail with `NameError`.
3. `record.is_mma()` treated explicit Combat Sambo, Boxing, Kickboxing, Wrestling and Judo history rows as MMA. Explicit sport/ruleset metadata now wins; only legacy untagged rows use event-name inference.
4. Launcher discovery previously scanned sibling `MMA_Legend*` directories. If launch files were misplaced or multiple builds coexisted, it could select a different version. The launcher now boots only its colocated package and fails clearly if the folder is incomplete.

## Packaging cleanup
- Removed redundant `run.py`.
- Release builder excludes `__pycache__`, `.pyc/.pyo`, saves, debug logs, playtest traces/snapshots and other transient artifacts regardless of where tests generated them.
- Runtime package no longer contains 36 historical/versioned regression files.
- Removed orphaned `mma_legend/rng.py`; live systems already use their own injected/global RNG paths and no module imported this stub.
- Save format remains JSON v17.

## Validation
- Runtime/test/tool compile pass.
- `python3 -m mma_legend.diagnostics` — all systems OK; 58 countries, 194 authored opponents, 42 combat moments, 511 events.
- `python3 -m tests.tests_132` — all Part-2 gates pass after relocation.
- `python3 -m tests.tests_133` — all maintenance/layout/bugfix gates pass.
- Historical regression modules through 1.19.3 pass from the new package layout.
- The unchanged 2,400-fight fairness suite is execution-heavy; the combat engine itself was not modified by 1.33 and retains the prior 1.32 fairness validation. Reduced clone/style probes are run for this release.
- Supplied v1.30 playtester saves remain loadable under JSON v17. Their Combat Sambo history no longer causes a false MMA-ledger mismatch in the save-audit tool.

## Release decision
1.33.0 is the new clean maintenance baseline for continued development. 1.32.0 remains the gameplay rollback point.
