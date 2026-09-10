# 1.42.0 — Taekwondo & Kicking

Scope: full release containing v1.40 Performance/Education, v1.41 Promotion Rankings/Gym Life and the v1.42 kicking expansion. Taekwondo is now a first-class amateur/Olympic discipline, specialist-gym path and MMA striking identity.

Key validation: diagnostics ALL SYSTEMS OK; v1.40/v1.41/v1.42 suites; v1.30 release gates; historical combat legality, damage/injury, phone-width, sport/calendar and contract suites; 400-fight seeded MMA finish-rate audit returned to ~50% decisions after advanced-kick gating.

# 1.41.0 — Performance, Education & Gym Life

**Goal:** make the fighter's life outside fight night as persistent and legible as the combat/world simulation.

- `performance.py` owns legal supplement stacks, temporary expression/adaptation modifiers, prohibited programs, health burden, anti-doping scrutiny, sample/result state and violations. Raw trained stats are never purchased by supplements/PED programs.
- `education.py` owns secondary school and university state: attendance, grades, graduation, applications, degrees, semesters, credits, exams, tuition, scholarships, pause/dropout and small domain benefits.
- `gym_progression.py` owns specialist-membership background development. BJJ/Judo belt requirements remain in `amateur_sports.py`; promotion is now automatic once those requirements are satisfied.
- `career._promotion_rankings_browser` exposes every named promotion's persistent board without changing ranking ownership in `world.FighterPool`.
- 36 new contextual events react to actual gym membership/education state.
- Save schema v19 adds explicit gym progression state; old saves remain usable as reference fixtures but are not compatibility constraints.

Validation: diagnostics ALL SYSTEMS OK; v1.30 release gates; v1.32–v1.41 modern regression suites; targeted historical economy/education/save suites; event-pack validation; clean extracted release checks.

---

# 1.39.0 — Combat Intelligence

**Goal:** make the canonical fight engine react to the fight that is actually happening rather than only to opening stats/gameplan labels.

- `combat_intelligence.py` remains advisory: `engine/fight.py` still owns legality, positions, damage, scoring, gas and finishes.
- Fighter decision quality is derived from Fight IQ/adaptability/discipline/composure and acts as bounded action-weight changes.
- Live reads track opponent takedown/strike/submission patterns and reinforce or abandon tactics at different speeds.
- Between-round AI responds to failed shots, repeated level changes/kicks, score state, gas state, self damage and opponent damage.
- Takedown chains now create a real second clinch-range finish attempt.
- Scrambles use grappling, speed, control, strength, Fight IQ, adaptability and gas, with outcomes appropriate to the starting position.
- Scouting depth gates the information shown; camps create specific preparation rather than a universal hidden stat boost.
- Added Anti-Wrestling, Submission Defense and Pressure & Entries camp plans.
- Completed opponent-specific camp preparation survives until the booked fight.
- Fight outcomes expose transient action/result telemetry for balance analysis.
- This milestone targets a new long-form playthrough; older saves are reference material, not a compatibility gate.

Validation: v1.39 regression suite, v1.38 living-career checks, v1.30 release gates, diagnostics, legality/booking/camp suites, reduced equal-fighter fairness sample and a two-year living-world audit with zero duplicate bookings, zero invalid title slots and maximum three lifetime pairings.

---

# 1.38.0 — Living Careers

**Goal:** make a long career feel less like a static ladder by giving fighters and promotions persistent motives while preserving the stable v1.37.1 interface.

- NPCs persist a career personality, current career goal, goal-change week and short goal history.
- Goals include develop, activity, rebuild, rank climb, title chase, move up, defend belt and final run.
- Existing `ai.npc_intent()` consumes those goals; `world._climb_npcs()` uses them as a transfer preference rather than creating a second roster-movement writer.
- Promotion identity is data-driven through `PROMOTION_PROFILES`: UFC emphasizes merit/star power, LFA/Cage Warriors/ARES protect and test prospects, ACA emphasizes hard merit matchmaking, regional organizations favor local development, and other promotions have their own blends.
- The existing semantic card builder consumes promotion identity through pair-cost/probability adjustments, preserving hard trilogy and booking constraints.
- Pro inbox offers now show career meaning, risk/upside and promotion identity. Eligible promotion desks are ranked by résumé, fame/activity, regional fit and existing promoter/matchmaker rapport instead of mostly shuffled. Opportunity results feed bounded fame/reputation/legacy rewards.
- The v1.37.1 UI/navigation remains frozen; no menu hierarchy redesign was introduced.
- Save version remains v17; old saves default new fields safely and populate NPC career state on the next world tick.
- Fixed the post-offer `X) Back out` path, which previously could loop at the decision prompt.

Validation: v1.38 tests, v1.37.1 UI checks, v1.30 release gates, diagnostics, supplied playtester saves and a three-year long-world audit with zero duplicate-booking weeks, zero invalid title slots and maximum three lifetime pairings.

---

# 1.37.1 — training menu cleanup

**Goal:** finish the UI freeze with one focused readability change requested from phone playtesting.

- Train and Amateur are plain-text weekly actions; Fight retains its contextual glove emoji when shown.
- Training focus is rendered as a single vertical list from Striking through Balanced.
- Intensity is rendered as a separate vertical list with aligned energy cost and injury risk.
- Repeat Last Session remains available but is visually separated from the focus choices.
- Back/cancel at either training stage remains browse-safe and spends no week or energy.
- Underlying training gains, injury probabilities and save schema remain unchanged.

Validation: v1.37.1 targeted UI tests, v1.37/v1.36 navigation checks, v1.30 release gates, compileall and system self-check.

---

# 1.37.0 — UI freeze candidate

**Goal:** stop redesigning the navigation and polish the restored v1.36 interface into a stable beta-facing UI baseline.

- Weekly actions remain flat and direct; secondary career information stays separated underneath.
- Only Train, Fight and Amateur use action-list emojis. Deep management screens use plain text headers.
- Generic choice prompts use one `>` style across the main app/career/fight flow.
- Compact Dashboard now actually reduces weekly information density.
- Color preference is saved on the Fighter schema (`ui_color`) while `--no-color` remains authoritative.
- Fighter presentation is grouped by combat domain instead of one long stat dump.
- BJJ/Judo progress, contracts, weight and fight-week state are presented in shorter phone-friendly lines.
- Navigation/time-spend semantics are unchanged from 1.36: only explicit completed activities advance time.
- Save version remains v17 and older playtester saves load without migration loss.

Validation: v1.37 UI checks, v1.36/1.36.1 navigation/menu checks, v1.35/v1.34 UI checks, v1.30 release gates, v1.22 phone-width checks, system self-check, and supplied v1.30 playtester save loads.

---

## 1.36.1
Focused menu cleanup requested after the v1.36 UI recovery. Amateur booking moved under Amateur; weekly labels simplified; NO TIME wording removed; emoji use reduced. Save v17 unchanged.

# 1.36.0 — UI recovery / navigation-safety milestone

**Reason:** 1.34/1.35 added useful information and fight-prep QoL, but playtesting found the new hub hierarchy visually busy and less intuitive than the older direct-action interface. 1.36 keeps the useful underlying systems while deliberately restoring a flatter navigation model.

## Player-facing changes
- Weekly actions are direct again: Train, Rest, Fight, Amateur, Nutrition, Team and Life.
- Fighter/Stats, Rankings, Calendar, Alerts, Timeline/Money and Save are visibly separated as browse-only NO TIME screens.
- The title menu is short and old-style; the tutorial is a three-page linear primer and no longer interrupts new career creation.
- Dashboard, Team, Life and Nutrition use a restrained colour/symbol hierarchy and less repeated explanatory text.

## Correctness fixes
- Removed whole-Fighter serialization diffs as the Team time-spend detector. Harmless metadata synchronization can no longer advance a week.
- Team training uses an explicit completion signal. Coach advice and belt evaluation are browse-only.
- Relationship, school and medical Back paths are true no-time exits.
- Weekly manager/news processing is executed once per actual week rather than once per menu return.

## Compatibility / validation
- Save schema remains v17 and all three supplied 1.30 playtester saves load with their full ~1,532-fighter worlds.
- Diagnostics: ALL SYSTEMS OK.
- 1.27-1.30 release gates, 1.32-1.36 UI/maintenance suites and 1.19.4 fairness checks pass in the 1.36 tree.

Keep 1.35.0 as the rollback point for the prior UI architecture.

---

# 1.35.0 — UI / QoL Part 2

Added Career overview/calendar, Fight Prep, gameplan recommendation, paged timeline, post-fight summary and optional guided UI preferences. The underlying features remain in 1.36, but the weekly navigation and onboarding presentation were simplified after playtest feedback.

---

## 1.34.0 Part 1 — UI / Navigation QoL

- Replaced the weekly skill wall with a compact decision dashboard.
- Reorganized the weekly action surface around Career, Team, Life, Fight/Inbox, Train and Rest; legacy H/I/N/Z shortcuts remain accepted.
- Added visible time/energy/context tags to weekly actions.
- Added persistent alerts with a Career inbox; dashboard viewing no longer consumes/clears notifications.
- Added week-end change reports covering money, condition, weight, fame and trained skills.
- Reworked regular training around a fast repeat-last-session path. Invalid/cancelled training no longer drains energy or spends a week.
- Added a persistent mini status strip to high-traffic hubs.
- Removed unreachable legacy coach-hub UI code.
- Save format remains v17 and older 1.33 saves remain loadable.

# 1.33.0 — maintenance/refactor baseline

**Status:** clean developer baseline built from 1.32.0. Gameplay/save semantics remain compatible with JSON v17; this pass primarily separates runtime, tests, tools and documentation while fixing defects discovered during the move.

## Structural cleanup

- Runtime code remains under `mma_legend/`; 36 versioned regression modules moved to top-level `tests/` so player code is no longer mixed with release history.
- Developer-only `save_repair`, `sim_careers`, `world_audit` and release packaging moved to `tools/`. Runtime modules do not import them.
- Current architecture/changelog/system-map/version-history documents live under `docs/current/`; prior release audits and handoffs remain under `docs/history/`.
- Removed redundant `run.py`. `START.py` remains the phone entry point and delegates to a simplified `main.py`; `python3 -m mma_legend` is now supported.
- Removed the orphaned `rng.py` helper after import-graph verification showed no runtime or test consumer. It was not connected to the engine and therefore could not provide the replay guarantee its docstring implied.
- The launcher intentionally searches only its own directory, eliminating the previous sibling-version scan that could load an older `MMA_Legend*` folder when several builds existed on one device.

## Bugs fixed while refactoring

1. **Regression discovery gap:** `tests_132.py` defined `run()` but not `main()`, while the old all-tests runner called only `main()`. A supposedly full regression run therefore printed “imported ok” and skipped every 1.32 assertion. `tests.runner` now requires and executes either entry point.
2. **Imported save-repair crash:** the write branch in the old `repair.py` referenced `_rec` that was only imported in the module's `__main__` block. Calling `audit_file(..., write=True)` after importing the module could raise `NameError`. The tool now imports its dependency inside the callable path and writes UTF-8 JSON explicitly.
3. **Side-sport rows misclassified as MMA:** `record.is_mma()` previously excluded only BJJ/No-Gi/grappling, so explicit Combat Sambo, Boxing, Kickboxing, Wrestling and Judo history rows returned true. Explicit sport/ruleset metadata is now authoritative; event-name heuristics exist only for legacy untagged rows. The supplied 1.30 playtester save now audits cleanly instead of reporting a false amateur-MMA record mismatch.

## Validation

- `compileall` passes for runtime, tests and tools.
- `mma_legend.diagnostics` reports all systems OK on v1.33.0.
- 1.32 and new 1.33 regression gates pass after the move.
- Historical suites through 1.19.3 were rerun from their new `tests/` location and passed; the unchanged 1.19.4 2,400-fight fairness suite is too heavy for the single-command execution cap, so reduced fairness probes are used in this maintenance pass while the exact engine remains unchanged from the previously validated 1.32 build.
- All three supplied v1.30 saves load under the refactored runtime; the save-audit false positive caused by Combat Sambo rows is removed.

Keep 1.32.0 as the previous rollback point.

---

# 1.30.0 — stable Phase 1–3 milestone

**Status:** stable inspection baseline built from 1.29.0 after completing the previously unfinished long-world matchmaking, contract/manager/scouting preparation and fight-week/post-event/legacy roadmap. Save schema is JSON v17. Runtime saves and playtest telemetry are diagnostic-only and are not bundled.

## Why 1.30 exists

The 1.29 audit showed that Phase 1 was only partly semantic and that major portions of Phase 2/3 were either shallow, disconnected or missing. In particular, promotion-role labels were not driving the live card builder, contract negotiation existed as backend code without a complete player workflow, promoter memory imported a nonexistent module and failed silently, scouting/camps were too generic, and Phase 3 lacked a coherent fight-week/post-event/legacy layer.

1.30 closes those gaps as shared systems rather than isolated menu text.

## Phase 1 — long-world intelligence

- `promotion_events.py` now uses real bout roles: prospect showcase, gatekeeper test, contender fight, title eliminator, rebuild, activity, rematch and title defense. Extreme inactivity receives priority over story-role preferences.
- Champions are excluded from ordinary non-title matchmaking. Severely overdue championships can receive a second title slot when necessary.
- Recent pairing memory remains useful for rematch flavor, but `lifetime_matchups` independently enforces a hard trilogy ceiling across an entire career. Five-season recency pruning can never reopen fight #4.
- Thin/saturated divisions repair themselves by importing or swapping in legitimate fresh same-tier opposition. Champions whose entire local contender pool is trilogy-saturated receive a fresh challenger instead of becoming permanently frozen.
- Persistent lifetime title wins/defenses are recorded on fighters so the capped recent `title_history` feed can remain bounded without erasing career legacy.
- Fresh-world crash fixed: matchmaking-role bookkeeping no longer uses mutable `Fighter` objects as dictionary keys.

## Amateur geography/calendar

- Small federations skip artificial Regional Opens; larger countries retain them.
- Nationals remain the domestic championship layer. Continental competition is exactly once per year and routes to European, Pan-American or Asian Championships from the fighter's country.
- Worlds remain annual. Boxing, Wrestling and Judo retain the four-year Olympic route.
- NPC amateur simulation was migrated off the obsolete Europe-only table and now uses the same regional model as the player.

## Phase 2 — contracts, managers, memory and preparation

- Contract workflows now negotiate purse, show/win economics, fight count, term, clauses and eligible non-exclusivity. Smaller promotions may concede freedom for lower guarantees; major promotions can refuse.
- Supported clause effects include short-notice purse premium, championship-fight escalation and rematch option. Bonuses are applied after the actual promotion purse is known, fixing an overwrite bug that could erase the premium.
- Manager negotiation/scouting/career-management competency is live alongside personality and relationship.
- Added `memory.py`: promoters/matchmakers remember accepted/declined offers, accepted short notice, cancellations, missed weight, difficult negotiation and meaningful performance context. Broad silent import failure is no longer the behavior.
- Medical withdrawal is treated more leniently than an ordinary cancellation; card logic can search for replacements.
- Scouting now uses real opponent information including stance, reach/height, recent form, strengths/weaknesses, style/tendencies and frequently used/mastered techniques. The amount revealed scales with scouting quality.
- Camp planning reads the booked opponent and recommends a focus/reason automatically.
- Short-notice economics/fame/relationship consequences are integrated, while declining an emergency request does not unfairly block routine matchmaking.

## Phase 3 — fight week, event consequences, rivalries and legacy

- New `phase3.py` gates fight-week presentation by actual importance. Major/title bouts can show tale of the tape and a player-choice staredown without spamming routine cards.
- Post-event processing can award contextual performance bonuses, compute ranking movement/title consequences and annotate the persistent event row.
- Rivalry creation uses actual bout context: close decisions, rematches, trash talk and relevant gym history.
- Completed-event summaries expose important results, championship changes, bonuses and rankings consequences.
- New `legacy.py` provides title statistics, current belts, performance bonus count, record book, Hall-of-Fame score/tier/candidate logic and induction.
- Adjacent-division double-champion opportunities are supported for proven champions. A fighter can retain multiple legitimate belts instead of a new belt silently erasing the old one.

## QoL / stabilization

- Nutrition/dashboard now show fight-cut pacing: status (ahead/on track/behind/ready), weeks left, kg remaining and required kg/week.
- The obsolete Lifestyle `G` gym path is removed; gym/team remains under Coach.
- The long-world audit now distinguishes raw inactivity from fighters already booked or medically unavailable when diagnosing stranded fighters.

## Release evidence

- `python3 -m mma_legend.diagnostics`: **ALL SYSTEMS OK**, v1.30.0, 58 countries, 194 authored opponents, 42 combat moments and 511 events.
- `python3 -m mma_legend.tests_130_release`: 19/19 milestone checks pass, covering regional calendars, fresh-world generation, semantic roles, hard trilogy cap, thin-roster refresh, inactivity/title priority, contracts/exclusivity, fight week/staredown, post-event/rivalry, double champion, Hall of Fame/record book, completed-card summaries, lifetime-history preservation and weight/dashboard QoL.
- Historical regression discovery passed all normal modules from 0.8.1 through 1.30.
- Heavy 2,400-fight fairness suite passed independently: Boxing 50%, Wrestling 50%, BJJ 49%, Muay Thai 51%; wrestler-vs-striker 57%; momentum, combinations, TKO and contested-standup symmetry passed.
- Fresh deterministic 20-year full-population stabilization run completed with all 12 promotions active, zero invalid belts, lifetime matchup maximum exactly three, title-defense p90 around the high-30s/low-40s during late years, and no long-horizon runtime explosion. At the final checkpoint the world remained roughly 1,430 active fighters (about 593 pros / 837 amateurs) with hundreds of historical retirements/staff preserved.
- Year-20 raw inactivity outlier was investigated rather than blindly tuned: the 103-week fighter was already booked on the next EFC card. Excluding future-booked or medically unavailable fighters, the longest genuinely available healthy pro was 48 weeks idle.

## Version decision

`1.30.0` is the stable inspection baseline for deciding the next major development direction. It is not a claim that the game is near beta; the project is still mid-development. Keep 1.29.0 as the prior rollback point.

---

# 1.29.0 — focus-aware amateur calendar and fight history

**Status:** lead-developer approved stable baseline, built from the approved
1.28.0 baseline. Save schema is JSON v15. Supplied player saves remain
diagnostic-only and are not bundled.

## Phase 1 re-audit

- Confirmed that v1.28 already kept independent W-L-D ledgers and tagged
  history rows for all seven sports, but found three player-facing integration
  gaps: the Amateur hub always exposed MMA actions, side championships ran
  immediately instead of on a calendar, and side bouts had no explicit fight
  mode picker.
- The weekly `C) Fight` shortcut also bypassed active sport and could book MMA
  while the player was focused on Judo, Boxing or another sport.
- MMA's legacy calendar still displayed ADCC entries, leaking a side-sport
  competition into MMA focus.

## Exclusive active-sport routing

- `_actions_for`, `_dispatch_action` and `_amateur_hub` now use
  `active_amateur_sport` as the routing gate. MMA focus exposes MMA only; a
  side focus exposes only that selected sport.
- Turn-pro prompts are hidden outside MMA focus. The player retains all prior
  records and can switch back, but cannot enter a hidden sport accidentally.
- A live championship registration blocks changing focus until the player
  cancels it or the event resolves.

## Scheduled side-sport calendar

- Added absolute-date `calendar_entries()` for two Regional Opens, two
  Nationals, two Europeans and one World Championships per sport/year, plus
  the next valid four-year Olympics for Boxing, Wrestling and Judo.
- Side-sport signup opens eight weeks before the event and persists event name,
  sport, level, season week and absolute career week. The event resolves only
  after the world reaches that date.
- Added qualification explanations for sport XP, sport-specific national team,
  European nationality, European medal and Olympic World/European results.
- Old MMA registrations receive matching sport/level/absolute date metadata.
  Legacy ADCC signups can still resolve, but new ADCC entries are no longer
  shown while MMA is the selected focus.

## Fight modes and visible records

- Every BJJ / No-Gi, Boxing, Kickboxing, Wrestling, Judo and Combat Sambo bout
  now offers Play, Live Sim or Instant. One tournament choice applies to the
  full bracket rather than interrupting between rounds.
- History rows now include opponent ID, event, sport display name, ruleset,
  competition level, career week, selected mode and fight statistics.
- The selected sport hub and calendar show recent bouts. Career Statistics
  shows the six most recent non-MMA fights across sports.

## Integration fixes

- Fixed national-team assignment writing to a stale dictionary reference after
  the migration guard refreshed top-level sport state. A National medal now
  reliably persists selection for exactly that sport.
- Absolute due weeks prevent registrations from being lost across year wrap or
  delayed-save loading. Turning professional clears all new registration fields.
- Save v15 adds `competition_sport`, `competition_level` and
  `competition_due_week` with migration defaults for older MMA registrations.
- Added `tests_129` covering exclusive menus/shortcuts, full calendar cadence,
  four-year Olympics, sport-bound registration, event-week resolution, focus
  switching, simulation modes, dated fight history and save-v15 persistence.

## Release evidence

- Compilation and the full discovered historical regression suite pass with
  `FAILED MODULES 0`, including 2,400-fight engine fairness at
  Boxing 50 / Wrestling 50 / BJJ 49 / Muay Thai 51.
- `tests_129` passes focus-exclusive menus, complete annual/four-year calendar
  cadence, dated registration/resolution, fight modes, history metadata and
  save-v15 persistence.
- Real non-mocked Instant bouts completed under BJJ / No-Gi, Boxing,
  Kickboxing, Wrestling, Judo and Combat Sambo rules.
- Diagnostics report v1.29.0, 58 countries, 194 authored opponents, 42 combat
  moments and 511 events; every system passes.
- Deterministic five-year world audit: 835 active amateurs, 620 active pros,
  all seven sports and all 12 organizations populated, inactivity median 15 /
  p90 39 / p99 54 / max 69 weeks, with zero duplicate booking weeks, invalid
  title slots or UFC champion/belt mismatches.

## Version decision

`1.29.0` is approved as the new stable baseline. Keep the clean 1.28.0 ZIP as
the rollback point. See `RELEASE_AUDIT_1.29.0.md` for the concise handoff.

---

# 1.28.0 — multi-sport championships and long-world integrity

**Status:** lead-developer approved stable baseline, built from the approved 1.27.0 baseline. Save
schema is JSON v14. Supplied player saves and traces were used only as read-only
diagnostic references and are excluded from the package.

## Seven complete amateur ecosystems

- Added independent Regional, National, European, World and Olympic tables for
  all seven sport ledgers. Nationals run at weeks 12 and 38; Europeans at 20
  and 46; Worlds at 28.
- Added sport-specific national-team selection. Winning a Judo National place
  no longer grants MMA, Boxing or any other sport's eligibility.
- Added a four-year Olympic tournament at week 32 for Boxing, Wrestling and
  Judo. Qualification requires the relevant national team, sufficient sport XP
  and World/European results. The Olympic bracket has four matches.
- Fixed championship energy gates that could admit a fighter who had enough
  energy to start a three-match bracket but could not legally enter its final.
- Fixed sport focus input for phone play: number, letter, full name and aliases
  are accepted. Save-v13 migration now preserves a legacy selected side sport
  instead of defaulting it back to MMA.

## Population, identity and permanent specialists

- Increased the standard world to 840 amateurs and 560 initial pros, with
  active targets of 840 amateurs and 620 professionals. Intake replenishes the
  seven sport fields and qualified MMA prospects replace pro retirements.
- NPCs now own an explicit `mma_transition` career intention. A substantial
  minority of side-sport specialists never cross over; eligible specialists
  can move into amateur MMA after building a genuine record.
- New zero-bout amateurs now actually compete and develop. The old intake path
  created prospects who could remain at 0-0 forever.
- Added nationality-linked first/last-name pools and mapped all supported
  countries to appropriate regional naming groups. Original authored opponent
  names remain preferred before generated combinations.

## Promotion calendars, matchmaking and rankings

- Rebuilt card matching around longest idle time plus résumé/ranking fit.
  Persistent matchup memory heavily penalizes recent and repeated pairings.
- Opening rosters are balanced before cards are created. Runtime vacancy logic
  now permits legitimate same-tier regional transfers; the old comparison
  could strand one division with two fighters while a peer promotion had
  surplus talent.
- Pro intake prefers the fighter's home promotion, then fills a thin regional
  division through international scouting. Earned UFC recruitment now uses
  live results and streaks without draining feeder divisions below their floor.
- Scheduled NPC bouts update W-L-D, five-fight form, signed streak, idle time
  and capped fight history only when their dated event resolves.
- Cancelled bouts no longer reserve fighters in the open-booking set.

## Belts and lineage

- `FighterPool.belts` is authoritative for every organization. Rankings derive
  champions from the live belt holder and remove that fighter from numbered
  contender slots.
- Belt rows persist reign start, defense count and last defense. Successful
  defenses no longer reset the championship; new champions clear the previous
  holder cleanly.
- Added capped title lineage for inaugural champions, vacancies, title wins
  and defenses. The Rankings screen shows recent lineage and defense totals.

## Persistence and diagnostics

- Save v14 persists per-sport championship/national-team state, world title
  lineage and matchup memory.
- Added deterministic `world_audit.py` for 5/10/20-year population, promotion,
  inactivity, pairing, card, title and Olympic diagnostics.
- Added `tests_128` for full sport ladders, phone-friendly selection,
  sport-specific teams, Olympic qualification, permanent specialists,
  country-specific names, viable opening divisions, NPC form, title defenses
  and save-v14 state.

## Release evidence

- Full discovered regression: all 33 versioned modules green,
  `FAILED MODULES 0`; compileall passes.
- Diagnostics: v1.28.0, 58 countries, 194 opponents, 42 combat moments and 511
  events; combat/save/people/booking/data all pass, `ALL SYSTEMS OK`.
- Deterministic 20-year audit: 837 active amateurs, 596 active professionals,
  all seven sports and all 12 organizations populated, UFC roster 78,
  inactivity median 15 weeks / p99 49 / max 71.
- The same audit resolved 2,044 title fights across all 96 promotion/division
  combinations and produced 21 Olympic medalists. It found zero duplicate
  booking weeks, invalid title slots or UFC champion/belt mismatches.
- Matchmaking produced 5,726 unique pairings; the most repeated pair met eight
  times across twenty years, down from a rejected pre-fix case of 15 meetings
  in five years.

## Version decision

`1.28.0` is approved as the new stable baseline. Keep the clean 1.27.0 ZIP as
the rollback point. See `RELEASE_AUDIT_1.28.0.md` for the concise handoff.

---

# 1.27.0 — amateur sport careers, belts, media identity and living cards

**Status:** lead-developer approved stable baseline, built from 1.26.0. Save
schema is JSON v13. The supplied human saves and traces were used read-only as
diagnostic references and are not included in the release.

## Amateur sports and martial-arts grades

- Added seven explicit competition focuses: MMA, BJJ / No-Gi, Boxing,
  Kickboxing, Wrestling, Judo and Combat Sambo. Background discipline remains
  separate from the active sport.
- Side sports now own their records, experience, sport-specific weight labels,
  regional/national championship opportunities and medal tables. Their results
  are written to tagged history rows and never change amateur-MMA or pro W-L.
- Added `JudoRuleset` and `CombatSamboRuleset`, both enforced by the shared
  menu/AI/resolution action gate. Judo is throws, pins and legal upper-body
  submissions; Combat Sambo combines striking, takedowns and submissions.
- Replaced player-facing Sambo identity with Combat Sambo. Save v13 migrates
  old Sambo background/style/competition flags; historic named techniques such
  as Sambo Throw remain valid.
- BJJ now progresses white/blue/purple/brown/black through grade points, real
  mat weeks, stripes and a paid coach evaluation. Judo now progresses
  white/yellow/orange/green/blue/brown/black through its own points, weeks and
  grading. Both persist and provide bounded relevant-action accuracy bonuses.
- Removed Gym from Lifestyle. `T) Coach` is now the single Gym & Team hub for
  coaching, technique work, home sparring, teammates, specialist membership
  and belt evaluation. Added a Judo dojo membership alongside BJJ/kickboxing.

## Fame, media and fighter identity

- Added `notoriety.py` as the mutation/gating service for bounded 0-100 Fame,
  followers, temporary press hype, decay and bout exposure. Core runtime fame
  rewards now log their reason through this service.
- Rebalanced amateur fame: routine amateur/side-sport bouts give no fame;
  regional medals give little recognition and National/European/World golds
  award 3/5/8 rather than the previous 15/30/50 jumps.
- Post-fight interviews are suppressed for amateur and low-end pro prelims.
  Featured fights receive regional media; UFC main events and title fights get
  major coverage and a contextual pre-fight press conference.
- Added 144 phone-safe nicknames. They unlock from pro wins, fame or sport gold,
  are suggested from fighter strengths, allow a custom name or deferral, and
  avoid duplicate NPC nicknames inside the same organization.

## Persistent promotion cards

- Added `promotion_events.py`. All 12 promotions now maintain dated event
  objects with stable IDs, location, headliner/co-main/prelim slots, weight
  classes and title flags. Organization cadence ranges from UFC every three
  weeks to smaller promotions every six to eight.
- Player offers attach to a real event and inherit its week/location. The full
  card displays on fight week and upcoming headliners are visible from
  Rankings. NPC results now occur only when the scheduled card reaches its
  week; the old immediate random weekly pro-fight call is no longer used.
- Added opponent withdrawals, in-organization replacement search, short-notice
  flags and clean cancellation when no replacement exists. Event bookings are
  updated with the replacement and fighters cannot occupy two open cards.
- Title slots must contain the live champion. A 3,600 organization-week stress
  run found stale future title labels after champion changes; `repair_titles`
  now downgrades those invalid flags before they can reach fight week.
- UFC title fights now run challenger-first/champion-second introductions with
  nickname, country, record and weight before the opening bell.

## Event content and integration fixes

- Added 24 context-gated events for side sports, dojo/gym life, teammates,
  promoters, replacement rumors and legitimate higher-tier media. Total event
  inventory is 511 and the event DSL now understands `active_sport`.
- Restored `engine/scoring.py` from the untouched 1.26 rollback after release
  validation found the working copy unexpectedly truncated mid-constructor.
  Compilation caught this before packaging; the restored behavior matches the
  stable baseline.
- Save v13 persists event calendar/history/world week, both belt systems,
  nickname state and sport progression. A supplied v1.26-era human save loaded
  read-only with its 4-4 MMA ledger intact and all v13 defaults present.

## Release evidence

- Full discovered regression: all 32 versioned modules green,
  `FAILED MODULES 0`; compileall passes.
- Diagnostics: v1.27.0, 58 countries, 194 opponents, 42 combat moments and 511
  events; combat/save/people/booking/data all pass, `ALL SYSTEMS OK`.
- Existing 2,400-fight fairness gate remains Boxing 50%, Wrestling 50%, BJJ
  49%, Muay Thai 51%; wrestler-vs-striker 57%.
- Balance lab: amateur equal 54%, pro equal 51%, elite equal 45%; decision rates
  85%/78%/49% respectively.
- Calendar stress: 3,600 organization-weeks across all 12 promotions, zero open
  double bookings and zero invalid title slots after the repair.
- All 511 event cards render at 44 columns or less in the existing phone gate.

## Version decision

`1.27.0` is approved as the new stable baseline. Keep the clean 1.26.0 ZIP as
the rollback point. See `RELEASE_AUDIT_1.27.0.md` for the concise handoff.

---

# 1.26.0 — reach, real defensive skills and ruleset reconstruction

**Status:** lead-developer approved stable baseline, built from the approved
1.25.1 package. Save schema is JSON v12. Supplied older saves remain diagnostic
references and are not bundled or promised as long-term compatibility targets.

## Skill and technique model

- Expanded the weighted fighter sheet from 12 to 15 skills. Striking Defense,
  Submission Defense and Distance Management are now generated, trainable,
  persisted and shown like the other combat skills.
- Added persistent reach (centimetres) and stance. Reach is generated from
  height/physique and affects range contests and accuracy only; it never adds
  damage.
- Removed seven broad concepts from the move database presented to coaches:
  Boxing Defense, Kickboxing Defense, Sambo Defense, BJJ Escape, Distance
  Management, Cage Cutoff and Pressure Walking.
- Save upgrade v12 converts those legacy concept levels once into modest points
  in the corresponding real skill, then removes the old move labels.
- All 117 remaining teachable rows receive structured `action_id`, `role`,
  `target` and `kind` metadata. Specific reactions such as Philly Shell,
  Shoulder Roll, Long Guard, Leg Kick Check and Peel the Hands remain learnable
  techniques but are passive reactions, not attack buttons.
- Replaced the unused invisible 1-10 passive counters with a small chance for
  real tactical-skill growth during relevant sessions.

## Fight engine

- Added outside / kicking / boxing / pocket range bands. Every standing exchange
  runs a symmetric contest using Distance Management, Fight IQ, speed, reach
  and specific reaction training. AI selection and accuracy respect the current
  band and each fighter's preferred range.
- Pre-fight tactics now include preferred range and Movement / Guard / Counter
  defence. Missed standing strikes can create a bounded counter window.
- Striking Defense now opposes clean standing connections. Submission Defense
  opposes both submission setup and the final finish roll. These calculations
  are symmetric for the player and opponent.
- Expanded grappling to open guard, front headlock, north-south and leg
  entanglement, with real transitions for snap-downs and leg entries plus heel
  hooks, kneebars and north-south chokes.
- Existing chains remain live: jab-to-power combinations and chain wrestling;
  the expanded position graph adds setup-to-submission chains rather than
  allowing advanced submissions from arbitrary ground positions.

## Sport rules

- `Ruleset.allows_action()` is now consumed by technique menus, AI choice and
  final resolution—the three paths share one enforcement gate.
- Boxing permits standing punches only. Kickboxing permits punches, kicks and
  limited clinch striking but no takedowns/ground work. Wrestling permits
  takedowns, rides, escapes and positional advancement but no strikes or
  submissions. Grappling excludes strikes. MMA retains the complete legal set
  subject to amateur fouls.
- Period length now belongs to each ruleset instead of being inferred only from
  the old `grappling_only` flag.

## Integration and balance defects found during release gating

- Seeded simulations were not repeatable between Python processes because AI
  iterated a set of legal actions in hash order. Legal actions are now sorted
  before weighted selection and safety fallbacks.
- The equal-fighter balance fixture equalized division and 15 skills but not
  the newly added reach/stance. It now equalizes both, preventing the fairness
  lab from measuring a hidden physical mismatch.
- Stabilized the old brutal-weight-cut Monte Carlo regression with a local seed;
  it no longer depends on random work performed by earlier test modules.
- Updated intentional position-legality assertions for the expanded graph; no
  behavioral guardrail was removed.

## Release evidence

- Full discovered regression: all 31 versioned modules green,
  `FAILED MODULES 0`.
- New `tests_126`: 15-skill/reach schema, concept migration, structured move
  metadata, reaction filtering, position graph, five-sport legality, range
  control and striking-defense effectiveness all green.
- Standalone strict fairness: 2,400 clone fights; Boxing 50%, Wrestling 50%,
  BJJ 49%, Muay Thai 51%. Wrestler-vs-Muay-Thai viability: 57%.
- Damage/injury calibration sample: 61% decisions / 39% finishes.
- Balance lab (about 300/scenario): pro equal 47%, elite equal 52%; pro equal
  81% decisions and elite equal 54% decisions. The narrow basic-kit fixture is
  decision-heavy by construction; varied-style NPC calibration remains 61/39.
- Diagnostics: version 1.26.0, 487 events, combat/save/people/booking/data all
  pass, `RESULT: ALL SYSTEMS OK`. Compileall passes.

## Version decision

`1.26.0` is approved as the new stable baseline. The clean 1.25.1 ZIP is kept
as the rollback point. See `RELEASE_AUDIT_1.26.0.md` for the concise handoff.

---

# 1.25.1 — senior review / stable 1.25 baseline

**Status:** senior approved. The 1.25.0 junior candidate was not approved
unchanged; the blocking integration faults below were corrected first.

## Audit scope and evidence

Reviewed the handoff, v1.24 playtest audit, full developer history, architecture,
system map and player changelog before editing. Audited every area claimed by
1.25.0: contract/identity repair, UFC title and ranking gates, weight-campaign
state, weekly economy/debt, contextual event selection/effects, long-screen
pacing, lifestyle menu cleanup and supplement sponsor utility.

The junior feature work was otherwise coherent: weight campaigns use real
walking mass and one canonical weigh-in; the weekly ledger is applied once;
event requirements/effects validate; the new pack remains supplemental; and
all 36 new cards render within the phone content width.

## Blocking defects found and fixed

### `contracts.py`, `identity.py`

- `contracts.release()` emptied `org_contract` but retained
  `fighter.organization`. `identity.sync()` and `contracts.active()` then
  interpreted that intentional free-agent state as the v1.24 blank-contract
  corruption and silently reconstructed an exclusive deal.
- Release now clears organization, generic/UFC rank, ranking board,
  `ufc_signed`, and stale title-offer state while retaining `last_release`.
- Runtime and raw-save blank-contract healing now requires
  `exclusive is True`. This preserves recovery of the observed corrupt save
  without treating `{}` as damaged contract data.

### `world.py`, `identity.py`

- `world.update_rankings()` counted DWCS as UFC experience. Its first UFC board
  applied the three-bout gate, but the later per-promotion board inserted the
  player anyway and rewrote `ufc_rank`; stale UFC rank also was not cleared
  for a still-signed but ineligible player.
- Added one promotion-history helper shared by rankings and title eligibility.
  It accepts `UFC` and UFC-branded card labels, excludes DWCS, and counts pro
  bouts only.
- The three-UFC-bout player gate now applies consistently to the divisional,
  per-promotion and P4P boards. Rank/board flags are cleared before rebuilding.

### `career.py`, `data/career_and_sponsors.json`

- Free legal supplements were granted by substrings in a sponsor name, which
  made future naming changes and accidental matches part of gameplay logic.
- Supplement suppliers now declare the `legal_supplements` benefit in sponsor
  data, and the shop checks that capability.

### `tests_1251.py`

Added behavioral coverage proving that:

- a declined/released UFC deal remains released after sync and permits another
  promotion;
- only an explicitly exclusive blank deal self-heals;
- DWCS plus two UFC appearances is still unranked, while a third UFC-branded
  bout permits divisional/P4P ranking;
- supplement coverage is metadata-driven rather than keyword-driven.

## Balance and diagnostic evidence

- Standalone engine fairness: 2,400 fights; clone player-slot win rates Boxing
  45%, Wrestling 49%, BJJ 50%, Muay Thai 50%; wrestler vs Muay Thai 64%.
- Balance lab (300 per scenario): equal pro 51%, elite equal 48%; method mixes
  remained within existing regression expectations.
- Headless careers (60 x 80 weeks): no amateur-veteran mismatch, premature
  major-promotion offer, or grappling KO violations. Low simplified-career win
  rates remain the already-documented probe limitation and did not justify
  changing a demonstrably fair combat engine.
- Event DSL: zero validation issues across 487 events. In 12,500 weekly draws,
  ordinary profiles fired ~17-19%, the hurt/loss profile 38.6%, v1.25 content
  was 0.2-6.0% of fired cards, and immediate category repeats were 8.1-14.9%.
- Rendering all 36 new events at phone width produced a maximum 42-character
  content line.
- Economy: 52-week ledger totals reconciled exactly. School/amateur support was
  +$1,420; regional pro recurring net was -$4,056 before fight/job income; a
  booked UFC contender with three retainers was -$5,616. Debt at 1.2% weekly
  remains intentionally punitive and should be revisited only with real-career
  income/purse telemetry.
- Full regression discovery, `tests_125`, `tests_1251`, standalone `tests_194`,
  diagnostics and compileall passed. The final archive was then re-extracted
  and validated again before release.

## Version decision

`1.25.1` is the new stable baseline. Save schema remains JSON v11: all changes
use existing fighter fields or optional sponsor content metadata.

---

# 1.25.0 — junior handoff from 1.24 human playtest

**Status:** junior-developer handoff candidate for senior review. Do not interpret this label as “senior-approved release.”

## Input evidence

The only supplied playtest artifact was `save_auto(3).json` from v1.24.0. It was treated as diagnostic evidence only and is intentionally excluded from this package. High-signal state from that snapshot:

- player was visibly in UFC, but `org_contract.org` was blank while the deal was exclusive;
- generic `org_rank` was #1 while UFC-specific `ufc_rank` was #7;
- an old LFA belt was still stored as active;
- `title_offer_week` existed and the first recorded UFC bout was a five-round title fight;
- cash/debt/weekly ledger fields showed two competing economy calculations;
- the player was walking ~87.9 kg for Middleweight and wanted nutrition to perform more of the real camp reduction;
- several supplement brands were already sponsors but sponsorship had little concrete utility.

Loading the supplied autosave under this branch (without writing it) produced: active UFC contract restored, old LFA belt moved to former history, UFC rank/org rank reconciled to #9 in the loaded world, ACA date blocked by UFC exclusivity, and `identity.title_shot()` returned `None`.

## Code changes and rationale

### `identity.py`, `contracts.py`, `orgs.py`, `world.py`, `persistence.py`

- Repair named-promotion + blank-contract corruption toward the named promotion.
- Reject blank organization when creating a contract.
- Clear stale previous-promotion belt on signing and retain it in `former_belts`.
- UFC title logic now uses UFC-specific rank/history. Required challenge gate: top-3 UFC rank, >=3 UFC bouts, >=2 UFC wins, live +2 streak, no recent loss. Champion defenses remain separate.
- Promotion ranking refresh reconciles `org_rank`/`ufc_rank`; save debug header reports UFC-specific rank when in UFC.
- Added playtest audit signals for the exact corruption family.

### `cut.py`, `booking.py`, `career.py`

- Booking initializes `story_flags.weight_camp`.
- Added `WEIGHT_STRATEGIES`: performance (4% final water target), balanced (7%), bully (10.5%).
- `tick_body()` records weekly walking weight/bodyfat/nutrition/plan during a booked camp.
- Deficit meal plans chase the strategy target over remaining weeks; maintenance/bulk plans do not receive hidden loss.
- Final weigh-in stores real mass lost, water cut, rehydration, cage mass and “bully kg” over the class limit.
- Nutrition menu exposes progress and lets player choose fight weight strategy.
- Brutal-cut preparation coefficient adjusted from 0.012 to 0.0125 to keep the legacy “discipline matters strongly” invariant.

### `economy.py`, `systems15.py`, `cut.weekly_costs()`

- `economy.weekly_breakdown()` is now the sole recurring ledger.
- `cut.weekly_costs()` applies that ledger to actual cash, rather than displaying one model while deducting another.
- Side job is not passive weekly income; manager cut is not a weekly expense. Sponsor retainer is passive and credited.
- Added explicit debt repayment. Negative cash becomes debt once; wallet returns to zero.
- Loan UI shows cash/debt/net and offers repayment choices; borrowing has a cap.

### `events.py`, `ai.py`, `data/events_v125.json`

- 36 new events: media 12 / nutrition 8 / money 6 / sponsor 5 / career 5.
- Baseline event trigger chance reduced 0.22 -> 0.18.
- Consecutive same-category events receive a multiplicative selection penalty.
- `balanced_event_effects()` caps one random card's money/fame/rep/follower/stat magnitude by career stage. This is a runtime guardrail over historical JSON, not a rewrite of the old content.
- Debt is now a valid currency-scale event effect. One new debt event actually repays debt instead of merely subtracting cash.

### `ui.py`, `fights.py`, `app.py`, `career.py`

- Added `continue_prompt()` that attempts actual input even on non-TTY phone consoles; catches EOF in headless runs.
- Long events, competition/calendar information and Timeline/Money use it.
- Visible dead G lifestyle option removed.
- Manual media menu stays unexposed; the old function remains in code to minimize destructive cleanup in this junior patch.
- Supplement-company sponsorship grants free legal supplements. Current detection is name/keyword-based and is explicitly a senior-review candidate for metadata tagging.

## Validation actually performed

Passed:

- compileall
- `tests_081`, `088`, `09`, `11`, `110`, `12`, `120`, `120x`, `121`, `122`, `123`, `124`, `124_release`, `125`, `13`, `130`, `140`, `15`, `150`, `16`, `160`, `17`, `170`, `18`, `19`, `191`, `192`, `193`
- `tests_125`: 11/11 checks
- supplied v1.24 autosave diagnostic load (read-only) as described above
- reduced `tests_194` clone smoke: Boxing 53%, Wrestling 48%, BJJ 48%, Muay Thai 53%; momentum/combination/TKO/stand-up symmetry source assertions pass

Not completed in this environment:

- full `tests_194` (400 fights x four mirror styles + 400 wrestler-vs-striker) exceeded the execution window. Senior MUST run it before blessing the branch.

## Senior review priorities

1. Run `python -m mma_legend.tests`, `python -m mma_legend.tests_194`, `python -m mma_legend.diagnostics` from the extracted ZIP.
2. Re-evaluate UFC title gate values (3 UFC bouts / 2 wins / top 3 / +2 streak). The architecture is fixed; exact thresholds are a design choice.
3. Inspect the runtime global event caps. They solve observed imbalance cheaply, but a future content pass may prefer hand-tuning historical cards.
4. Replace supplement-sponsor keyword detection with sponsor metadata/capabilities if you want a durable sponsorship system.
5. Review debt interest balance (currently inherited ~1.2% weekly); transaction/display bugs are fixed, interest tuning is not claimed.
6. Playtest all three weight strategies across divisions. “Weight bully” should grant cage size only by accepting more final-cut risk/gas cost, never a hidden flat damage buff.
7. Consider deleting the now-unexposed manual `social_media_menu()` only after confirming no event/story path calls it.
8. Continue using old saves strictly for bug reproduction. Do not preserve old-save behavior if it conflicts with a stable new career.

# MMA Legend — Developer Version History / Handoff Ledger

This file is the **developer-to-developer continuity record**. `CHANGELOG.md` is
player-facing; this document records why changes were made, what code paths were
touched, how they were validated, and what the next developer should distrust or
re-check.

## Working rules for future sessions

- **Last senior-stable baseline:** 1.25.1 — senior-corrected 1.25 integration, playtest intelligence and economy/event hardening.
- **Reviewed candidate:** 1.25.0 — junior fixes from the v1.24 human playtest; accepted only after the 1.25.1 corrections above.
- **Baseline received:** 1.21.0 Phase 1 Checkpoint, produced in ChatGPT Work mode.
- **Save policy:** old/supplied saves are diagnostic and balance fixtures only. Do
  **not** preserve old-save compatibility at the cost of engine stability. Do not
  ship reference/debug saves in release ZIPs. `make_zip.py` already excludes the
  standard save filenames.
- **Save schema:** still JSON v11. 1.22 adds no required persisted fields and does
  not need a schema bump.
- **Release gate:** `python3 -m mma_legend.tests`, then diagnostics and balance lab.
  New versioned test modules must remain discoverable by `mma_legend.tests`.
- **Balance rule:** do not tune combat globally because a career probe looks bad.
  First separate engine fairness, opponent generation, progression and the probe's
  own assumptions.

---


# 1.24.0 — combat physiology / playtest forensics / career intelligence

This section records the completed 1.24 release. It sits on top of 1.23 Phase 3 and closes the physiology, weight/nutrition, combat-integration and playtest-forensics work. The supplied 1.23 playtest saves are used
strictly as diagnostic evidence and are not copied into the branch or treated as
compatibility targets.

## Playtest evidence received

Three week-205 snapshots of Francisco Ferrari exposed state divergence that could not be
explained from the old save header alone:

- `save.json` and `save_auto.json` contained only 520 NPCs while the manual slot contained
  the full 907-NPC world. Their debug header still claimed `pool_n=907`.
- The autosave/default snapshot was taken before post-bout perk/career bookkeeping:
  `ko_losses=1`, `td_career=0`, `body_shots=1`, one perk. The same-week manual snapshot
  had `2 / 1 / 7` and the newly granted `glass` perk.
- The player was 0-2 professionally but #1 on the Balkan Combat board and stored
  `prospect`, `pro`, `contender`, `journeyman` and `title_contender` simultaneously.
- The exclusive Balkan Combat contract stored `$0/$0` terms.
- Existing fight history has no chronological exchange trace, AI rationale, displayed
  menus or screen transcript, making several KO/TKO rows impossible to explain from the
  final stats alone.
- `performance_rating` is present in the fight ledger but all supplied career rows use
  `0.0`; it is currently not a meaningful telemetry signal.

## Root causes and high-confidence fixes

### Canonical autosave / post-fight finalization

`persistence.autosave()` no longer trims the world to 520 fighters. Autosaves now write
compact JSON but serialize the **full live pool**, so loading an autosave cannot silently
turn one universe into a smaller one.

Autosave ownership was moved out of the middle of `fights.fight_result()`. Perk bout
counters/evaluation now finalize before the caller writes the canonical post-bout save.
This prevents quitting after a fight from restoring pre-perk/pre-counter state.

`perks.grant()` no longer overwrites `last_week_note` with `perk X`; it records
`story_flags.last_perk` instead.

### Résumé-first rankings and story identity

`world.FighterPool._rank_score()` was rewritten so professional results, recent form and
activity dominate. Hidden skill/fame are small tie-breakers rather than a way for a 0-2
fighter to become promotion #1.

`story._can_start()` gained pro-specific gates (`min_pro_wins`, `max_pro_losses`,
`requires_pro`, `max_org_rank`). The title-buildup chain now requires an actual pro résumé
and a top-four promotion rank. The old total/amateur-wins shortcut is removed from that
chain.

Stored historical tags remain available for event history, but `story.career_label()`
derives the **current** displayed identity from pro record/rank/belt. Weekly news no
longer dumps contradictory append-only tags as if they were simultaneous current roles.
The turn-pro chain now ends with `pro`, not an unconditional `journeyman` label.

### Matchmaking intelligence

Early professional matchmaking now uses both win gap **and total pro-bout experience**.
A 0-1/0-2 prospect can no longer pass the old loose rule and be fed a 6-0 opponent simply
because the veteran has fewer than eight wins.

Named promotion cards now select same-org fighters first, then true free agents. A
fighter assigned to a rival promotion is no longer silently borrowed for local/regional
cards. If a live roster cannot supply a legal opponent, the generated emergency opponent
is registered to the card's promotion.

### Contract intelligence

`orgs.sign_org()` now fills realistic baseline win/show purse terms when a direct-sign
path does not supply them. Individual bout offers can still negotiate above the contract
baseline, but exclusive contracts no longer store `$0/$0` by default.

## New playtest telemetry

New `mma_legend/telemetry.py` records a bounded in-save tail plus an append-only,
size-rotated `playtest_trace.jsonl` during a real human session.

It captures:

- active screen/header and exact ANSI-stripped lines rendered to the player;
- prompts and the player's actual input;
- fight-plan choices;
- event-AI trigger probability/roll, eligible-event count and highest weighted events;
- matchmaking candidate counts, candidate summaries and selected opponent;
- fight start/end context;
- each real-player-fight exchange: requested vs legal fallback action, position/role,
  target, hit chance, RNG roll, damage, gas before/after, momentum, control and body map;
- fight AI action selection reason (`signature`, learned-technique bag or weighted pick)
  plus top action weights;
- save phase/path/world count.

Headless balance simulations do **not** write per-action telemetry; combat telemetry is
gated behind `begin_fight()` so regression/fairness labs remain fast.

Every save now embeds a top-level `playtest` snapshot. Debug metadata distinguishes
`world_pool_n` from `saved_pool_n`.

### One-file playtest export

The save menu gains `P) Export playtest bundle`. It creates
`MMA_Legend_playtest_bundle.zip` containing:

- `playtest_snapshot.json` — fresh canonical full-world save;
- `playtest_summary.json` — debug header + automatic contradiction audit + recent trace;
- `playtest_trace.jsonl` (and rotated previous trace when present);
- `debug_log.txt` when present.

Reference save slots are deliberately not bundled.

### Automatic contradiction audit

`diagnostics.audit_playtest_state()` flags high-signal states such as:

- winless early pro ranked at/near promotion #1;
- premature title-contender identity;
- fragmented career-role tags;
- zero-purse exclusive contract;
- official-record vs detailed-ledger gaps (informational because legacy/pre-ledger fights
  can legitimately exist);
- KO/TKO ledger rows with no knockdown/times-down evidence;
- suspiciously small loaded world pools.

## Regression evidence so far

Historical suites through `tests_194` remain green after these changes. The new
`mma_legend.tests_124` also passes seven dedicated checks:

1. 0-2 high-skill/fame fighter cannot outrank a 2-0 résumé;
2. early-pro experience band rejects a 6-0 feeding matchup;
3. exclusive cards do not borrow rival-org fighters;
4. emergency roster fill joins the card's promotion;
5. direct contracts receive non-zero terms;
6. autosave serializes the full live world;
7. playtest bundle contains exact recent UI/input evidence and the contradiction audit
   recognizes the supplied-playtest-shaped state.

`python -m mma_legend.diagnostics` remained `ALL SYSTEMS OK` before the release bump; after the final metadata bump it must report **1.24.0**. The package is only valid after extraction/retest.

## Release completion / validation

Closed before packaging:

- nutrition/body-composition is consolidated around structured plan metadata;
- hard/brutal cut Monte Carlo now has preparation-sensitive miss risk;
- physical caps are enforced through training/camp/story gain paths;
- earned perks feed small real gameplay modifiers;
- `performance_rating` is a defined 1-10 observable bout grade;
- fame/sponsor scale is coherent (fame 0-100; major brands require pro résumé + audience);
- manager advice describes concrete matchmaking/recovery objectives;
- generated playtest traces/snapshots are excluded from the release archive;
- historical legality/damage/contract/event suites and strict clone fairness are green.

Representative 1.24 validation:

- hard-cut miss Monte Carlo: ~22-26% for an ~11% cut vs ~0% routine under the QA fixture;
- brutal 84kg -> Lightweight cut: sloppy camp ~1-2% make rate vs disciplined ~44-50%;
- clone fairness: Boxing 47%, Wrestling 54%, BJJ 50%, Muay Thai 50%;
- wrestler vs Muay Thai viability: 61% in the dedicated 1.19.4 fixture;
- event database remains 451 cards and phone-width validation remains green.

Known follow-up: the simplified `persona_careers()` probe historically reports low player career win rates while controlled combat is fair. Continue treating that as matchmaking/progression/tooling telemetry work, not evidence for a global player combat buff.


# 1.23.0 — Phase 3

## Goal inherited from the three-phase plan

1. Add a substantial set of contextual events for wins, losses, injuries, camps,
   money, gyms, teammates, family, media and career progression.
2. Run complete regression, large combat/fairness samples, event validation and
   phone-width checks.
3. Load supplied/reference saves only as diagnostic fixtures and do not mutate them.
4. Update documentation/version history and package a clean phone-ready release.

Phase 3 deliberately starts from the 1.22.0 Phase-2 ZIP. No old save was used as
the development baseline and no compatibility concession was made for an old save.

## Files changed

### `mma_legend/data/events_v123.json` — new

Added **60 contextual events**, exactly six in each `phase3_group`:

- `wins` — streak pressure, regional buzz, tactical consolidation, rising expectations,
  spending after a purse, opponents studying successful patterns;
- `losses` — post-loss reflection, coach tape review, losing-streak reset, veteran advice,
  close-loss emotion and career-pressure decisions;
- `injuries` — scan bills, rehab monotony, teammate support, family concern, cautious
  return-to-movement and learning around limitations;
- `camps` — specialist details, extra hard rounds, homesickness abroad, recovery choices,
  opponent film study and foreign-room networking;
- `money` — low cash, debt pressure, equipment choices, larger purses, teammate loans and
  the hidden costs of being a professional;
- `gyms` — coach relationship quality, gym tension, equipment improvements, inter-gym
  reputation, shared expenses and difficult specialty-room matchups;
- `teammates` — requested rounds, corner duty, wins/losses around the room, sparring
  tension and technical knowledge sharing;
- `family` — time away from fighting, fatigue concern, household money, schedule support,
  visible damage and emotional support during losing streaks;
- `media` — viral clips, rivalry framing, hometown features, bad sparring clips, podcasts
  and increased cameras during a streak;
- `career` — first pro win, ranking talk, manager leverage, promotion scouting, contender
  pressure and veteran/mentor status.

All new choices use explicit A/B keys. New event text is written to fit the same mobile
voice as the existing packs and uses only effect fields that the engine actually applies.

### `mma_legend/data.py`

Loads `EVENTS_V123` and appends it to `event_packs()`, bringing the current database
from 391 to **451 events**. `newest_first=True` naturally puts the pack at the front of
the candidate list without creating a second event-selection path.

### `mma_legend/events.py`

**Context DSL expansion using existing persisted state only.** `context_pack()` now
exposes:

- `camp` (normal OR international), `intl_camp`, `booked`;
- signed `streak`;
- `followers`, `debt`, sponsor count;
- teammate name/presence, manager presence, specialty-gym presence;
- named organization;
- relationship map.

`eligible()` now supports declarative requirements for those values:

- boolean `camp`, `intl_camp`, `booked`, `teammate`, `manager`, `gym`;
- `org` as presence boolean, exact string or allowed list;
- min/max streak, followers, debt and sponsor count;
- min/max family/friends/coach/partner/rival relationship values.

No Fighter field was added, so **SAVE_VERSION remains 11**.

**Validator upgrade.** `validate_event_pack()` previously checked only missing/duplicate
IDs. It now also detects:

- unknown requirement keys;
- contradictory min/max ranges;
- an event requiring both pro and amateur;
- invalid/non-0..1 trigger chances;
- unknown effect keys / invalid relationship effect targets;
- missing choice labels and duplicate explicit choice keys.

This matters because malformed event JSON previously tended to fail silently as dead
content rather than crash.

**School-token regression fixed.** The old school gate used substring matching. The word
`upgrades` therefore contained `grades` and could make an unrelated event school-only.
School keywords now use word-boundary matching. This bug was discovered by the new
reachability test, not by manual play.

**Phone rendering.** `handle_event()` now wraps the event title, description, context
line, base effects, every choice label and selected-choice effect summary. Width access
uses a 44-column fallback so lightweight historical console stubs remain compatible.

`_fill()` also supports `{teammate}`, `{org}` and `{streak}` placeholders.

### `mma_legend/tests_123.py` — new

Release-focused Phase-3 suite verifies:

1. 60 new events / ten groups / six per group / 451 total events;
2. strengthened DSL validator returns no issues;
3. **every one of the 60 new events is reachable** in at least one synthetic but plausible
   career context;
4. context gates really reject mismatched streak/teammate state;
5. the `upgrades` school-substring regression stays fixed;
6. every one of all **451 event cards** renders at <=44 columns;
7. conditional new-pack weight stays contextual rather than dominating older content;
8. teammate placeholders resolve to the actual teammate name.

Representative new-pack conditional shares from the deterministic test:

- rising amateur: 9%
- hurt/post-loss amateur: 12%
- pro prospect: 10%
- contender: 15%
- international camp: 9%

### `mma_legend/tests_121.py`

The 1.21 regression had an exact global event-count assertion (`== 391`). That is no
longer a valid historical invariant once a later release adds content. It now preserves
the actual 1.21 invariant (`EVENTS_V121` remains 30), requires the total to be at least
391, and still requires every current pack to validate. The exact current count lives in
`tests_123.py`. No behavioral regression assertion was removed.

### Version/documentation files

- `mma_legend/constants.py` -> 1.23.0
- `README.txt` -> 1.23.0 title/folder paths
- `SYSTEM_MAP.md` -> 451 events + current DSL source of truth
- `ARCHITECTURE.md` -> Phase-3 event architecture and validation contract
- `CHANGELOG.md` -> player-facing 1.23.0 summary
- `VERSION_HISTORY.md` -> this handoff record

## Validation performed for 1.23.0

### Full regression discovery

`python3 -m mma_legend.tests`

Result: **26 versioned test modules discovered; `FAILED MODULES 0`.**

### Diagnostics

`python3 -m mma_legend.diagnostics`

Pre-version-bump diagnostic result was **ALL SYSTEMS OK** with:

- 451 events;
- headless amateur / pro / no-gi combat;
- save -> load round trip;
- people system;
- booking pipeline.

A final post-version-bump diagnostic is required at packaging and should report v1.23.0.

### Large combat sample

`balance.report(500)` = 2,000 canonical benchmark fights:

- amateur equal: player W 49%, KO 16%, TKO 15%, SUB 9%, DEC 60%;
- pro equal: player W 49%, KO 17%, TKO 19%, SUB 9%, DEC 55%;
- elite equal: player W 48%, KO 50%, TKO 27%, SUB 4%, DEC 19%;
- age 36 vs 24: older player W 43%, KO 14%, TKO 19%, SUB 9%, DEC 57%.

Separate clone fairness, 600 fights/style = 2,400 fights:

- Boxing 50% player-slot wins;
- Wrestling 53%;
- BJJ 49%;
- Muay Thai 52%.

Conclusion: Phase 3 does **not** change combat constants. Slot fairness remains healthy.
The elite all-78 fixture is still finish-heavy, as documented in 1.22; do not use that
artificial fixture alone to nerf finishing.

### Persona-career probe remains suspect

A 30-person / 52-week run produced amateur 35-205 (15%) and pro 26-119 (18%).
This reproduces the known mismatch while controlled equal fixtures stay around 50%.
Treat this as evidence that the simplified probe/opponent assumptions differ from the
real career pipeline, **not** evidence for a blanket player combat buff. A future tooling
pass should replace this probe with real booking/progression telemetry rather than tune
the engine around it.

### Reference-save diagnostic load

Two supplied/reference fixtures (`save.json` and `save_auto.json` from the Phase-1 audit
workspace) were loaded with the current loader. Both returned a player + world pool and
the source SHA-256 was identical before and after load. They were **not edited, migrated
in-place or copied into the release tree**.

This confirms they remain useful debugging fixtures. It is deliberately **not** a promise
that future releases preserve compatibility with them.

## Handoff notes for the next developer / Work session

1. Start from **1.23.0**, not 1.22 or 1.21. Phase 3 is implemented.
2. Keep `events_v123.json` as one data pack; do not duplicate these 60 cards into older
   packs.
3. When adding a new `require` key, implement it in `eligible()` and register it in
   `validate_event_pack()` in the same change. Unknown JSON requirements should remain
   release failures rather than silent no-ops.
4. Keep the every-event reachability test. It caught a real historical substring bug.
5. Do not weaken the 44-column all-event render test when adding longer prose; wrap the
   UI or shorten the content instead.
6. New event volume should be measured against old packs. Do not solve repetition by
   blindly increasing weekly event hunger; quiet weeks are intentional.
7. `camp` in event context now includes international camps. Use `intl_camp` when a card
   specifically requires travel abroad.
8. The persona career probe is still a known bad signal. If investigating career
   difficulty, instrument the real matchmaking/booking pipeline: opponent rating gap,
   age/experience gap, fight frequency, training growth, purse/camp affordability and
   actual player decision strategy.
9. Supplied saves remain reference fixtures only. Do not ship them and do not distort a
   new schema to keep them alive.

# 1.22.0 — Phase 2

## Goal inherited from the three-phase plan

1. Add a phone-safe body-damage map to the live fight HUD.
2. Make smarter fighters deliberately exploit injured/damaged targets.
3. Raise overseas camp prices according to room quality and expected reward.
4. Clean up dashboard, menus, fight text and overlong phone lines.
5. Rebalance combat only if simulations show a clear engine problem.

The 1.21 checkpoint already contained first-pass implementations for several of
these bullets. 1.22 treats those as prototypes and closes the behavioral gaps.

## Files changed

### `mma_legend/damage.py`

**Added** `BodyMap.worst_leg()`.

Reason: 1.21 reduced both legs to `max(lead_leg, rear_leg)` for AI decisions and
the HUD. The fight engine therefore knew one leg was bad but not which leg to
attack.

**Extended** `BodyMap.hit()` to accept `lead_leg`, `rear_leg`, and `cut:<zone>`
target hints while keeping legacy `leg`, `body`, and default head behavior.

**Added** `BodyMap.worsen_cut(zone, action, dmg)`.

Reason: a smart fighter targeting an existing cut should worsen that cut, not
roll a completely unrelated random brow/cheek cut. The worsening amount is
intentionally modest and still probabilistic to avoid doctor-stoppage spam.

### `mma_legend/engine/fight.py`

**Added** `_damage_target_hint(action, body, fight_iq)`.

Behavior:
- low kick + visible damage + IQ >= 55 -> target the worse lead/rear leg;
- body attacks -> explicit body target;
- sharp head attacks + existing cut >= 45 + IQ >= 62 -> target that cut;
- ordinary head attacks -> head.

**Kept** `_damage_hunt_weight()` as the action-selection layer. 1.22 therefore
uses two distinct tactical steps:

1. *Should I choose an action that attacks this weakness?*
2. *If I chose it, where exactly should I aim it?*

That distinction is important. 1.21 mostly implemented step 1.

**Persistent damage exploitation:** between-fight `fighter.damage` now also
increases low-kick interest for damaged legs and accurate head-strike interest
for existing cuts. Existing body/head/takedown vulnerability weighting remains.
This lets AI notice weakness before the current fight's `BodyMap` has built up.

**Cut behavior:** if an AI-selected target is `cut:<zone>`, a landed sharp strike
has an elevated chance to worsen the same zone. Generic sharp head strikes still
retain the old chance to open a fresh random cut.

**Commentary:** rear-leg low kicks can be described as rear-leg attacks rather
than always claiming the lead calf was chopped.

**No blanket combat constants changed.** Base accuracy, damage, KO probability,
submission probability and scoring constants were deliberately left alone.

### `mma_legend/ui.py`

**Fight HUD:** keeps the familiar `H/B/L/C` summary and appends `L/R` detail.
Example:

    H12 B34 L76 C44 · L/R18/76

`L` remains the worst-leg value for fast scanning; `L/R` reveals which leg is
actually compromised. The line remains under the 44-column phone target.

**Fight feed:** long commentary now wraps while preserving `>` / `<` actor
prefixes and event tags (`TD`, `KD`, `CUT`, etc.).

**Menus:** `menu_table()` wraps descriptions under the action name instead of
letting a long description run off-screen.

**Text wrapper:** `wrap_text()` now splits pathological long tokens, so one huge
ID/compound token cannot bypass width guarantees.

**Status messages:** `good()`, `warn()`, `info()`, `gold()` and `milestone()` now
use a shared width-safe status renderer with aligned continuation lines.

**Dashboard:** rewritten around decision priority rather than subsystem count.
Panels are now:
- `CAREER` — identity, record, org/phase, body, money/fame/week, rank;
- `RIGHT NOW` — booked fight, camp, medical state, opportunities, people,
  progression and life warnings;
- `CONDITION` — energy/health/nutrition/mood/confidence bars.

The information was grouped rather than simply deleted. Low-priority state no
longer consumes one line per subsystem.

**Bug fixed:** overseas trips use `intl_camp_weeks`, while normal fight camps use
`camp_weeks_remaining`. The old dashboard read the normal camp counter for an
international camp and could display the wrong remaining duration.

### `mma_legend/camps.py`

Replaced manually maintained camp prices with `_quoted_cost(spec)`.

Inputs to quote:
- weeks away;
- quality (1-5);
- count of rare techniques;
- network upside (1-5);
- destination travel premium/discount.

The derived `spec["cost"]` field is still populated at import time so existing
callers do not need an API migration.

Current quotes:
- Bishkek — $3,900
- Phuket — $4,800
- Makhachkala — $5,200
- Rio — $5,200
- Las Vegas — $6,200

Pricing is intentionally much higher than the original 1.19/1.21 values because
these camps grant multiple weeks of stat growth, rare techniques and persistent
career connections. Early-career fighters should have to save, borrow, or wait.

`preview()` now exposes `quality`, `network`, and `reward_count` for UI/tests.

### `mma_legend/career.py`

The overseas-camp menu now displays price, quality, network value, focus and
rare-technique reward in wrapped phone-safe lines.

### `mma_legend/events.py`

**Stability hotfix discovered during Phase 2 audit.**

1.21 correctly stopped blank event input from silently choosing A, but it only
matched an explicit `choice["key"]` or the full label. Older event packs embed
keys in labels (`"A) Take a week off"`) and have no key field, so typing `A`
produced no effect.

1.22 choice resolution now:
1. uses explicit `key` when present;
2. otherwise parses a leading `A)`, `B.`, `C-`, etc.;
3. otherwise assigns the choice's index letter;
4. still treats blank input as no choice.

This is intentionally included in 1.22 rather than pretending the supplied
Phase-1 checkpoint was flawless.

### `mma_legend/tests_122.py`

New regression suite covers:
- exact damaged-leg targeting;
- cut targeting and same-zone worsening;
- both-leg HUD visibility and 44-column width;
- long fight feed, menu description and long-token wrapping;
- compact dashboard and correct overseas-camp clock;
- reward-derived camp prices;
- legacy event `A/B/C` input;
- equal-pro combat guardrail after tactical AI changes.

### Version/documentation files

- `mma_legend/constants.py` -> 1.22.0
- `README.txt` -> 1.22.0 run paths/title
- `SYSTEM_MAP.md` -> current version 1.22.0
- `CHANGELOG.md` -> player-facing 1.22.0 summary
- `VERSION_HISTORY.md` -> this handoff ledger

## Validation performed for 1.22.0

### New Phase-2 suite

`python3 -m mma_legend.tests_122`

Result: all Phase-2 checks pass.

### Full historical regression + diagnostics

- `python3 -m mma_legend.tests` -> `FAILED MODULES 0`
- `python3 -m mma_legend.diagnostics` -> `RESULT: ALL SYSTEMS OK`
- Diagnostics reported version `v1.22.0`, 391 events, save/load OK, and booking pipe OK.

### Balance lab after tactical changes

Representative 300-fight run:

- amateur equal: player win 50%, decisions 60%
- pro equal: player win 45%, decisions 55%
- elite equal: player win 42%, decisions 23%
- age 36 vs 24: older player win 45%, decisions 57%

The existing dedicated clone-fairness suite continues to put Boxing, Wrestling,
BJJ and Muay Thai mirrors around the 50/50 region. Phase 2 therefore does **not**
apply a global combat-number rebalance.

The elite fixture still finishes very often. That fixture has elite stats across
several finishing attributes and is not enough evidence by itself to lower all
finish rates. Revisit only with promotion/skill-tier telemetry from real career
matchups.

### Known questionable probe — do not tune combat around it

`balance.persona_careers()` still reports roughly 10-17% player win rates in its
simplified career loop. Earlier inspection showed that probe generates opponents
with assumptions that do not mirror the real matchmaking/progression pipeline.
Treat this as a **Phase 3 validation/tooling investigation**, not proof that the
fight engine needs a player buff.

## Handoff notes for the next developer / Work session

1. **Do not re-implement Phase 2 from the plan text.** Check this file first;
   several bullets existed in prototype form in 1.21 and were completed here.
2. Start Phase 3 from 1.22.0, not from the old 1.21 checkpoint.
3. Preserve `_damage_hunt_weight()` vs `_damage_target_hint()` as separate
   concepts unless there is a strong reason to redesign tactical AI.
4. If adding stance switching, migrate `lead_leg/rear_leg` semantics carefully.
   Right now they are stable fight-side labels, not dynamically swapped stance
   anatomy.
5. If adding new foreign camps, set `quality`, `network`, `travel_premium`,
   `weeks`, `focus`, and `teaches`; let `_quoted_cost()` derive the price.
6. If changing camp rewards, update the pricing formula or reward metadata so
   price and reward cannot drift apart again.
7. Do not remove legacy event-key parsing until all event JSON packs have been
   migrated to explicit `key` fields and validated.
8. Phase 3 should run broader UI-width probes across non-fight screens. Phase 2
   fixed the shared/high-frequency paths, not every historical hand-written
   `console.print()` string in the project.
9. Supplied old saves may be loaded to reproduce bugs, but they are not release
   compatibility contracts.

---

# 1.21.0 — Phase 1 checkpoint received from Work mode

This was the input baseline for the 1.22 work. The supplied changelog describes
it as stabilization plus first-pass tactical damage/event/UI work.

Important baseline facts confirmed before Phase 2:
- historical test discovery worked;
- all existing test modules were green;
- diagnostics were green;
- one-year/one-birthday progression was fixed;
- duplicated recent fight results were fixed;
- action timing/menu reroll protections existed;
- locational injuries and healing were integrated;
- 391 events were loaded/validated;
- first-pass H/B/L/C HUD and action-level damage hunting existed;
- overseas camp prices were $1,800-$4,200;
- first-pass dashboard cleanup existed.

**Regression found after handoff:** legacy event labels without explicit keys
could no longer be selected by typing a single letter. Fixed in 1.22.0 and
covered by `tests_122.py`.

For older history, see `CHANGELOG.md`, `ARCHITECTURE.md`, and `SYSTEM_MAP.md`.


## 1.31.0 — Part 1: simulation and career correctness
- Reconciled side-sport national-team state from National silver/gold medals and repaired international championship eligibility for legacy saves.
- Rebuilt fight-week weight resolution: scale weight never exceeds walking mass, under-limit/heavyweight athletes do not receive fictional dehydration cuts, and legacy bully campaigns are repaired.
- Audited supported amateur sport structures and corrected current Boxing/Kickboxing period structure plus Judo/Combat Sambo upper-weight labels.
- Expanded fight strategy influence and NPC tactical adherence, and reworked takedown selection/resolution around entries, setups, defense, fatigue, range and technique.
- Removed broad Sambo/Judo/BJJ concept-techniques from playable technique data, migrated legacy saves, and added named throws, passes, sweeps, escapes and submissions.
- Eased BJJ/Judo belt progression while keeping mat-time and grading requirements, fixed discipline-aware belt display, and made belt ownership/mat progression single-owner.
- Locked hometown gym/coach access during international camps and added camp-specific training beats and skill development.
- Repaired promotional-offer acceptance so normal named-promotion offers create a real contract instead of a disconnected one-fight booking.
- Added contextual weight-event gating so cut/bully stories require an actual booked cut.

---

# 1.32.0 — Part 2: career depth and presentation

Built directly on the validated 1.31.0 Part 1 branch. The goal of this pass is not to alter the newly repaired fight/sport/weight rules again, but to make the surrounding career loop readable, persistent and worth interacting with.

## Career-life persistence repair

Several long-running systems wrote dynamic attributes (`timeline`, `side_job`, international-camp metadata, `connections`, `last_ledger`, notes/injury history). `Fighter.from_dict()` accepts declared dataclass fields only, so those values could silently disappear on reload. 1.32 declares them explicitly and adds persistent job progression/history while keeping save format v17.

## Side jobs

Ten jobs now occupy different economic niches: delivery, waiter, warehouse, construction, security, bouncer, lifeguard, martial-arts assistant, personal trainer and private combat coach. Jobs have visible pay, fatigue, risk, prerequisites and secondary effects. Reliability creates modest raises; physical/teaching exposure progresses slowly rather than replacing training. International camps block home shifts.

## Timeline and event identity

The timeline is now a view over authoritative fight history rather than a competing record writer. Amateur and professional fights render separately, sport identity is retained, and available strike/takedown/knockdown/control/submission statistics plus performance rating are shown. New ledger rows retain career week.

Promotion cards now receive stable series identities when built: `<Promotion> N` for numbered/title cards and `<Promotion> Fight Night N` for ordinary cards. Event identity, series and number persist into completed history and the player's fight ledger. Existing unnamed scheduled/history cards are labelled once when migrated.

Cards are deeper: major organizations can schedule up to nine bouts, smaller promotions up to seven, with main event, co-main, main-card and prelim slots rather than four anonymous bouts.

## UI/event pacing

A choice is now its own acknowledgement. Choice events resolve immediately instead of asking for Enter again. Information-only screens keep deliberate acknowledgement. A spent career week receives one explicit week-boundary prompt before the next dashboard appears.

Fight-plan templates now expose predicted simulation behavior so strategy is legible before the fight starts. International-camp status screens explain active focus, teachable techniques and which home systems are locked.

## Context cleanup

Legacy event packs receive additional narrow contradiction guards for partner-specific text without a partner, contract-renewal text without a contract, title-defense text without a championship and international-camp text while at home. This complements Part 1's cutting/heavyweight and school/camp gating.

## Validation

See `RELEASE_AUDIT_1.32.0.md`. Save format remains JSON v17.


# 1.35.0 — UI / QoL Part 2

Built on 1.34.0 Part 1. This release completes the two-part usability milestone without replacing the combat/world simulation architecture.

## Orientation and navigation
- Main menu redesigned for Continue-first play.
- Career is now the canonical information hub with a one-screen overview and unified calendar.
- Booked fights become a dedicated Fight Prep phase instead of a passive status screen.

## Onboarding
- New topic-based Learn/Guide menu.
- Optional guided first four decisions; tips never block alternative actions.
- Contextual `?` help in the weekly loop.

## Fight UX
- Matchup-aware coach gameplan recommendation, tactical card, remembered preferred template and saved watch-mode default.
- Consolidated post-fight result/stat/career-impact card.

## Long-career QoL
- Timeline overview + filters/paging.
- Per-career compact dashboard and week-report preferences.
- New UI fields remain inside Fighter's declared schema, so save format stays v17.

