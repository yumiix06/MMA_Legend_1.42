# MMA Legend 1.38.0 Release Audit

## Scope
Living NPC careers, promotion personality, matchmaking politics and richer player career opportunities. The frozen v1.37.1 UI/navigation architecture is intentionally unchanged.

## New systems
- Persistent NPC career personalities and goals (`career_personality`, `career_goal`, goal-change history).
- Goal-aware weekly NPC intent, card matchmaking and roster-transfer preference.
- Twelve distinct promotion profiles controlling merit, star power, prospect protection, activity, toughness and regional emphasis.
- Promotion-interest ranking for player inboxes using sporting résumé, activity, marketability, regional fit and existing promoter/matchmaker rapport.
- Career-opportunity metadata on offers: showcase, rebuild, step-up, contender test, short-notice jump, home-market feature and championship opportunity.
- Bounded opportunity rewards after wins so higher-risk career choices can accelerate reputation/fame/legacy without replacing normal progression.
- World audit observability for career-goal/personality distribution and career-goal changes.

## Bug fixed during implementation
The post-offer decision screen advertised `X) Back out`, but X did not have a branch and could keep the player trapped in the decision loop. X/B/0 now leave cleanly; invalid input is explained.

## Compatibility
- Save version: 17 (unchanged).
- New NPC fields are declared on `Fighter`, so old saves upgrade through normal defaults and then populate career goals during world simulation.
- v1.37.1 weekly navigation/training UI remains unchanged.

## Balance comparison
A deterministic three-year reduced-world audit was run against the same seed on v1.37.1 and v1.38.0. v1.38 preserved all promotion populations, title cadence and the lifetime trilogy ceiling. 90th-percentile pro inactivity improved from 29 weeks to 26 weeks (median 12 -> 13); no duplicate booking weeks or invalid title slots occurred.

## Validation
- `python -m mma_legend.diagnostics`: ALL SYSTEMS OK.
- `tests_138`: PASS.
- v1.37.1 UI regression: PASS.
- Full v1.30 release milestone suite: PASS.
- v1.32/v1.33/v1.36/v1.37 maintenance/UI suites: PASS.
- Three-year reduced world audit: 0 duplicate-booking weeks, 0 invalid title slots, maximum lifetime pairing 3, all 12 promotions populated.
