# MMA Legend 1.30.0 — stable release audit

## Decision

**Approved as the stable inspection baseline**, replacing 1.29.0. This does not mean the game is close to beta; it is a mid-development milestone intended for the next deep design review. Save schema is JSON v17.

## Scope completed

### Phase 1 — long-term world simulation
- Real promotion matchmaking roles: prospects/showcases, gatekeepers, contenders, title eliminators, rebuilds, activity fights, intentional rematches and title fights.
- Champions are not booked into ordinary non-title fights. Severe title inactivity can create a second championship slot.
- Hard lifetime trilogy ceiling, independent of the pruned recent-rematch cache.
- Fresh-challenger roster repair prevents saturated champions/divisions from freezing.
- Lifetime championship counters preserve title wins/defenses after the bounded recent lineage list reaches its cap.
- Small countries skip artificial Regionals; continental championships run once per year and route to European, Pan-American or Asian competition. Player and NPC amateur worlds share the same calendar model.

### Phase 2 — contracts, managers and preparation
- Negotiable purse economics, fight count, term, exclusivity and clauses.
- Manager negotiation/scouting/career-management competencies combine with personality and relationship.
- Persistent promoter/matchmaker memory for accepted/declined offers, cancellations, missed weight, difficult negotiations, short-notice help and performance context.
- Advanced opponent scouting (stance, reach/height, form, strengths/weaknesses, tendencies, techniques) and opponent-aware camp recommendations.
- Short-notice contract premium/fame/goodwill integration; emergency declines do not unfairly freeze normal matchmaking.

### Phase 3 — fight week and career storytelling
- Major/title fight-week presentation, tale of the tape and staredowns, gated away from routine fights.
- Contextual post-event bonuses, ranking/title consequences and completed-card summaries.
- Rivalries can emerge from close decisions, rematches, trash talk and relevant gym history.
- Record book, Hall-of-Fame scoring/induction and genuine adjacent-division double-champion support. Multiple earned belts can coexist.

## Stabilization defects fixed
1. Fresh-world matchup-role code used mutable `Fighter` objects as dict keys and could crash.
2. NPC amateur simulation still wrote to the obsolete Europe-only championship table.
3. Champions could appear in non-title fights.
4. Severe inactivity could lose priority to showcase/eliminator story logic.
5. A single title slot could let healthy champions miss whole defense rotations.
6. The old rematch cache could forget a trilogy after several seasons and theoretically reopen fight #4.
7. Trilogy-saturated champion divisions could freeze with no fresh challenger path.
8. Bounded title lineage could eventually erase Hall-of-Fame/record-book evidence; lifetime title counters are now separate.
9. Short-notice bonuses could be calculated before the true promotion purse and then overwritten.
10. The obsolete Lifestyle gym path has been removed; gym/team remains under Coach.

## QoL
- Nutrition/dashboard show cut status (ahead / on track / behind / ready), weeks left, kg remaining and required kg/week.
- Contract/dashboard surfaces negotiated title/short-notice terms.
- Opponent-aware scouting/camp recommendations reduce redundant manual questions.
- Completed-card and legacy screens expose information already stored by the simulation.

## Release gates
- `python3 -m mma_legend.diagnostics`: **ALL SYSTEMS OK** — v1.30.0, 58 countries, 194 authored opponents, 42 combat moments, 511 event cards.
- `python3 -m mma_legend.tests_130_release`: **19/19 PASS**.
- Historical discovered regression suite: all normal modules from 0.8.1 through 1.30 pass.
- Heavy 2,400-fight fairness suite run independently: Boxing 50%, Wrestling 50%, BJJ 49%, Muay Thai 51%; wrestler-vs-striker 57%; momentum/combination/TKO/contested-standup symmetry pass.

## Long-world evidence
A fresh deterministic full-population 20-year simulation was used as the stabilization gate. Late-world state retained all 12 promotions and valid championship ecosystems, with lifetime opponent meetings capped at three even after recent-memory pruning. The final checkpoint remained around 1,430 active fighters (roughly 593 pros / 837 amateurs) with extensive retirement/staff history retained. Late-year title-gap p90 was around the high 30s/low 40s rather than the earlier 70+ week behavior.

The raw year-20 maximum inactivity was investigated rather than automatically tuned: the 103-week fighter was already booked on the next EFC card. Excluding already-booked or medically unavailable fighters, the longest genuinely available healthy professional was 48 weeks idle.

## Packaging boundary
Release ZIP must exclude saves/autosaves, playtest snapshots/traces, debug logs, bytecode caches, generated playtest bundles and prior ZIPs. The extracted release must pass diagnostics and `tests_130_release` before distribution.
