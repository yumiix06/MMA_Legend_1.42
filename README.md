# MMA Legend 1.42.0

Text-based MMA career simulator. **v1.42.0 is the Taekwondo & Kicking update**, and the full build also includes v1.40 Performance/Education and v1.41 Promotion Rankings/Gym Life. Fresh careers are the design target; older saves are debugging/reference fixtures rather than compatibility constraints.

## Run the game

### iPhone / iPad
Keep the folder intact and tap **`START.py`** (or `main.py`) in Pythonista/Pyto-style apps.

### Computer
```bash
python3 main.py
# or
python3 -m mma_legend
```

## v1.42.0 — Taekwondo & Kicking

- Added Taekwondo as a full amateur/Olympic sport with WT-style three-round kyorugi, its own weight classes, legal-action rules, technical scoring and round wins.
- Added Taekwondo as a starting background, NPC style and quick-play background.
- Added Taekwondo dojangs, automatic belt progression, passive technique learning/mastery and dedicated gym events.
- Added nine named Taekwondo techniques and new playable action families: side kick, spinning back kick, spinning hook kick, axe kick and tornado kick.
- Expanded kicking mechanics in MMA/kickboxing: setups, distance management, missed-spin counter windows, low-kick checks, caught body kicks, leg-damage interaction and gameplan weighting.
- Added the **Taekwondo Kicking** MMA gameplan and matchup-aware coach recommendation for Taekwondo specialists.
- Advanced spinning attacks are strongly technique-gated so untrained fighters do not spam high-damage kicks; pro MMA finish/decision balance remains sane.
- Added 18 new Taekwondo/kicking events; total authored event count is now 565.
- Fighter/Team screens now show Taekwondo belt and dojang progress.

## v1.41.0 — Promotion Rankings & Gym Life

- Rankings includes a visible **Promotion rankings (all organizations)** browser with champions and top-15 boards for every named promotion/weight class, even while unsigned or amateur.
- Specialist BJJ, Judo, Kickboxing/Muay Thai and Taekwondo memberships develop automatically on home weeks.
- Membership builds mat time, grading points, technique XP/mastery and slow discipline polish; BJJ/Judo/Taekwondo belts promote automatically when requirements are met.
- International camps pause home-gym development so the fighter cannot train in two countries at once.
- Added 36 BJJ/Judo/Kickboxing/school/university contextual events.

## v1.40.0 — Performance & Education

- Legal supplements are temporary training/recovery/performance modifiers instead of permanent stat purchases.
- Dedicated prohibited-performance/anti-doping state with scrutiny, sample collection, pending results, violations, suspensions and health burden.
- Fighters under 18 cannot acquire debt.
- Training menu displays current skill levels beside each focus.
- Rebuilt secondary school and added a real university foundation: degrees, semesters, credits, exams, tuition, scholarships, pause/dropout and contextual degree benefits.

## Folder layout
```text
MMA_Legend_1.42.0/
├── START.py
├── main.py
├── README.md
├── mma_legend/
├── tests/
├── tools/
└── docs/
```
Runtime saves, playtest traces, caches, bytecode and debug logs are excluded from release ZIPs.

## Developer checks
```bash
python3 -m mma_legend.diagnostics
python3 -m tests.tests_142
python3 -m tests.tests_141
python3 -m tests.tests_140
python3 -m tests.tests_130_release
python3 -m tools.build_release
```

## Documentation
See `docs/current/ARCHITECTURE.md`, `SYSTEM_MAP.md`, `CHANGELOG.md`, `VERSION_HISTORY.md`, and `RELEASE_AUDIT_1.42.0.md`.

## v1.39.0 — Combat Intelligence

- Added `combat_intelligence.py` as a bounded tactical decision layer over the canonical fight engine.
- Fighters now read repeated takedowns, jabs/kicks, gas, score state and live damage, with adjustment speed driven by Fight IQ, adaptability, discipline and composure.
- NPC opening gameplans are matchup-aware and between-round plans can change when shots fail, damage accumulates, gas collapses or the score demands risk.
- Damage awareness now affects **action selection**, not only accuracy: compromised legs/body/head change self-preservation and intelligent fighters exploit real opponent damage.
- Stuffed shots can become true secondary takedown chains from clinch contact; chain quality depends on grappling, Fight IQ, adaptability, gas, intent and learned techniques.
- Scrambles are contested and position-aware, including stand-ups, half/side control and back-taking outcomes from turtle/front-headlock exchanges.
- Scouting is information-gated. Low tape read no longer reveals exact opponent ratings; deeper reads progressively expose tendencies, broad strengths, likely approach and best techniques.
- Fight camps now separate Striking, Wrestling, Cardio, Complete, Anti-Wrestling, Submission Defense and Pressure & Entries. Preparation bonuses are opponent-specific and capped.
- Completed camps keep their opponent read/preparation until the booked fight, then bout-specific preparation is cleared.
- FightOutcome now exposes bout-scoped decision telemetry so strategy adherence and adaptation can be measured in balance labs.
- UI architecture is intentionally unchanged. Old saves are reference-only for this release and are not a design constraint.


## v1.38.0 — Living Careers

- Added persistent NPC career personalities and goals: develop, activity, rebuild, rank climb, title chase, move up, defend belt and final run.
- NPC weekly intent now follows career context rather than only energy/idle thresholds.
- Added distinct promotion identities (prospect protection, meritocracy, star power, activity, hard matchmaking and regional focus).
- Promotion identity now affects card pairing, contender/showcase frequency, player-opponent selection and roster movement.
- Player fight offers now explain their career meaning: showcase, rebuild, step-up, contender test, short-notice jump, home-market feature or championship opportunity.
- Career opportunities carry risk/upside ratings and successful high-value opportunities award bounded reputation/fame/legacy bonuses.
- Strong NPCs seeking a move up are preferentially selected for legitimate roster vacancies while existing roster floors, title integrity and trilogy limits remain authoritative.
- Fixed offer-reason handling where a string could be split into individual characters by manager/promotion AI.
- UI/navigation structure is unchanged from v1.37.1. Save format remains v17.


## v1.37.1 — training menu cleanup

- Removed the remaining Train and Amateur emojis from the weekly action list.
- Rebuilt regular Training focus choices as a clean one-option-per-line column.
- Rebuilt Light / Normal / Heavy intensity choices as a second aligned column with energy and injury risk.
- Repeat Last Session and Back now sit below the focus list instead of competing with the training options.
- Cancelling from focus or intensity still consumes no energy and does not advance the week.
- Training mechanics, gains and save format are unchanged.

## v1.37.0 — UI freeze candidate

- Kept the flat v1.36 weekly navigation; no new hub hierarchy was introduced.
- Reduced weekly emoji use to only the most useful recognition cues.
- Standardized generic choice prompts on `>` and removed remaining decorative arrow glyphs from the main management flow.
- Added a real Compact Dashboard mode and saved per-career Color preference.
- Added direct Settings access from the secondary Career actions.
- Reworked Fighter into grouped Striking, Grappling, Physical and Fight IQ sections with concise career/condition information.
- Belt display now shows concise belt/stripe state plus progress toward the next grade.
- Contract and fight-week information is shorter while preserving title, short-notice, weight-target and negotiated-clause visibility.
- Main menu/tutorial wording was tightened to match the final navigation.
- Team/Life browse safety remains unchanged: backing out never advances time.
- Save format remains v17.

## v1.36.1 — menu cleanup

- Amateur fight booking now lives entirely inside the Amateur menu.
- The weekly Fight option is hidden for unbooked amateurs and returns for booked bouts or professional careers.
- Weekly menu rows are action names only; time-cost descriptors and the old browse labels were removed.
- Emoji use is restrained to a few primary actions; decorative section symbols were removed.
- Navigation safety from v1.36 is preserved: opening or backing out of Team, Life and information screens does not advance the week.
- Save format remains v17.


## v1.34.0 Part 1 — UI / navigation
Compact weekly dashboard, domain-based Career/Team/Life navigation, persistent alerts, action cost tags, weekly change reports, and one-key repeat training. Legacy shortcuts remain accepted.


## v1.35.0 Part 2 — UI / QoL

- Reworked the title screen around Continue / New / Load / Quick Start / Learn rather than developer-facing status noise.
- Replaced the old seven-page tutorial with a topic guide plus an optional non-blocking guided start for new careers.
- Expanded Career into Overview, Fighter Sheet, Calendar, Timeline, Rankings, Amateur, Weight, Inbox, Finances and saved interface preferences.
- Added a unified career calendar for booked fights, championships, camps and contract expiry.
- Rebuilt booked-fight navigation into a no-time Fight Prep hub with tale of tape, scouting, weight/camp and contract/purse pages.
- Upgraded gameplan selection with a matchup-aware coach recommendation, tactical summary card and remembered preferred plan.
- Fight-view preference now acts as the default when the cage closes.
- Timeline opens as a short amateur/pro overview and offers a paged/filterable full-history browser.
- Added a consolidated post-fight summary for result, key stats and career consequences.
- Added optional compact dashboard and week-report preferences saved per career.
