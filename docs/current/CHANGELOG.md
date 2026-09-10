## 1.42.0 — Taekwondo & Kicking
- Added Taekwondo as a full side sport/Olympic pathway with WT-style kyorugi rounds, weight classes, legal technique set, technical scoring and round-win resolution.
- Added Taekwondo starting background, NPC/quick-play style support, three dojangs and automatic Taekwondo belt/syllabus development.
- Added nine named Taekwondo techniques plus side/spinning/axe/tornado kick action families shared appropriately with MMA/kickboxing.
- Expanded kick setups, distance effects, low-kick checks, caught body kicks, missed-spin counter windows, leg-damage costs and tactical weighting.
- Added Taekwondo Kicking as a real MMA gameplan and coach recommendation for trained specialists.
- Tightened advanced-kick knowledge gating after a regression audit found untrained spinning attacks inflated MMA finish rates; the historical damage/finish-rate gate is back in range.
- Made world promotion rankings a prominent direct Rankings choice and added Taekwondo belt progress to Fighter presentation.
- Added 18 Taekwondo/kicking events, bringing the authored event library to 565.
- Save schema is JSON v20. Old saves remain reference-only.

## 1.41.0 — Performance, Education & Gym Life
- Integrated the completed v1.40 legal supplement / anti-doping engine and structured secondary-school / university systems into the full release.
- Save schema is JSON v19. Fighters under 18 are hard-clamped to zero debt/negative cash during upgrade and runtime.
- Rankings now includes a world browser for every named promotion and every weight class, even when the player is unsigned or amateur.
- Specialist BJJ, Judo and Kickboxing/Muay Thai memberships now develop automatically each home week: mat time, grading points, named-technique learning/mastery and very slow discipline polish.
- BJJ/Judo belts promote automatically when the existing mat-week + grading-point requirements are met. Leaving a gym never deletes earned belts, stripes or techniques.
- International camps pause home-specialist development, preventing double training across locations.
- Rebuilt specialist-gym data with 10 rooms/dojos and valid named technique syllabi.
- Added 36 context-gated gym/education events (BJJ, Judo, Kickboxing/Muay Thai, school and university), bringing authored event count to 547.
- Added gym progress/syllabus views and concise specialist status in Team/Fighter screens.
- Training retains live current skill values beside each focus.
- Added v1.41 regression coverage for world promotion boards, automatic gym learning/belts, camp exclusion, technique legality, event validation and v19 persistence.

## 1.39.0 — Combat Intelligence
- Added bounded live tactical intelligence driven by Fight IQ, adaptability, discipline, confidence/composure and actual observed fight patterns.
- NPC opening plans are matchup-aware; automatic fighters and corners adjust between rounds for failed wrestling, repeated entries/kicks, score urgency, gas and live damage.
- Damage now changes action selection: fighters protect compromised weapons and intelligently attack damaged legs/body/head/cuts.
- Rebuilt stuffed-shot chaining into a real clinch-to-secondary-takedown sequence instead of a cosmetic clinch entry.
- Rebuilt scrambles as contested, position-specific exchanges that can reach stand, half guard, side control or back control.
- Scouting is layered by opponent read/camp readiness; low scouting no longer exposes exact hidden ratings.
- Added tactical booked-fight camp focuses: Anti-Wrestling, Submission Defense and Pressure & Entries alongside Striking/Wrestling/Cardio/Complete.
- Fixed completed camps erasing opponent-specific preparation before fight night.
- Added transient action/result telemetry to FightOutcome for strategy-adherence and combat-AI audits.
- Old saves are reference fixtures only; compatibility was not used to constrain v1.39 design.

## 1.38.0 — Living Careers
- Added `living_careers.py` with persistent NPC career personality/goal state.
- Career goals now influence NPC weekly intent, promotion transfers and card matchmaking.
- Added promotion profiles for merit, star power, prospect protection, activity, matchmaking toughness and regional identity.
- Promotion profiles influence contender/showcase selection and player opponent selection without bypassing existing hard matchmaking gates.
- Eligible player promotion desks are now ranked by résumé, streak, fame/activity, regional fit and existing promoter/matchmaker rapport rather than being mostly shuffled.
- Player offers now expose career opportunity, risk/upside and promotion identity; successful meaningful opportunities give bounded career rewards.
- Preserved existing promotion ownership, contract ownership, ranking logic, event calendars, roster floors and lifetime trilogy ceiling.
- Fixed offer `why` string normalization in AI decoration.
- Fixed the post-offer `X) Back out` path, which could previously loop instead of leaving the decision screen.
- Save format remains JSON v17.

## 1.37.1 — training menu cleanup
- Removed weekly-menu emojis from Train and Amateur.
- Changed the Training focus selector from a dense four-column grid to a vertical one-option-per-line list.
- Changed intensity selection to aligned vertical Light / Normal / Heavy rows with energy and injury-risk information.
- Moved Repeat Last Session and Back below the focus list for cleaner scanning on phone.
- Preserved no-time cancellation at both the focus and intensity stages.
- No training balance or save-schema changes.

## 1.37.0 — UI freeze / polish
- Froze the flat weekly navigation introduced in 1.36; no further hub redesign.
- Reduced weekly emoji use and removed remaining decorative arrow prompt glyphs from the core management flow.
- Made Compact Dashboard functional and added a saved per-career Color preference.
- Added Settings to the secondary weekly Career actions.
- Reworked Fighter into concise career/condition blocks plus grouped Striking, Grappling, Physical and Fight IQ attributes.
- Added concise BJJ/Judo belt state with progress to the next grade.
- Tightened dashboard weight/contract/fight presentation while preserving title, short-notice, cut target and contract-clause information.
- Simplified main-menu/tutorial wording and shortened secondary labels (Fighter, Timeline).
- Kept v1.36 navigation safety: browse-only Team/Life paths do not spend a week.
- Save format remains JSON v17.

## 1.36.1 - Menu cleanup
- Removed amateur fight booking from the weekly Fight action; amateur booking now lives inside Amateur.
- Simplified the weekly menu to action names only and removed the NO TIME labels.
- Replaced decorative symbol icons with a small restrained set of emojis.
- Removed decorative section markers for a cleaner phone layout.
- Preserved navigation safety: browsing/backing out never advances the week.
## 1.36.0 — UI Recovery / Navigation Safety

- Reverted the player-facing weekly navigation toward the older flatter layout after playtest feedback that 1.34/1.35 over-organized the game into hubs. Primary actions are direct again; browse-only career screens are grouped separately.
- Reworked the title screen into Play/System groups and replaced the topic/guided onboarding stack with a short three-page linear How to Play guide. New careers start immediately; `?` remains available in-week.
- Fixed the reported Team browsing bug. The old dispatcher compared the entire serialized fighter before/after opening Team; harmless `sync_techniques()` normalization could therefore mark a full week. Team now returns an explicit time-spent result and only completed training marks `week_kind=full`.
- Coach Advice is now genuinely NO TIME and no longer gives repeatable free Fight IQ/relationship gains.
- Fixed People -> Back being charged as a half-week, School -> Back falling through to "skip class", and Rehab -> Back / opening Rehab without an injury consuming a recovery week.
- Weekly news and manager ticks are presentation-gated to once per actual calendar week, preventing browse-only navigation from re-triggering weekly side effects.
- Simplified the dashboard to identity/record, organization/rank, body/cash/fame, condition and at most a few urgent fight/camp/contract lines. Preserved title, short-notice, cut trajectory and contract-clause visibility.
- Reorganized Life into People and Money/Recovery groups with intuitive keys; removed the old reserved/dead `G` gym path.
- Simplified Nutrition: current body state and plans are visible immediately; the recurring rules wall moved behind `? How weight works`.
- Calendar and Alerts/Inbox are direct NO-TIME weekly shortcuts, preserving useful 1.35 features without requiring the large Career hub.
- ANSI menu colours now remain enabled on iOS Pythonista/Pyto-style consoles that report a non-TTY; `NO_COLOR` and `--no-color` still disable colour.
- Added `tests_136.py` covering Team/Life/People/School/Rehab no-time exits, advice farming prevention, explicit Team time spend and coloured menu rendering.
- Save format remains JSON v17.

---

## 1.35.0 — UI / QoL Part 2

- Reworked the main menu around player intent: Continue autosave, New Career, Load Career, Quick Start, Learn/Guide, Options and Diagnostics. Successful data validation no longer occupies prime title-screen space.
- Replaced the linear seven-page tutorial with topic-based help and an optional non-blocking four-step guided start. `?` now opens contextual navigation help during the weekly loop.
- Added `mma_legend/ux.py` as a read-only presentation/orientation layer. It derives next objectives, career overview, fighter sheet, unified calendar and tutorial hints from authoritative existing state rather than duplicating simulation ownership.
- Expanded Career navigation into overview, fighter sheet, calendar, timeline, rankings, amateur path, nutrition/weight, inbox, finances and interface preferences.
- Added a unified career calendar combining booked fights, registered championships, current camp end, contract expiry and upcoming amateur championship dates.
- Rebuilt a booked fight into a browse-only Fight Prep hub with tale of tape, scouting, camp/weight and purse/contract pages. Browsing cannot silently spend a week.
- Gameplan selection now exposes a matchup-aware coach recommendation and a consolidated tactical card, remembers the player's preferred template, and records the final plan in persistent career UI state.
- Fight watch mode now defaults to the saved preference while still allowing a per-fight override.
- Timeline now opens with a short amateur/pro snapshot, then offers a paged/filterable history browser rather than dumping an entire long career.
- Added a consolidated post-fight summary card with result, core fight statistics, record, money/fame/legacy and recovery state.
- Added per-career Compact Dashboard, Week Report and Guided Start toggles. New fields are schema-owned and save-v17 backward compatible.
- Added `tests_135.py` covering new UI persistence, calendar, guided tutorial progression, gameplan recommendation and no-time fight-prep browsing.

---

## 1.34.0 Part 1 — UI / Navigation QoL

- Replaced the weekly skill wall with a compact decision dashboard.
- Reorganized the weekly action surface around Career, Team, Life, Fight/Inbox, Train and Rest; legacy H/I/N/Z shortcuts remain accepted.
- Added visible time/energy/context tags to weekly actions; labels are rendered with phone-safe parentheses so the legacy markup cleaner cannot erase them.
- Added persistent alerts with a Career inbox; dashboard viewing no longer consumes/clears notifications.
- Added week-end change reports covering money, condition, weight, fame and trained skills.
- Reworked regular training around a fast repeat-last-session path. Invalid/cancelled training no longer drains energy or spends a week.
- Added a persistent mini status strip to high-traffic hubs.
- Removed unreachable legacy coach-hub UI code.
- Save format remains v17 and older 1.33 saves remain loadable.

# 1.33.0 — maintenance, structure and reliability

* Reorganized the project into a clean player runtime (`mma_legend/`), external regression suite (`tests/`), developer utilities (`tools/`) and current/history documentation (`docs/`).
* Removed the redundant `run.py` launcher. `START.py` and `main.py` now launch only the package beside them instead of scanning sibling old-version folders, preventing the wrong installed build from being started accidentally. Desktop users can also run `python3 -m mma_legend`.
* Moved versioned regression modules out of the runtime package. The new `tests.runner` executes suites exposing either `main()` or `run()`, fixing the old discovery bug that silently skipped the entire 1.32 test suite.
* Moved save repair, long-world audit, batch-career simulation and release packaging into `tools/`. Fixed save-repair write mode relying on a global import that existed only under `__main__`.
* Fixed MMA history classification: explicit Combat Sambo, Boxing, Kickboxing, Wrestling and Judo rows are no longer treated as MMA. Legacy untagged rows still use conservative event-name fallback logic.
* Release packaging now filters caches, bytecode, runtime saves, debug logs and playtest traces from any directory rather than relying on a cluttered source tree.
* Removed the unused `mma_legend/rng.py` replay stub; the combat/world engines never imported it and it did not seed live fights.
* Save format remains JSON v17; no gameplay state migration is required.

---

# 1.32.0 — Part 2: career depth, presentation and persistence

* Reworked side jobs into ten distinct jobs with pay/fatigue/risk tradeoffs, prerequisites, slow raises, contextual shift outcomes and job history. International camps correctly block home employment.
* Declared previously dynamic career-life fields on `Fighter` (timeline, side job, job progression, international camp metadata, connections, ledger/notes/injury history), fixing silent data loss through `from_dict()` while keeping save JSON v17 backward-compatible.
* Timeline now separates AMATEUR CAREER and PROFESSIONAL CAREER, shows the record as it develops, keeps sport identity, and surfaces available fight stats/performance ratings. New fight rows store career week.
* Promotions now build persistent numbered or Fight Night event series. Cards carry event name/type/number, larger prelim/main-card structure, and completed histories preserve the same identity. Legacy unnamed scheduled cards are migrated on load/use.
* Professional fight history now records the actual event name (for example `Balkan Combat Fight Night 4`) rather than only the promotion name.
* Event choices no longer require a redundant second Enter press. Information-only cards still pause, while every spent week ends with exactly one explicit `Week N complete → begin Week N+1` prompt.
* Added narrow context guards for impossible partner, contract-renewal, title-defense and international-camp event text without suppressing legitimate introduction events.
* Fight strategy selection now shows the expected behavioral consequences (more shots, more counters, more range control, gas cost, etc.) so the player can see what the simulation is being told to do.
* International-camp presentation now exposes current destination, focus, teachable techniques and the local-system locks while abroad.
* Added `tests_132.py` to protect the new persistence, job, pacing, card-identity and timeline behavior.

---

# 1.31.0 — Part 1: simulation and career correctness

* Reconciled side-sport national-team state from National silver/gold medals and repaired international championship eligibility for legacy saves.
* Rebuilt fight-week weight resolution so scale weight cannot exceed walking mass and under-limit/heavyweight athletes do not receive fictional dehydration cuts.
* Corrected supported amateur-sport structures, current Boxing/Kickboxing period structure, and Judo/Combat Sambo upper-weight labels.
* Strengthened fight-strategy influence and NPC tactical adherence; takedowns now account for entry/setup, range, defense, fatigue and technique.
* Removed broad Sambo/Judo/BJJ concept-techniques from playable technique data, migrated legacy saves, and expanded named throws, passes, sweeps, escapes and submissions.
* Eased BJJ/Judo belt progression, fixed discipline-aware belt display, restricted hometown gym/coach access during international camps, and added camp-specific training beats.
* Repaired named-promotion offer acceptance so it creates a real persistent contract, and added contextual weight-event gating.

---

# 1.30.0 — Stable world intelligence, contracts and career storytelling

## Long-world matchmaking and championships

* Promotion matchmaking now actively creates prospect showcases, gatekeeper tests, contender fights, title eliminators, rebuild fights, activity fights, intentional rematches and title defenses instead of storing unused intent labels.
* Champions are protected from ordinary non-title bookings. Extreme inactivity outranks showcase/story preferences, and severely overdue belts can occupy a second championship slot on a card.
* Recent rematch memory is separate from lifetime meeting history. A pair may form a trilogy but can never silently reopen a fourth fight after old recency data is pruned.
* When a champion has exhausted every local contender through legitimate trilogies, the promotion imports a fresh same-tier challenger rather than freezing the belt or breaking the trilogy rule.
* Lifetime title wins/defenses are stored independently of the capped recent lineage feed so long careers retain Hall-of-Fame and record-book evidence.

## Amateur calendar geography

* Small countries no longer receive artificial Regional Opens. Larger federations retain regional competition where the domestic depth justifies it.
* Continental championships run once per year and route by country: European Championships, Pan-American Championships or Asian Championships.
* Worlds remain annual; Boxing, Wrestling and Judo retain their four-year Olympic path. Player and NPC amateur simulation now use the same continental model.

## Contracts, managers and promoter memory

* Contract negotiation now covers money, fight count, term, clauses and, at eligible smaller promotions, exclusivity. Major promotions may refuse non-exclusive terms.
* Negotiated clauses include short-notice and championship-fight purse escalators plus rematch options; clause bonuses apply to the actual promotion purse.
* Manager negotiation/scouting/career-management competencies, personality and relationship now influence advice and outcomes.
* Added the real persistent promoter/matchmaker memory service. Accepted/declined fights, short-notice help, cancellations, missed weight, difficult negotiations and performance quality can affect future relationships.
* Medical withdrawals and ordinary cancellations are distinguished. Promotions can search for replacements rather than leaving scheduled cards corrupted.

## Scouting and fight preparation

* Opponent scouting can surface real stance, height/reach, record/form, style/tendencies, strengths, weaknesses and commonly used/mastered techniques according to scouting quality.
* Booked opponents feed the camp planner directly. Coaches recommend Striking, Wrestling, Cardio or Complete preparation for an actual matchup instead of asking the player to manually identify the opponent's style.
* Short-notice wins can add fame and promoter goodwill, while declining an emergency opportunity does not unfairly freeze normal matchmaking.

## Fight week, post-event world and legacy

* Major/title fights receive gated fight-week presentation, tale of the tape and a player-facing staredown. Routine low-importance fights do not receive the same ceremony.
* Post-event processing can award contextual performance bonuses, report ranking/title consequences and attach those consequences to the persistent event record.
* Rivalries can now emerge from real bout context including close decisions, rematches, trash talk and relevant gym history.
* Completed-card summaries surface results, championship changes, bonuses and ranking consequences.
* Added persistent record-book and Hall-of-Fame logic plus a legitimate adjacent-division double-champion route. Multiple earned belts can coexist instead of silently replacing one another.

## Stabilization and QoL

* Fixed fresh-world crashes caused by mutable Fighter objects being used as dictionary keys.
* Fixed the NPC amateur simulator still writing to the obsolete Europe-only championship table.
* Weight-cut UI now shows ahead/on-track/behind/ready status, weeks remaining, kilograms remaining and required kg/week in Nutrition and the dashboard.
* Removed the obsolete Lifestyle gym path completely.
* Save schema is JSON v17. Total event content remains 511 cards.

---

# 1.29.0 — Focus-aware amateur competition calendar

## One active sport, one competition path

* The Amateur hub and weekly Fight action now follow the selected sport.
  Choosing Judo, Boxing, Wrestling or another side sport completely hides MMA
  brackets, MMA booking and MMA championship entries. Selecting MMA hides all
  side-sport competition entries.
* A registered championship is bound to its sport. Change focus only after the
  event resolves or after cancelling the registration from that sport's
  calendar.

## Proper scheduled championships

* Side-sport tournaments now use dated registration instead of happening
  immediately from a menu. The calendar shows career year, season week,
  registration status and qualification reason.
* Each sport has two Regional Opens, two Nationals, two Europeans and one World
  Championships per year. Boxing, Wrestling and Judo show the next eligible
  four-year Olympic Games.
* Registrations persist their sport, level and absolute event week in save v15,
  preventing year-wrap and sport-switch mistakes.

## Fight modes and records

* Every non-MMA match supports Play, Live Sim and Instant result modes.
  Tournament mode is selected once and used for the whole bracket.
* Side-sport history now stores the date, sport, opponent, event, ruleset,
  competition level, statistics and mode. Recent results appear in the active
  sport hub/calendar and career statistics.
* Fixed a dictionary-refresh bug that could award a National medal without
  preserving the matching sport's national-team selection.

---

# 1.28.0 — Living amateur world and promotion integrity

## Amateur competition

* Every amateur sport now has its own Regional, National, European and World
  championship record. Two Nationals and two Europeans run each year.
* National-team selection is tracked separately for MMA, BJJ / No-Gi, Boxing,
  Kickboxing, Wrestling, Judo and Combat Sambo.
* Boxing, Wrestling and Judo athletes can qualify for the Olympic Games every
  fourth career year.
* The amateur population is larger and all seven sports remain active deep into
  long careers. Some specialists remain lifelong non-MMA competitors; others
  can make a recorded crossover.

## Living world

* Expanded country-linked name generation across Europe, the Balkans,
  Caucasus, Central Asia, the Americas, Africa and East/Southeast Asia.
* Opening pro rosters now guarantee viable divisions. Promotions recruit new
  professionals and make merit-based or same-tier transfers when a division
  needs depth.
* Promoters match fighters by activity, résumé and ranking while remembering
  prior meetings. This sharply reduces accidental repeat-fight loops.
* NPC wins/losses now update recent form, streaks and fight history when their
  scheduled card actually happens.

## Rankings and championships

* Every organization has one authoritative champion per weight class. The
  champion is no longer duplicated as the numbered #1 contender.
* Title reigns track start week and successful defenses. Vacancies, new
  champions and defenses are preserved in a visible lineage.
* Fixed long-world roster collapse, frozen zero-bout amateur prospects,
  cancelled-card booking locks, and old saves silently reverting their chosen
  side sport to MMA.

---

# 1.27.0 — Sports, belts, media and real event cards

## Amateur careers

* Compete separately in MMA, BJJ / No-Gi, Boxing, Kickboxing, Wrestling, Judo
  and Combat Sambo, each with its own record, experience, weight category and
  medals.
* Added real BJJ stripe/belt progression and Judo belt progression. Promotions
  require mat time, grading points and a coach evaluation.
* Sambo is now correctly presented as Combat Sambo. Existing careers migrate.
* Gym was removed from Life and rebuilt under Coach as one Gym & Team hub.

## Fame and media

* Amateur wins no longer make a fighter famous by themselves. Major medals,
  important pro fights, upsets, finishes and titles drive recognition.
* Amateur and low-level pro fights no longer force interviews. Major fights
  receive proper press conferences and richer post-fight media.
* Added 144 unlockable nicknames with contextual suggestions and custom names.

## Promotions

* Organizations now announce real dated cards with locations, headliners,
  co-mains, title fights and prelims. NPC fights happen on card week.
* Your accepted bout belongs to that card. Opponents can withdraw, replacements
  can step in, and genuine short-notice opportunities exist.
* UFC title fights now include challenger and champion introductions.
* Added 24 context events. Total event content: 511 cards.

---

# 1.26.0 — Reach, defence and sport rules

## Fighters and training

* Reach and stance are now persistent fighter traits.
* Striking Defense, Submission Defense and Distance Management are real,
  trainable skills on the fighter sheet.
* Broad labels such as Boxing Defense and Distance Management are no longer
  taught as moves. Older copies convert them once into the appropriate skill.
* Specific reactions such as Shoulder Roll and Peel the Hands still matter,
  but they boost defence instead of appearing as attack buttons.

## Combat

* Standing fights now move through outside, kicking, boxing and pocket range.
  Reach helps control long range but does not increase damage.
* Fight plans now include preferred range and Movement, Guard or Counter
  defence. Good defence can create a short counter opportunity.
* Submission Defense now resists both setups and finishes.
* Added open guard, front headlock, north-south and leg entanglement, with
  snap-downs, leg entries, heel hooks, kneebars and north-south chokes.

## Rules and reliability

* Boxing, kickboxing, wrestling, grappling and MMA now enforce distinct legal
  action sets in menus, AI and final resolution.
* Fixed seeded balance tests changing between app runs because action sets were
  read in unstable hash order.
* Full regression, diagnostics, five-sport legality and 2,400-fight fairness
  gates pass. Version 1.26.0 is the new stable baseline.

---

# 1.25.1 — Senior review and stable baseline

> Senior-approved maintenance release. The 1.25.0 junior candidate was not
> accepted unchanged.

## Promotion integrity

* Fixed released or renewal-declining fighters having their exclusive contract
  silently reconstructed on the next identity sync/load.
* Release now clears the named organization and stale promotion ranking/title
  state as well as the contract itself.
* Blank-contract recovery now runs only for the explicit corrupt-exclusive
  shape; a deliberate empty free-agent contract remains empty.
* DWCS no longer counts as UFC ranking experience. Three actual UFC/UFC-branded
  bouts are required before the player enters divisional or P4P boards.
* UFC rank is cleared before every rebuild, preventing a stale rank from
  surviving an ineligible refresh.

## Sponsor data

* Replaced supplement-company name matching with explicit
  `legal_supplements` sponsor benefit metadata.

## Senior validation

* Added `tests_1251` for release persistence, corruption repair boundaries,
  UFC/DWCS ranking and P4P integration, and metadata-driven sponsor benefits.
* Full regression discovery, standalone 2,400-fight fairness, diagnostics,
  compileall, balance/career probes, event Monte Carlo, economy runway checks,
  and all-new-event phone-width rendering passed.

---

# 1.25.0 — Playtest intelligence, weight-camp UX and economy hardening

> Junior-developer handoff candidate. Built from the stable 1.24.0 release after the supplied human autosave exposed UFC/title/contract, UI pacing, weight-cut UX, event, sponsor and economy issues. Senior review is explicitly requested before treating this as the next long-term baseline.

## UFC / promotion intelligence

* Fixed the corrupt state where the UI could say UFC while an exclusive contract stored a blank `org`, causing the fight board to treat the player as a free agent and expose rival promotions.
* UFC title shots now use `ufc_rank`, UFC-only bout history and live UFC résumé gates. A DWCS win / first UFC offer can no longer become an immediate title fight through generic `org_rank`.
* A recent UFC loss blocks another immediate title shot. Normal challenge path requires top-3 UFC rank, at least 3 UFC bouts, at least 2 UFC wins and a live +2 streak.
* Signing a new promotion moves the previous promotion belt to `former_belts`; an LFA belt can no longer display as the active belt while fighting in UFC.
* Debug/save headers now report the promotion-specific UFC rank and only the belt belonging to the current promotion.

## Weight / nutrition / weight-bully loop

* Booking a fight starts a persistent weight-camp record: starting walking weight, fight target, strategy, weekly scale history and final weigh-in/cage result.
* Added Performance / Balanced / Weight Bully strategies. The trade is real camp weight loss vs larger final water cut / cage size / miss and gas risk.
* Nutrition now chases the booked-fight walking-weight target only when the player actually selects a deficit plan; maintenance/bulk plans do not secretly make weight.
* Nutrition UI shows start/current/target weight and real mass lost during camp.
* Fight-week output reports real camp mass loss, water cut, rehydration and cage kilograms over the division limit.
* Slightly strengthened preparation sensitivity on brutal cuts so disciplined camps meaningfully outperform sloppy ones without making huge cuts routine.

## Economy / debt

* Replaced two competing weekly-money models with one ledger that is both displayed and actually applied to cash.
* Sponsor retainers are credited; side jobs pay only when the player works a shift; manager cuts are not charged again as a weekly bill.
* Negative cash is converted into formal debt once instead of leaving a negative wallet plus a second debt number.
* Lifestyle debt screen now supports borrow / repay $100 / repay $400 / repay maximum and shows cash, debt and net position.
* Voluntary borrowing has career-stage limits.
* Event DSL now handles debt as currency-scale state rather than accidentally clamping it like a 0-100 stat.

## UI / quality of life

* Long/new information screens use an actual Enter-to-continue prompt. The implementation no longer relies on `stdin.isatty()`, which can be false in iOS/Pythonista while input still works.
* Competition calendar, event cards and Timeline/Money screen use player-controlled pacing.
* Removed the dead visible `G` lifestyle slot; Gym is `E`.
* Manual media/social-media action remains off the weekly menu; media is handled through contextual events for now.
* Supplement-company sponsors (e.g. nutrition/supplement brands) provide legal supplements free in the shop.

## Event rebalance / expansion

* Added 36 contextual events: 12 media, 8 nutrition, 6 money, 5 sponsor, 5 UFC/career. Total database: 487.
* Reduced baseline random-event hunger from 22% to 18%; hurt/broke/post-loss weeks still rise contextually.
* Repeated event categories are damped so the same theme is less likely to spam consecutive weeks.
* Player-facing random-event effects are stage-capped to prevent old cinematic rewards from overwhelming the stabilized economy/stat scales.
* The 1.25 pack remains supplemental in sampling (~0–6% of eligible weighted picks across representative profiles).

## Diagnostics

* Playtest audit now flags blank-contract/current-org mismatch, stale previous-promotion belt and premature UFC title-offer state.
* The supplied 1.24 autosave was loaded diagnostically only; it is not included and is not a compatibility target. Under 1.25 logic it resolves to a UFC contract, no active LFA belt, outside-promotion dates blocked and no valid title shot.

## Validation

* `tests_125`: all junior-handoff checks pass.
* Historical modules through `tests_193` pass after the intentional event-total update.
* `tests_192` brutal-cut preparation regression passes after risk tuning.
* Full `tests_194` 400-fight engine-fairness suite is intentionally left for senior/local completion because it exceeds the execution window here; reduced 80-fight clone smoke was Boxing 53%, Wrestling 48%, BJJ 48%, Muay Thai 53%, and all source-symmetry checks passed.
* Diagnostics must report v1.25.0 / 487 events / ALL SYSTEMS OK before accepting the package.

---

# 1.24.0 — Combat physiology, career intelligence and playtest forensics

## Combat / physiology reconstruction

* Weight classes now create persistent physical identity: heavier divisions have higher strength/impact potential but lower speed/cardio ceilings and higher gas cost; lighter divisions invert that trade-off.
* Raw developed skill is separated from fight-night expression. Nutrition, body fat, health, weight-cut condition, injuries and persistent damage can temporarily suppress effective stats without deleting training progress.
* Hands use `striking`; kicks use `kicks`; Body Kick is a real distinct action. Technique levels, camp sharpness and scouting now contribute small capped edges.
* Fight-night mass/height create only a capped grappling/clinch modifier so size matters without replacing skill.
* Core perks now affect the systems they describe (accuracy/tendencies, gas, chin/cut behavior) instead of being collectible labels only.

## Nutrition / weight cutting

* Meal plans are persistent weekly regimens. Structured `nutrition.json` fields are the source of truth for weight movement; old label-substring diet logic was removed.
* One canonical weigh-in now preserves walking weight and separately records scale and rehydrated cage weight.
* Hard/brutal cuts have real miss-risk curves; preparation strongly matters but cannot make a brutal cut routine. Larger cuts also impose fight-night energy/durability/cardio costs.
* Generic PED/doping risk no longer acts as an unrelated weight-cut bonus.

## Career intelligence fixes from the 1.23 playtest

* Promotion rankings are résumé-first; hidden skill/fame can no longer make a 0-2 pro promotion #1.
* Pro story/title gates use pro résumé and promotion standing rather than leaking amateur wins into contender logic.
* Early-pro matchmaking uses experience bands and named promotions do not silently borrow fighters from rival exclusive rosters.
* Direct contracts receive real show/win purse terms.
* Fame is normalized to 0-100; major sponsors require an actual pro résumé plus audience, not just amateur wins.
* Manager advice now states the real objective (experience fit, recovery, headline value) instead of vague risk language.

## Save / playtest forensics

* Autosaves now preserve the full live world and occur after complete post-fight bookkeeping, preventing manual/autosave universe divergence.
* Added bounded telemetry for exact UI text, prompts/inputs, matchmaking/event reasoning, AI action weights and real-player fight exchanges.
* Save menu can export one playtest ZIP containing a canonical snapshot, contradiction audit and recent trace.
* Performance rating is now a defined 1-10 fight grade instead of permanent `0.0` placeholder data.

## Validation

* New 1.24 observability/intelligence and release-gate suites cover autosave world integrity, ranking/matchmaking/contract logic, physiology caps, structured nutrition, cut Monte Carlo, perks, sponsorships and performance ratings.
* Legacy combat legality, damage/injury, contracts, event validation and engine fairness suites remain green. Clone mirrors remain around 50/50 across Boxing, Wrestling, BJJ and Muay Thai.

---

# 1.23.0 — Phase 3 contextual world events and release validation

## 60 new contextual events

* Added `events_v123.json` with 60 new cards: six each for wins, losses, injuries,
  camps, money, gyms, teammates, family, media, and career progression.
* New events react to real existing career state instead of generic week rolls: win/loss
  streaks, booked fights, normal/foreign camps, teammates, specialty gyms, managers,
  named organizations, debt, followers, sponsors, and relationship strength.
* The new pack is intentionally a minority of eligible event weight. Across representative
  career states it accounts for roughly 9-15% of conditional selections, so old story
  content remains visible.

## Event engine hardening

* `context_pack()` now exposes streak, booking/camp state, teammate/gym/manager/org,
  debt/followers/sponsor count and relationship values to declarative event requirements.
* `validate_event_pack()` is now a real DSL validator: duplicate/missing IDs, unknown
  requirements/effects, contradictory min/max gates, invalid chance values, empty
  choices and duplicate choice keys are release failures.
* Fixed an old substring bug where `upgrades` matched the school keyword `grades`,
  which could silently make unrelated adult events ineligible.
* Event titles, descriptions, choices and effect summaries now wrap safely on phones.
  The complete 451-card database was rendered in the Phase-3 test at <=44 columns.

## Validation / packaging

* Added `tests_123.py` covering pack shape, reachability of every new event, context
  gates, event weighting, teammate text substitution and all-event phone width.
* Full discovered regression suite: 26 versioned modules, `FAILED MODULES 0`.
* Diagnostics: all systems green with 451 events, save/load, combat and booking checks.
* Large balance pass: 2,000 canonical benchmark fights plus 2,400 style-clone fights.
  Clone player-slot win rates were Boxing 50%, Wrestling 53%, BJJ 49%, Muay Thai 52%.
* No global combat tuning was applied. The simplified persona-career probe still gives
  low pro win rates (~18%), while controlled equal-fighter tests remain fair; it stays
  classified as a harness/opponent-generation investigation, not a combat-buff target.
* Reference saves load successfully for diagnosis and their SHA-256 hashes remain
  unchanged by load. They are not shipped and are not compatibility contracts.
* Save schema remains JSON v11; Phase 3 adds no required persisted fields.

# 1.22.0 — Phase 2 tactical gameplay and mobile presentation

## Tactical damage is now location-aware all the way through

* The fight HUD keeps the fast `H / B / L / C` scan order and now also shows
  lead/rear leg damage (`L/R`) so a player can see which side is compromised.
* High-IQ AI does not merely prefer "a low kick" anymore. It selects the
  actually damaged lead or rear leg once the damage is visible.
* High-IQ AI can deliberately work an existing cut instead of every sharp
  strike opening/worsening an unrelated random facial zone.
* Live body-map damage and persistent between-fight damage both inform attack
  selection: injured legs attract low kicks and takedowns, body damage attracts
  liver/knee work, head trauma attracts power shots, and existing cuts attract
  accurate hands/elbows/ground strikes.
* Cut targeting is deliberately throttled so one marked brow does not become an
  automatic doctor stoppage. Existing KO/TKO/submission constants were not
  globally buffed.

## Overseas camps are priced by what they are worth

* Removed hand-entered camp prices. Quotes are derived from weeks away, room
  quality, rare techniques, networking upside and travel premium.
* Current quotes: Bishkek $3,900; Phuket $4,800; Makhachkala $5,200;
  Rio $5,200; Las Vegas $6,200.
* Camp previews now show quality, network value, focus and rare-technique reward
  in phone-safe wrapped lines.
* `spec["cost"]` remains populated for older callers, but is generated from the
  reward profile so future camp edits cannot silently leave pricing stale.

## Phone-first UI pass

* Weekly dashboard reorganized into `CAREER`, `RIGHT NOW`, and `CONDITION`
  instead of appending every subsystem as an independent status line.
* Overseas-camp status now reads `intl_camp_weeks`; the old dashboard displayed
  the normal fight-camp clock and could show the wrong remaining time.
* Fight feed wraps long commentary while preserving actor prefixes and finish
  tags such as `TD`, `KD`, `CUT` and `SUB`.
* Shared action menus wrap long descriptions with readable indentation.
* Status messages (`good`, `warn`, `info`, milestones) wrap to terminal width.
* The text wrapper now splits pathological long tokens instead of leaking past
  the 44-column phone target.

## Stabilization hotfix found during the Phase 2 audit

* Legacy event packs store choices as labels such as `A) Take a week off`
  without a separate `key`. 1.21's safer choice parser accidentally made a
  plain `A` invalid for those events. 1.22 derives a key from legacy prefixes
  (or the choice index), while still keeping blank input from silently choosing A.

## Validation and balance policy

* Added `tests_122.py` for exact leg targeting, cut targeting/worsening, HUD
  width, feed/menu/token width, dashboard camp clock, value-based camp pricing,
  legacy event letters and an equal-fighter combat guardrail.
* The complete historical suite remains the release gate; no old suite was
  deleted or bypassed.
* Balance lab after the Phase 2 changes stays close to slot-fair in equal fights
  and ordinary pro decisions remain the majority. Because the measurements did
  not show a clear engine-wide imbalance, Phase 2 intentionally makes **no**
  blanket accuracy/damage/KO rebalance.
* Existing simplified persona-career probes still produce very low player win
  rates. This remains flagged as a career/opponent-generation harness issue to
  investigate separately rather than "fixing" combat around a suspect probe.

# 1.21.0 — stabilization, tactical damage and living events

## Progression correctness

* Removed the second yearly age writer. One 52-week year now means one birthday.
* Fight form is recorded once by the fight ledger; one loss can no longer count as two.
* Menu actions explicitly prove they changed career state before time advances.
  Back, cancel, view, save and invalid input cannot reroll weekly events.
* Starting physique letters now initialize their intended physique name and body-fat value.
* Legacy camp/life injuries now enter the locational-damage injury model. One week heals
  one injury week, and treatment no longer double-charges a second generic rehab visit.

## Tactical combat

* The live fight HUD now shows `H / B / L / C`: head, body, worst leg and cut damage.
* Fight AI reads live body-map damage. Smart opponents return to a hurt leg or body,
  pressure accumulated head trauma and work an existing cut toward a doctor look.
* Repetition counters are now per fighter. One fighter throwing jabs no longer makes the
  other fighter's jab less accurate.
* Chain-wrestling follow-ups were recalibrated and now reward actually knowing chain,
  single-leg, clinch or mat-return technique.
* Boxer AI commits to hands, body punching and returning to the feet instead of wasting
  exchanges on low-percentage takedowns and unfamiliar kicks.

## Camps, UI and events

* International camps are major investments: $1,800-$4,200, up from $600-$1,800.
* The career dashboard removes repeated walking-weight, physique and body-fat lines and
  presents record, phase, organization, body and money in a compact phone-first block.
* Event requirements now enforce nested min/max age, losses, reputation, energy, health,
  injury state, damage and last-result gates.
* Fixed `parents` accidentally matching the word `rent`, string team changes being ignored,
  and blank input silently selecting choice A.
* Added 30 contextual events for tactical training, camp life, recovery, injuries, money,
  school, family, sponsors, managers, rivalries and career pressure. Total: 391 events.
* Every event pack is included in duplicate-ID validation and diagnostic counts.

## Tools and tests

* `python3 -m mma_legend.tests` discovers every versioned suite instead of stopping after
  eight old modules.
* The balance lab now creates genuinely equal numeric matchups, uses deterministic move
  sets, recognizes named decision/TKO/KO variants, and produces professional persona bouts.
* Added `tests_121.py` for the new progression, injury, event, HUD, AI and camp invariants.
* 24 suites green; system self-check green.

# 1.20.0 — locational damage and real injuries

## Damage is a body map, not a number

`f_dmg` / `o_dmg` were two scalars, so a body kick and a head kick differed
only in magnitude and the only early finish was a head KO. New `damage.py`
tracks head / body / lead leg / rear leg plus a separate cut layer, and **each
location feeds a different system**:

* **head** -> knockdowns, concussive KO, and the only KO by punches
* **body** -> steals gas, which is how liver shots end fights late
* **legs** -> kick power, takedown entries and movement
* **cuts** -> doctor stoppage, independent of damage

Real finishes now exist: **KO (body)** when accumulated body damage folds a
man, **TKO (leg)** when a leg will not hold weight, **TKO (doctor)** when a cut
is too deep. Accumulated head trauma raises the next KO roll. A compromised leg
cuts kick accuracy to 45-20% and drags takedown entries with it.

**Checked kicks damage the kicker's shin**, which makes checking a real skill.

Calibrated against measured 15-minute fights. Head damage was saturating at 100
in every single fight on the first pass; per-location scaling is now tuned so a
typical decision sits mid-range. Result: **58% decisions / 42% finishes**, and
clone-vs-clone fairness still holds at 49-51%.

## Injuries carry out of the cage

14 injuries with real weeks, severity and cost — bruised shin through broken
hand, broken knuckle, orbital fracture, jaw fracture, torn shoulder, torn knee.

* **Post-fight**: what happened to the body map becomes what you carry out.
  Heavy head damage or two knockdowns is a concussion; a wrecked leg is a dead
  leg; deep cuts need stitches; punching a skull breaks hands.
* **Serious injuries block every booking path**, through the one gate in
  `matchroom.gate()`.
* **Surgery** is fast and expensive ($2600 for a broken hand, halves the
  layoff). **Physio** is a quarter of the price and saves less. Some things —
  concussion — only rest fixes.
* **Rare life injuries**: a street altercation, punching a wall after a bad
  decision, a pothole on a run. Measured at 3 per 500 weeks.
* **Training injuries** scale with intensity, low energy and age.

## Tests

`tests_120x.py` — locations drive separate systems, checked kicks hurt the
kicker, all three new stoppages exist, finish rate realistic, body maps reach
the outcome, injuries block booking, surgery vs physio, healing, rarity, and
serious fractures modelled.

24 suites green.

# 1.19.4 — engine fairness

Instrumented the engine with clone-vs-clone fights: identical fighters in both
slots should split 50/50. They did not. The player slot won **72%** of boxing
mirrors. Three separate one-sided pieces of logic:

1. **TKO stoppage was order-biased.** The player's condition was tested first
   in an if/elif chain, so whenever both men qualified in the same round the
   player always won. Each branch also read the WRONG fighter's gas — the
   player's stoppage of the opponent was gated on the player's own tank.
   Worth 2.3x the finishes.
2. **Momentum was player-only.** Both branches were gated on `is_p`, so the
   player gained from their own momentum while the opponent gained nothing
   from theirs.
3. **Only the player could throw combinations.** `last_p` was written for the
   player alone, so the +10% accuracy / +1 damage jab-into-power-shot bonus
   was unavailable to every opponent in the game. This was the largest single
   effect, and the reason boxing was the most skewed style.

Clone fights now land at 46-51% across all six styles.

## Style balance

With a fair engine the real balance problem became visible: strikers 64%,
wrestling 38% — backwards for MMA. Cause: `stand_up` was never given a
contested accuracy roll and fell through to the ~58%/tick default, so the
bottom fighter stood up at will. A wrestler held 22 seconds per takedown.

* Standing up is now contested by the top fighter's ground control.
* Judges weight control, passes and takedowns properly — a round spent on top
  is hard to lose on the cards.

Wrestling 38% -> 46%, BJJ 46% -> 49%, Sambo 42% -> 47%. Spread narrowed from
26 points to 21.

## Tests

`tests_194.py` — clone fairness across four styles, momentum two-sided,
combinations two-sided, TKO order-independent, stand-up contested, grappling
viable.

23 suites green.

# 1.19.3

## Fight UI

The live feed was a wall of text. Full names ("Umur Panteleev") burned 14+ of a
44-character phone line on every exchange, both fighters' lines looked
identical so nothing could be scanned, commentary repeated the same sentence
three times running, and the round banner spent four lines repeating gas.

* Short labels — surname only, so lines fit and the commentary stays
  grammatical ("You digs a liver shot" was the naive fix; surname is correct).
* Every exchange is prefixed and coloured by who acted: `>` you, `<` him.
* Right-aligned tags for the things that matter: `TD`, `SUB`, `KD`.
* Compact HUD header: one line for round/clock/position, then a damage bar and
  gas per fighter, so you can see who is being hurt without waiting for the
  round summary.
* Back-to-back duplicate commentary is suppressed.
* Moment menu capped at 4 options and printed on its own line — it was 6,
  wrapping to two lines every time.
* Round summary and corner advice split into short lines instead of one 60+
  character line that wrapped badly.

## Overseas camps

The old camp was a stat potion: pay, get +1 to three skills per week, receive a
`connection` dict that **nothing in the game ever read**. New `camps.py`:

* Five destinations with a named room and a culture, not just a bonus list —
  Makhachkala, Phuket, Rio, Vegas, Bishkek.
* Real cost: 4-6 weeks where you cannot fight, cash up front, energy drain,
  injury risk in the harder rooms.
* An adaptation curve. The first third is survival (happiness drops, gains are
  halved); after that you start learning. Leaving early wastes the money.
* Techniques the home gym cannot teach — chain wrestling in Dagestan, the
  berimbolo in Rio, elbows in Phuket.
* **Connections are real and are now read.** You come home with a named person
  in a role, and `corner_quality()` and `connection_bonus()` feed cornering
  and matchmaking reach.

`systems15.start_camp` / `tick_camp` delegate to the new module so there is one
implementation, not two.

## Tests

`tests_193.py` — feed prefixed and within width, no triple repeats, moment menu
fits one line, camps blocked when booked, camps cost real weeks and money,
camps teach and connect, connections are actually read.

22 suites green.

# 1.19.2

Two systems rebuilt: the booking spine and the weight cut.

## One booking entry point

Fights could be booked from five places — `find_fight`, `inbox_night`,
`booker_night`, competition week and no-gi night — each with its own
eligibility checks, purse handling and camp logic. That is the reason a rule
true on one screen was false on another. Worst case found: the manager menu
called `inbox_night(console, fighter, None)` with **no fighter pool at all**,
so offers built there had no world to draw opponents from.

New `matchroom.py` owns booking:

* `gate()` — the single answer to "can this fighter take a fight?"
  (suspension, injury, recovery, camp)
* `booked_status()` — one computation of what is on the books
* `sign_and_camp()` — the only place a date gets taken, guaranteeing the fight
  is in the future and a camp exists for it
* `book()` — the screen every menu route lands on

`manager_menu` and `lifestyle_menu` now take the pool and thread it through.
Also fixed a latent `NameError`: `lifestyle_menu` had no `pool` in scope at
all, and a local variable of the same name held a list of coach names.

## Weight cuts are physical now

Nothing enforced a maximum cut. A 118kg fighter could declare **Flyweight**
and the game shrugged — `cut_risk` saturated at 95 and there was no weigh-in.

Cuts are now bounded by physiology:

    <= 2%   natural      walks around at the limit
    <= 8%   routine      a normal camp cut
    <= 13%  hard         costs you in the cage
    <= 18%  brutal       real chance you miss or gas
    >  18%  impossible   refused outright

`lowest_class_for()` tells a fighter the lowest division their frame can make;
118kg is a Heavyweight and nothing else. Picking a home division now warns on
hard cuts, asks you to confirm brutal ones, and refuses impossible ones.

`weigh_in()` resolves the scale on every pro bout. Whether you make it depends
on the gap and how disciplined the camp was, not a flat dice roll — measured
on a brutal cut, a sloppy camp makes weight 0% of the time and a disciplined
one 96%. Missing weight costs 20-30% of the purse, fame, and the promoter
remembers it. Hard and brutal cuts drain energy going into the fight.

## Tests

`tests_192.py` — one gate, menus thread the pool, booked status, impossible
cut rejected, lowest class sane, bands scale, discipline decides a brutal cut,
hard cuts drain, natural weight is free.

21 suites green, self-check clean, headless careers 0 issues.

# 1.19.1

Audit of the 1.19.0 tree. Two suites were failing; the cause was a single
critical bug in the derived-record system introduced in 1.18.

## CRITICAL — every pro fight was counted twice

1.18 moved the official pro record to being derived from `fight_history` via
`record.commit()`. The legacy in-place increments in `fights._apply_outcome()`
were never removed, so both writers ran on every bout:

    player debut  0-0  -> 2-0 after one fight
    opponent      4-1  -> 4-3 after one fight

`_apply_outcome` no longer touches pro W-L; that ledger belongs to
`record.commit()`. Amateur records are still incremented there, because the
amateur ledger is not history-derived.

## CRITICAL — NPC careers were erased on first contact

`record.sync()` rebuilt the record purely from history. Every NPC is generated
with a synthetic record and an EMPTY history, so the first time a background
fighter fought, their whole career was deleted and replaced by that one bout:
a 4-1 contender came out of one fight at 1-0.

Records now carry a baseline, resolved by a rule that handles both cases:

* pro rows already in history  -> the ledger is the record, stored numbers that
  disagree are corruption to repair (the 1.18 intent, preserved)
* no pro rows but a record exists -> a generated NPC's prior career, preserved

Verified: NPC 4-1 + a win = 5-1; player 0-0 + a win = 1-0; and the 1.16 repair
case (bogus 17-5 over a 3-row ledger -> 2-1) still passes.

## Also in 1.19.1 — contracts were never saved

Auditing a real 1.15 playthrough (17-5, week 313, signed to Cage Warriors)
showed the game reporting the player as a FREE AGENT. Cause: `org_contract`
was never a declared field on `Fighter`, and `from_dict()` filters incoming
keys against `__dataclass_fields__` — so the contract was silently dropped on
every single load. Every deal signed was lost the next time the game started.
This is the root of "signing an organization doesn't work anywhere".

`org_contract` and `debt` are now declared fields. Verified by round trip:
sign -> save -> load keeps the deal and still blocks rival promotions.

## New: save auditor

    python3 -m mma_legend.repair save.json          # audit
    python3 -m mma_legend.repair save.json --write  # repair -> save_repaired.json

Finds records that disagree with their ledger, missing contracts on signed
fighters, pre-1.9 contract shapes, and missing debt/story_flags. Baselines
every fighter in the pool so no later resync can wipe NPC careers.

## New tests

`tests_191.py` — NPC career not wiped, corrupt record still repaired,
`_apply_outcome` no longer double counts, amateur record still counted inline,
contract survives save/load, exclusivity holds.

## Verification

19 suites green, self-check clean, `compileall` clean, headless career batch
runs with 0 issues.

# 1.19.0

Hurt body slows hooks and shots. Hurt legs make doubles sloppy and the
other man's doubles easier. A liver shot steals gas. Stuffed doubles
chain into a trip or clinch. Signature techniques fire from the seat
they belong in. Judges jitter by lean so splits exist; body shots count.

# 1.18.0

Official pro record is derived from MMA history under a named org.
Grappling and blank amateur nights no longer inflate W-L.
Opponent AI has a corner plan, reads your last shots, and feels out
round one.

# 1.17.0

Bigger world: new career ~560 amateurs / 400 pros. Autosave keeps ~520
and protects the player's org + class. Saves include a top-level debug
snapshot. Expired deals queue a re-sign instead of dumping a champ.

# 1.16.0

Title defense no longer dies when autosave trimmed every same-org
middleweight out of the pool. The champ gets a same-class challenger
from the wider roster. Belts must match holder org and class. Session
log no longer writes "fight TKO" on every quiet week.

# 1.15.0

Inbox can offer a title date when you are #1/#2 at your named org or you
hold the strap. Opponent is the champion or the next man. Purse +35%.
The title flag survives fight week. Manager AI does not kill title paper.
NPC cards pair champ vs #1 about half the time.

# 1.14.0

Regional belts persist per promotion and class. NPC cards can move them.
Hot regional names climb the named-org ladder. They do not walk into the UFC.
Amateur turn-pro lands on a home org, not a fake "Regional" label.
Pro purses follow the promotion table. A booked purse is no longer overwritten
by the old tier formula.

Life menu lost the ghost number keys, the duplicate press/social doors, and
the compete-in toggle (amateur sport still lives under D). Dead gym hire
list is gone. Dashboard shows a Contender Series hook when you have one.

# 1.13.0

Named promotion is the career. Room is only a matchmaking band.
`set_room` no longer overwrites Balkan Combat with "Regional FC".
Dashboard prints the org and contract, not a tier string. Rankings open
on your promotion first. A 4-0 regional kid is on that board, not UFC #4.

Load repair walks a premature UFC stamp home and fills a crashed
walk/bodyfat. Heavy-built will not sit at 5% / 80kg out of camp.

Meal-plan `weight_change` from nutrition.json now moves the scale.
Out of camp the walk rebounds toward natural. Fight-night cut is a
one-shot energy tax. Four more food events.

# 1.12.0

Nationals and local brackets share a same-day gas rule. After match 1 the
next opponent is tired from his quarter, and you only get a stool — not a
full tank.

Pro booking is manager-only. No manager, no inbox.

School events stop after graduation. Nutrition no longer asks to change
class every visit (press C). Out of camp, walking weight fills back toward
natural. Food events move nutrition, walk and bodyfat.

UFC is not a 3-0 stamp. Contender Series needs 6 pro wins and a streak.
A contract offer can be refused. Early UFC signs walk back to the home
regional org on load. Ranked spots need 3 UFC bouts. Dashboard shows the
real org, not "PFL | UFC".

Pro cards stay on the eight official MMA classes.
