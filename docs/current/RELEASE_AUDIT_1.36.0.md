# MMA Legend 1.36.0 Release Audit

## Scope
UI recovery and navigation-safety release built directly on 1.35.0 after playtest feedback. No save-schema change; JSON v17 remains authoritative.

## Fixed regressions / bugs
- Team -> Back could spend a week because the dispatcher compared full serialized Fighter state and `sync_techniques()` could normalize metadata. Fixed with explicit Team action completion.
- People -> Back could be charged as a half-week.
- School -> Back could fall through to Skip Class.
- Rehab -> Back or simply opening Rehab with no active injury could consume a week.
- Coach advice could be repeatedly farmed from a NO-TIME screen for Fight IQ/rapport.
- Weekly manager/news logic could re-run after returning from browse-only screens in the same calendar week.

## UX changes
- Restored flat direct weekly actions and a separate NO-TIME career-information section.
- Simplified title menu and replaced guided-start onboarding with a three-page How to Play guide.
- Simplified weekly dashboard, Team, Life and Nutrition screens.
- Added restrained semantic colour and a small symbol/emoji vocabulary; iOS consoles keep ANSI colour when supported.
- Calendar and Alerts remain direct browse-only shortcuts.

## Validation
- `python -m compileall -q mma_legend tests tools`: pass.
- `python -m mma_legend.diagnostics`: ALL SYSTEMS OK.
- `tests_122`, `tests_125`, `tests_127`, `tests_128`, `tests_129`, `tests_130_release`, `tests_132`, `tests_133`, `tests_134`, `tests_135`, `tests_136`: pass.
- `tests_194` engine fairness: pass.
- Three supplied v1.30 playtester saves load successfully and retain the full ~1,532-fighter world.

## Rollback
1.35.0 remains the previous rollback point.
