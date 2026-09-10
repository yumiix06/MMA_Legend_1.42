# MMA Legend 1.34.0 Part 1 — Release Audit

Scope: UI/navigation/QoL only; simulation behavior intentionally conservative.

## Implemented
- Compact weekly dashboard; no permanent 15-skill wall.
- Domain navigation: Career / Team / Life plus weekly Train / Rest / Fight-Inbox.
- Legacy hotkeys remain aliases.
- Action time/energy/context tags.
- Persistent alert inbox.
- Week-end state delta report.
- Repeat-last training and safe cancellation.
- Mini status strip in high-traffic hubs.

## Bugs fixed during the pass
- Invalid training focus could deduct energy while producing no session; now cancelled safely.
- The v1.33 historical regression suite hard-coded the exact old game version; it now verifies 1.33-or-newer while retaining its maintenance checks.
- Dead code after `_coach_hub()` return removed.
- Action-cost labels were initially written with square brackets, which the legacy markup cleaner strips; labels now use phone-safe parentheses and rendered-output regression coverage.

## Compatibility
- Save version remains 17.
- New UI fields have defaults and serialize through the existing Fighter dataclass.

## Validation
- `python -m compileall mma_legend tests`
- `python -m tests.tests_134`
- v1.33 maintenance suite
- v1.32 Part-2 suite
- v1.30 release milestone suite
- `python -m mma_legend --selfcheck`
- release ZIP is re-extracted and smoke-tested before delivery.
