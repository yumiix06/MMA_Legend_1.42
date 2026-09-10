# MMA Legend — how this tree is supposed to work

Version 1.21 onward. This is the developer contract, not flavour text.

## Spine (do not redesign)

- Weekly loop lives in `app.game_loop`. One action, then `Fighter.advance_week`, then `FighterPool.simulate_week`, then one story beat or random event.
- Fights live in `engine/fight.py` + `engine/positions.py` + `engine/scoring.py`. Ticks, LEGAL roles, gas, ride clock, 10-point-must / ADCC. Watch mode is asked at the cage.
- The player is `models.Fighter`. Saves are JSON v19. New fields get explicit upgrade defaults in `persistence._upgrade_player`. Fresh-career correctness is the design target; older saves are reference/debug fixtures.
- People (managers, matchmakers, promoters) live in `people.py`. NPC traits live in `npc.py`. Weekly NPC intent lives in `ai.py`.

## Identity (1.13 source of truth)

Named promotion is the career. Room is only a matchmaking band.

- Writer of `fighter.organization`: `orgs.sign_org` and `contracts.sign` / `contracts.release`. Nobody else.
- `booking.set_room` may change `room` + `promotion_tier`. It must not stamp `"Regional FC"` over `"Balkan Combat"`.
- `identity.sync` is the reconciler. Load, weekly tick, and sign all call it.
- `PROMOTION_TIERS` is a legacy label list. Do not use it for display or eligibility.
- UFC numbered ranks need 3 UFC bouts. Regional boards are per-org, per class. A 4-0 Balkan fighter is Balkan Combat MW, not UFC #4.

## Body / physiology (1.24 source of truth)

Persistent body state is `natural_weight`, `walking_weight`, `bodyfat`, `fight_weight_class` and cut health.

- `physiology.py` owns weight-class physical ceilings and effective fight-night stats. Do not recreate weight bonuses in combat/training code.
- `cut.tick_body()` owns weekly mass/bodyfat movement and reads structured `data/nutrition.json`; never infer diet behavior from label substrings.
- `physiology.nutrition_week()` owns meal-plan quality, recovery, happiness and cut-health changes. Do not double-apply those in `cut.py`.
- `cut.weigh_in()` is the only fight-week cut resolver. It writes temporary scale/cage weight and `cut_drain`; it must never overwrite `walking_weight`.
- `engine/fight.py` consumes `physiology.effective_stat`, impact/gas/size helpers and small perk modifiers. Skill remains primary; size effects stay capped.
- Food events may write `walking_weight` / `bodyfat` / `nutrition`; `events.apply_effects` already understands those keys.

## Fight damage / tactical targeting (1.20–1.22)

- `damage.BodyMap` is the live-fight source of truth for head, body, lead leg,
  rear leg and cuts. Do not recreate locational damage in a second module.
- `engine.fight._damage_hunt_weight` answers **which action** an AI should
  prefer against visible damage. `_damage_target_hint` answers **where that
  chosen action aims** (including the exact leg or an existing cut). Keep those
  decisions separate unless the tactical AI is intentionally redesigned.
- `fighter.damage` is the coarse between-fight injury/damage memory. It can
  bias opening tactics before the new fight's BodyMap has accumulated damage.
- HUD rendering belongs in `ui.GameConsole.fight_damage_line`; phone target is
  44 columns and the H/B/L/C scan order is intentionally stable.

## Overseas camps (1.19.3–1.22)

- `camps.py` owns destinations, adaptation, rare techniques, persistent
  connections and pricing. `systems15` remains a compatibility wrapper only.
- Camp price is derived by `camps._quoted_cost()` from weeks, quality, rare
  techniques, network upside and travel premium. Do not hand-edit `cost` and
  let reward/price drift apart.
- International trips count down with `intl_camp_weeks`; ordinary booked-fight
  camps use `camp_weeks_remaining` / `camp_for_bout`. UI must not mix clocks.


## Playtest observability (1.24)

- `telemetry.py` records exact rendered UI/input plus structured event/matchmaking/fight reasoning during human sessions.
- Combat exchange traces are gated to real player fights so balance labs do not explode in size/time.
- `persistence.export_playtest_bundle()` is the preferred bug-report artifact: canonical full-world snapshot, summary/audit, trace and debug log.
- Autosaves must serialize the same live world as manual saves and happen only after full bout finalization.

## Booking

- Amateur: `fights.find_fight` / brackets / calendar / no-gi.
- Pro: `fights.inbox_night` only, and only with a manager. Exclusive deals go through `contracts.can_accept`.
- DWCS is an invitation (`dwcs.py`), not a room you get promoted into at 3-0. A grind decision does not sign.
- `promotion_events.py` is the pro calendar source of truth. Offers attach to a
  stable event ID and date; NPC bouts resolve only when that event week arrives.
  Scheduled title bouts must contain the live champion and one fighter may not
  occupy two open cards.

## Amateur sports / belts (1.30 source of truth)

- `amateur_sports.py` owns active sport, normalized names, sport W-L-D, XP,
  medals, weight labels and championships. Side-sport rows must never affect
  amateur-MMA/pro records or MMA streaks.
- BJJ and Judo grade points plus mat weeks are separate. `evaluate_belt()` is
  the promotion gate; belts are not generic skill levels.
- `engine/judo.py` and `engine/combat_sambo.py` reuse the canonical fight engine
  and action legality gate. Do not build a second simulator for either sport.
- Gym membership, team sparring, coaching and grading all route through
  `T) Coach` / Gym & Team. Lifestyle must not grow a duplicate gym menu again.
- Each sport owns domestic, continental and World results. Small countries skip
  artificial Regionals; larger federations can retain regional opens. Continental
  championships run once per year and route by country to European, Pan-American
  or Asian Championships. Boxing, Wrestling and Judo also run a four-year Olympic
  path. National-team status is sport-specific.
- Active focus is an exclusive UI/booking gate: MMA focus exposes only MMA
  fights/calendar, while a side focus exposes only that sport. A scheduled
  registration blocks focus changes until cancellation or resolution.
- `calendar_entries()` owns absolute side-sport dates and signup windows;
  `check_scheduled_competition()` resolves the registered bracket on its event
  week. Every side bout writes sport, event, week, opponent, ruleset, level,
  stats and mode to `fight_history`.

## Fame / media / nicknames (1.27 source of truth)

- `notoriety.py` owns bounded Fame changes, decay, bout exposure and media tier.
  Followers are audience size, Press Hype is temporary heat, Reputation is
  professional respect, and Legacy is career achievement.
- `story.press_conference` and `story.post_fight_interview` consult media tier.
  Do not show routine media scenes for amateurs or low-end pro prelims.
- `nicknames.py` owns the 144-name catalog, eligibility and org duplicate guard.

## Events (1.23 source of truth)

Prefer `require` flags over title-keyword gates. Title matching is legacy fallback
only; Phase 3 fixed the `"upgrades"` -> `"grades"` substring bug by using word
boundaries for school terms.

`events.context_pack()` exposes existing career state to the event DSL. New content
may gate on streak, camp/international camp, booking, teammate, specialty gym,
manager, named org, followers, debt, sponsor count and relationship ranges. Add a
requirement to `events.eligible()` + `validate_event_pack()` together; do not invent
JSON keys that are never interpreted.

`data/events_v123.json` is the Phase-3 pack: 60 contextual cards across wins,
losses, injuries, camps, money, gyms, teammates, family, media and career
progression. `events.validate_event_pack()` must stay clean before release.

Event rendering is phone-safe in `events.handle_event()`: title, description, why,
choices and effect summaries all wrap to <=44 columns. Keep legacy A/B/C parsing
until every old pack is migrated.

## What "bigger change" means here

Add a policy module or a data pack. Do not fork `simulate_fight` or the Fighter dataclass unless the fight itself is the feature.

## World (1.28)

Named orgs keep belts on `FighterPool.belts` (`Org|Class`). NPC cards move a
strap, count defenses and append `title_history`. `promotion_events.py` owns
matchup memory and updates NPC form/history only when the dated card resolves.
Vacancy-driven merit movement can recruit proven fighters into UFC and rebalance
same-tier regional divisions. Qualified MMA amateurs replenish the professional
target; dedicated side-sport NPCs can remain amateur specialists for life.
Opening rosters are balanced per organization/division before cards are built.
Purses come from `orgs.ORGS` when the fighter has a named promotion. Life menu
is the short letter list only.

## 1.25 boundary: promotion truth, weight-camp truth, money truth

Three fragmented sources of truth were consolidated after the 1.24 human playtest:

1. **Promotion/title truth** — `organization` + active `org_contract` must agree. UFC title decisions use UFC-specific rank/history, never generic regional rank. Old-promotion belts become history on a new signing.
2. **Weight-camp truth** — booking starts a weight campaign. Structured nutrition changes real `walking_weight` over camp; the final water cut is only the remainder. Performance/balanced/bully strategy changes the target remainder and therefore cage size/risk.
3. **Money truth** — one recurring ledger is both displayed and applied. Cash and debt are distinct: negative wallet balances are converted into debt, loans/repayments change both sides explicitly, and passive income is limited to genuinely passive sources.

The 1.25 event layer is intentionally supplemental. Large legacy random-event rewards are stage-capped at display/application time rather than rewriting hundreds of historical JSON cards; repeated categories receive a selection penalty. Senior review should decide whether to keep this global guardrail or migrate old cards individually later.


## Long-world matchmaking / contracts / Phase 3 (1.30 source of truth)

- `promotion_events.py` owns semantic matchup roles, championship cadence, lifetime trilogy enforcement, fresh-challenger repair and completed event history. Never bypass the lifetime meeting ceiling just because recent matchup memory was pruned.
- `contracts.py` owns deal structure, negotiation and clause application. `people.py` supplies manager competencies; `memory.py` owns persistent promoter/matchmaker memory. Do not recreate these as disconnected story flags.
- `v08.scout_lines()` + the booked opponent feed real scouting/camp preparation. `career.camp_plan_advice()` chooses an opponent-aware focus; do not ask the player to manually identify information the game already knows.
- `phase3.py` owns gated fight-week/staredown/post-event/rivalry consequences. Routine fights must not receive major-fight ceremony.
- `legacy.py` owns current multi-belt state, lifetime title statistics, record book and Hall-of-Fame calculations. Hall-of-Fame logic must use lifetime counters rather than relying solely on the bounded recent title-lineage list.

---

## Repository organization (1.33)

Player/runtime imports must stay inside `mma_legend/`. Regression modules belong in
`tests/`; maintenance/simulation/release commands belong in `tools/`; current developer
continuity documents belong in `docs/current/`. Do not move test history back into the
runtime package merely to make `python -m mma_legend.tests_*` work — use
`python3 -m tests.runner` or a specific `python3 -m tests.tests_*` module.

`START.py` and `main.py` launch only the colocated `mma_legend` package. This is an
intentional invariant: never scan sibling old-version folders during startup.


## v1.34 navigation layer
The weekly UI is decision-first and intentionally flat in 1.36: Train / Rest / Fight / Amateur / Nutrition / Team / Life are direct actions; Fighter, Rankings, Calendar, Alerts, Timeline/Money and Save are separate browse-only entries. Browsing is time-free. Do not infer time from whole-object state diffs: submenus must explicitly set/return half/full time only after a completed action. Training returns an explicit success flag so cancelled/invalid input cannot advance time. Alerts persist until opened.


## v1.35+ presentation/orientation layer

`mma_legend/ux.py` is intentionally a reader of authoritative career state, not a new simulation owner. It may compose records, contracts, booked fights, camp state and amateur calendars into player-facing overview/calendar/help screens, but it must not independently advance weeks, resolve fights, change rankings or write parallel records. Fight Prep follows the same rule: informational pages are no-time views; mutation remains in the existing career/cut/booking systems.


## v1.38 living-career intelligence

`mma_legend/living_careers.py` is an **advisory intelligence layer**, not a new state owner. It persists fighter career motives and promotion personality, then supplies preferences to the canonical systems:

- `ai.py` still owns weekly NPC action intent.
- `promotion_events.py` still owns world card construction and matchup legality.
- `world.py` still owns roster movement, rankings and championships.
- `booking.py` still owns opponent selection for player offers.
- `contracts.py` still owns promotional contracts.

Living-career scores may change which legal option is preferred; they must never bypass hard eligibility, roster-floor, title or trilogy constraints.


## v1.39 combat-intelligence boundary

`mma_legend/combat_intelligence.py` is an **advisory combat layer**. It may observe bout actions/results, derive opponent preparation, recommend plans, weight legal choices, resolve contested scramble quality and suggest between-round adjustments. It must not become a second fight engine.

Ownership remains:
- `engine/fight.py`: legal action selection/resolution, positions, gas, scoring, damage, finishes and fight outcome.
- `engine/positions.py`: legal positional action graph.
- `damage.py`: body-map damage mechanics.
- `career.py`: player camp choice/start and weekly camp progression.
- `combat_intelligence.py`: knowledge/preparation/decision quality only.

A preparation bonus must be specific and capped. A wrestling camp can improve entry preparation; anti-wrestling can improve the takedown contest; neither may erase a large underlying skill gap. Scouting must never reveal exact hidden ratings at 0/20 read. FightOutcome decision telemetry is transient diagnostic data and not a parallel career ledger.

## Performance / education / specialist gyms (1.40–1.41)

- `performance.py` is the sole owner of supplement/PED active state and anti-doping flow. Legal supplements modify training/recovery/fight expression temporarily; never write permanent raw combat stats.
- `education.py` owns secondary/university progression. `systems17.graduate` is compatibility glue only.
- `gym_progression.py` owns passive specialist membership development. `amateur_sports.py` owns BJJ/Judo belt requirements and automatic promotion evaluation.
- Home specialist development is disabled while `intl_camp` is active; overseas camps remain owned by `camps.py`.
- `world.FighterPool.update_rankings()` owns promotion boards. Career UI may browse them but must never manufacture ranks.


## Taekwondo and kicking expansion (1.42)
Taekwondo uses the shared fight engine with a dedicated ruleset. `engine/taekwondo.py` defines three two-minute kyorugi periods and its legal action set; `engine/fight.py` owns scoring/action resolution, including turning-kick values and round wins. `amateur_sports.py` owns the career ladder and belts. This preserves one canonical combat simulator while allowing sport-specific rules.
