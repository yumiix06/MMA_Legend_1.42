# SYSTEM MAP — read this before touching the game

This is the memorize-it document. Not flavour. If a future session
starts cold, read docs/current/ARCHITECTURE.md then this.

Current version: 1.42.0
Save format: JSON v19
Package: mma_legend/  Launchers at zip root: START.py, main.py

---

## Player week (the only loop that matters)

app.game_loop
  1. If booked date is due → fights.booker_night
  2. Dashboard + news + manager note
  3. Action from _actions_for:
       A train    B rest    C fight/inbox    D amateur (hidden after pro)
       N food     T coach   E life           H stats
       I rankings J save    K retire         G turn-pro when ready
       Z timeline (view only, does not spend the week)
  4. If the action spends the week → Fighter.advance_week
       cut (damage, injury, costs, school, body)
       systems17 graduate / audit
       contracts.tick, dwcs.tick, aging, coach offer
       identity.sync
       energy/health/nutrition drift, camp tick
  5. pool.simulate_week
       NPC age/skills, roster repair, scheduled cards, seven amateur ecosystems,
       championships, rankings, belts and title lineage
  6. Only after a spent week: story.weekly_story OR events via ai.pick_event

View, save, invalid, cancel and Back actions neither advance time nor roll events.

---


## Physiology / nutrition / cut source of truth (1.24)

`physiology.py` owns physical ceilings and fight-night expression. Technical skill can
reach 100 in every division; strength/KO/cardio/speed ceilings vary by weight class and
physique. `effective_stat()` applies nutrition, health, cut condition, bodyfat, injuries
and persistent damage without rewriting learned skill.

`cut.tick_body()` reads structured `data/nutrition.json` weekly mass deltas. It must not
infer physiology from words inside a meal-plan name. `physiology.nutrition_week()` owns
quality/recovery/cut-health effects. `cut.weigh_in()` is the only fight-week scale/cage
weight resolver and never overwrites walking weight.

`telemetry.py` owns bounded UI/input/system traces and real-player fight exchange traces.
`persistence.export_playtest_bundle()` exports the canonical world plus diagnostics;
headless balance simulations must stay telemetry-light.

## Who is allowed to write what

organization, org_contract
  writers: orgs.sign_org, contracts.sign, contracts.release
  reconciler: identity.sync (weekly + load)
  NOT a writer: booking.set_room  (band only)

room
  matchmaking band: local / regional / national / mid / dwcs / ufc
  identity.ORG_ROOM maps named org → band

walking_weight, bodyfat
  weekly: cut.tick_body
  plan pick: cut.apply_plan_now
  events: events.apply_effects keys walking_weight / bodyfat
  fight night: fights._apply_weight_cut + cut_fatigue
  load crash: identity.repair_save

UFC signed flag
  only dwcs.resolve after a graded performance the player accepts
  load walks back premature UFC (wins < 8 and UFC bouts < 3)

---

## Combat

engine/fight.simulate_fight
  periods × ticks. Period duration comes from the active ruleset.
  Position string + top_is_player. LEGAL actions from engine/positions.py.
  Ruleset.allows_action is the final sport gate for menu, AI and resolver.
  Standing range: outside / kicking / boxing / pocket.
  Reach + Distance Management contest the band; reach never adds damage.
  Striking Defense opposes standing accuracy; Submission Defense opposes
  setup and finish. Fight plan stores range + movement/guard/counter defence.
  Gas from fighter.energy and cardio. _gas_mod below 55/35/18.
  Ride clock: ground holds consume real seconds, work/escape exchanges.
  Watch mode asked at the cage (_pick_watch_mode): Quick / Round / Full / Sim.
  Scoring: engine/scoring.py 10-point-must. ADCC points when grappling_only.
  FightStats.control_ticks still used for grades (seconds // 8).

combat.py is the wrapper fight_mma / fight_grappling / post-fight card.

`amateur_sports.py` owns separate side-sport records, XP, weight labels,
championship medals and BJJ/Judo grading. `promotion_events.py` owns dated pro
cards, slots, event history and replacements. `notoriety.py` owns fame mutation
and media eligibility; `nicknames.py` owns public fighter names.

117 playable technique rows after broad concepts are filtered from
data/techniques.json. Every row gets structured action/role/target/kind metadata
in techniques.py. Specific reactions are passive bonuses and never buttons.
Starting kit comes from constants by amateur_discipline. Coach / drop-in gym
can teach more.

15 weighted skills: striking, kicks, grappling, submissions, ground control,
KO power, striking defence, takedown defence, submission defence, distance
management, cardio, strength, speed, durability, fight IQ.

Positions: stand, clinch, closed/open guard, half guard, side, north-south,
mount, back, turtle, front headlock and leg entanglement.

15 archetypes in fighter_archetypes.json. 42 combat moments.
10 auto-perks, cap 3 (cut_artist, grinder, first_min, wrestle_chain,
body_work, iron_chin, home_crowd, film_room, late_gas, glass).

---

## Career ladder (real)

Amateur
  One active focus controls D hub and weekly C action; inactive sports are hidden
  MMA focus: local MMA bracket/fight + MMA championship calendar only
  Side focus: local selected-sport match + selected-sport calendar only
  Side bouts: Play / Live sim / Instant, all written to tagged dated history
  Scheduled registration stores sport + level + absolute due week (migrated forward in save v17)
  Sports: MMA plus BJJ/No-Gi, Boxing, Kickboxing, Wrestling, Judo and Combat Sambo
  Domestic: small countries skip artificial Regionals; larger federations may use them
  Continental: exactly one/year, routed to European / Pan-American / Asian by country
  World: one/year; Olympics every fourth career year for Boxing, Wrestling and Judo
  National-team places and medal tables belong to the selected sport
  Same-day gas after match 1 in a bracket
  v08 medals + national team + turn-pro gate

Pro booking
  C is inbox_night. Requires a manager. Exclusive contract is the gate.
  Offers from orgs.inbox → contracts.can_accept
  DWCS invite is a feeder exception (dwcs.py). 6 wins + 3-streak + fame 10.
  Grade: finish or dominant decision signs. Grind does not. Player can refuse.
  Direct UFC: orgs.direct_ufc_chance, hard gates (~9-2, fame 30, streak 4), cap ~12%.

Named orgs (orgs.ORGS)
  UFC PFL Bellator BRAVE CF KSW Cage Warriors Balkan Combat LFA Road FC ARES FC ACA EFC
  Home org from country (Serbia → Balkan Combat)

World
  Standard FighterPool starts 840 amateurs + 560 pros; active targets are
  840 amateur and 620 professional to survive long careers
  UFC rankings: champion + 1-15, player needs 3 UFC bouts to be numbered
  Org boards: per promotion per class (identity + world.update_rankings)
  Belts: pool.belts["Org|Class"] = {name, fid}. Persist in save pool.belts
  Title offers: identity.title_shot → orgs.stamp_title. Inbox gold line.
  booker_night copies booked.title onto _pending_title before clearing the date.
  NPC movement: vacancy/merit transfers, including earned UFC recruitment;
  same-tier moves repair thin regional divisions without stripping champions
  Pro cards update NPC form/streak/history and persistent matchup memory
  Titles persist reign start, defenses and lineage across all organizations
  Purses: orgs.ORGS["x"]["purse"] when named; room table only as fallback
  Booked purse is not overwritten by the old tier*200 formula
  Matchmaking roles: showcase, gatekeeper, contender, eliminator, rebuild, activity, rematch, title
  Hard lifetime trilogy ceiling survives recent-memory pruning
  Champions stay out of ordinary non-title bouts; overdue belts can gain a second title slot
  Saturated champion divisions import a fresh same-tier challenger rather than allowing fight #4

---

## People / contracts / memory (1.30)

people.Person frozen records. Rapport on fighter.people_rel. Managers expose
negotiation, scouting and career-management competencies in addition to personality.
Roles: promoter (one per org), manager (sign/fire, cut %, purse), matchmaker (offer
tags, quirks), media, gym coach. Manager office is also the fallback when C is
pressed with no manager.

contracts.py owns purse/show economics, fight count, term, exclusivity and negotiated
clauses (short-notice premium, title escalation, rematch option). memory.py owns
persistent promoter/matchmaker memories such as accepted/declined fights, cancellations,
missed weight, difficult negotiations, short-notice help and performance context.

---

## Events and story

511 random cards across events.json + v06 v07 v08 v14 v15 v19 v111 v121 v123 v125 v127.
Eligibility: events.eligible. Prefer declarative require{} gates over title keywords.
Phase-3 context gates use existing Fighter state: streak, booked/camp/intl-camp,
teammate, specialty gym, manager, named org, debt, followers, sponsor count and
family/friends/coach/partner/rival relationship ranges. No save fields were added.
AI pick: ai.event_score weights life/gym/money/media/injury by camp/broke/hurt.
`events.validate_event_pack()` is a release gate: IDs, requirement names,
min/max contradictions, effect keys, choice keys and trigger chance ranges.
The v123 pack contains 60 cards in ten groups: wins, losses, injuries, camps,
money, gyms, teammates, family, media and career progression.

10 story chains in story_chains.json (2-step arcs):
  first_real_test, callout, injury_fork, sponsor_interest, turn_pro_arc,
  nt_pressure, rematch_noise, ufc_notice, title_buildup, comeback_arc
Story beats fire before a random event that week.

School events require school_status in (school, uni). Graduation at 18.

---

## Phase 3 presentation / legacy (1.30)

phase3.py gates major fight-week presentation, tale of the tape, staredown, contextual
post-event bonuses/ranking consequences and rivalry creation. completed event rows are
updated so card summaries can show championship changes, bonuses and important results.

legacy.py owns multi-belt title stats, Hall-of-Fame scoring/induction and the record book.
Lifetime title counters remain authoritative even when recent title_history is capped.

## Body

natural_weight — creation size, rebound target
walking_weight — weekly scale
bodyfat — floor by physique (Heavy-built 12% out of camp)
fight_weight_class — home division, official 8 MMA classes for pro cards
meal_plan — name string; JSON weight_change is live as of 1.13
cut_fatigue — fight-night tax, fades out of camp

Kamil Mensah reference save (week 131, playtester):
  Serbia, Heavy-built, natural 93kg, was walking 80kg at 5% bf
  amateur 9-5-1, pro 4-0, fame 69, manager Harbor
  wrongly UFC after 3rd pro win while already Balkan Combat
  1.13+ load: home org Balkan Combat, bodyfat lifted, walk fills

---

## Files you actually edit for features

Identity / org / dashboard     identity.py orgs.py booking.py ui.py world.py
Body / food                    cut.py career.nutrition_menu events data
Booking / DWCS                 fights.py dwcs.py contracts.py people.py
Combat                         engine/fight.py engine/positions.py engine/scoring.py
Week loop / menus              app.py career.py
Save                           persistence.py models.Fighter
Events                         events.py ai.py data/events_*.json
Tests                          tests_123 events/release UI, tests_122 tactical UI,
                               tests_120 identity/body, tests_130 belts/purses,
                               tests_19 contracts, tests_110 DWCS, tests_18 legality

Do not add a second writer for organization. Do not ask fight-detail at
create-a-fighter. Do not use PROMOTION_TIERS for display.

---

## Developer layout / commands (1.33)

- Runtime: `mma_legend/`
- Regression: `tests/`; all suites: `python3 -m tests.runner`
- Self-check: `python3 -m mma_legend.diagnostics`
- Save audit/repair copy: `python3 -m tools.save_repair <save> [--write]`
- Long-world audit: `python3 -m tools.world_audit`
- Batch career probe: `python3 -m tools.sim_careers`
- Clean ZIP: `python3 -m tools.build_release`

The test runner executes either `main()` or `run()` and treats a missing entry point as a
failure. Release packaging excludes generated caches/logs/saves even when diagnostics or
tests created them in the working tree.


## UI/QoL (1.36)
- `app.py`: simple startup menu, three-page tutorial, flat weekly routing and explicit NO-TIME career-info shortcuts.
- Time ownership rule: browse-only menus never advance the calendar; Team/Life/People/School/Medical actions must explicitly mark half/full time after completion. Whole-object state comparison is not a valid time-spend signal.
- `ux.py`: calendar, next-objective helpers, lightweight compatibility hints and quick controls. The larger 1.35 Career hub remains implementation-compatible but is no longer the primary weekly route.
- `ux.py`: next-objective derivation, career overview, fighter sheet, unified calendar, contextual help/tutorial hints. Read-only by design.
- `matchroom.py`: booked-fight Fight Prep hub; booking/signing ownership is unchanged.
- `timeline.py`: quick phase overview plus paged/filterable ledger browser. `fight_history` remains authoritative.
- `fights.py`: tactical gameplan card/recommendation, watch-mode default and consolidated post-fight summary; canonical combat still lives in `engine/fight.py`.


### Living Careers (v1.38)
`living_careers.py` -> persistent NPC goal/personality + promotion profiles -> advisory weights consumed by `ai`, `booking`, `promotion_events`, and `world`. It does not write contracts, rankings, cards or belts directly.


### Combat Intelligence (v1.39)
`combat_intelligence.py` -> opening plan / live reads / camp prep / score + damage-aware adjustments / chain-wrestling + scramble quality -> consumed by `engine/fight.py`. Canonical action legality and resolution remain in `engine/fight.py` + `engine/positions.py`; this module only biases legal choices and contested outcomes.

## Specialist gym ownership (1.41)

`career.specialty_gym_menu` selects membership and shows syllabus/status.
`gym_progression.tick` runs once per spent home week and owns passive technique XP/mat time.
`amateur_sports.train_belt` + `auto_promote_belt` own BJJ/Judo grade state.
`camps.py`/`intl_camp` suppress home-gym ticks while abroad.
Promotion rankings remain `FighterPool.update_rankings()` world state; UI only reads/browses them.


## Taekwondo / kicking ownership (1.42)
- `engine/taekwondo.py` owns Taekwondo ruleset metadata; canonical action resolution remains in `engine/fight.py`.
- `amateur_sports.py` owns Taekwondo competition records, calendar/eligibility, weight labels and belt requirements.
- `gym_progression.py` owns passive dojang development, technique exposure/mastery and automatic belt promotion.
- `data/techniques.json`, `data/gym_and_promotions.json` and `data/events_v142.json` own authored Taekwondo content.
- New kicking actions are available to MMA/kickboxing only through the shared legality/technique gates; they do not create a second combat engine.
