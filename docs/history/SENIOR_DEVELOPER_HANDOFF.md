# SENIOR DEVELOPER HANDOFF — MMA Legend 1.25.0

> Current status: this remains the historical junior handoff. The maintained
> baseline is now v1.29.0; read `RELEASE_AUDIT_1.29.0.md` and the top of
> `VERSION_HISTORY.md` before making new changes.

> Historical handoff record. Senior review is complete: the candidate was
> corrected and approved as v1.25.1. See `SENIOR_REVIEW_1.25.1.md`.

Read this before changing code.

## Your role

You are the senior/lead developer receiving a junior patch built from the stable 1.24.0 release and one human v1.24 autosave. Treat 1.25.0 as a **review candidate**, not a trusted baseline until you validate it yourself.

## First files to read

1. `PLAYTEST_AUDIT_1.24.md` — what the human tester actually exposed.
2. Top `1.25.0` section of `VERSION_HISTORY.md` — exact files/functions changed, rationale and validation.
3. `SYSTEM_MAP.md` + `ARCHITECTURE.md` — current sources of truth.
4. `CHANGELOG.md` — player-facing summary.

## Required validation before accepting 1.25

Run from the extracted package:

```bash
python -m mma_legend.tests
python -m mma_legend.tests_194
python -m mma_legend.tests_125
python -m mma_legend.diagnostics
```

Expected new-suite result: `ALL 1.25 JUNIOR-HANDOFF CHECKS OK`. Diagnostics should report v1.25.0, 487 events, save/load/booking/people/combat green.

The junior environment could not complete the full long `tests_194` run. A reduced 80-fight/style mirror smoke produced Boxing 53%, Wrestling 48%, BJJ 48%, Muay Thai 53%, with symmetry source checks passing. **Do not skip the full fairness suite locally.**

## High-priority code review

### UFC/title/contracts

Review `identity.title_shot`, `identity.sync/repair_save`, `contracts.active/sign/can_accept`, `orgs.sign_org`, `world.update_rankings`. Confirm:

- UFC never uses generic `org_rank` as title eligibility;
- first UFC bout after DWCS cannot be a title fight;
- a loss cannot immediately generate another title shot;
- visible named promotion and active contract cannot disagree;
- UFC exclusivity blocks rival organizations;
- old-promotion belts become former history.

Thresholds (top 3, 3 UFC bouts, 2 UFC wins, +2 streak) are design choices and may be tuned, but do not reintroduce generic-rank leakage.

### Weight/nutrition

Review `cut.WEIGHT_STRATEGIES`, `ensure_weight_campaign`, `tick_body`, `weigh_in`, and booking initialization. Make sure real camp mass loss, final water cut, rehydration and cage size form one loop. A weight bully should receive size by staying heavier and accepting risk/gas tax—not a flat hidden power bonus.

### Economy/debt

Review `economy.weekly_breakdown`, `cut.weekly_costs`, `systems15.take_loan/repay_debt/tick_debt/clamp_money`. The display and transaction must stay identical. Tune interest if desired; current rate is inherited and not claimed as balanced.

### Events/media

Review `events.balanced_event_effects`, `ai.event_score/pick_event`, and `data/events_v125.json`. 36 cards were added, with 12 media cards replacing manual media as the primary path. The global effect caps are intentionally conservative but should be assessed against cinematic event design.

### UI pacing / sponsorship QoL

Review `GameConsole.continue_prompt` on the actual iOS runtime. It intentionally does not trust `isatty()`. Supplement sponsors currently use keyword matching; replace with structured sponsor metadata if you want this to scale.

## Do not do these accidentally

- Do not include the old playtest save in a release package.
- Do not promise old-save compatibility; saves are debug references only.
- Do not restore a manual media weekly action unless there is a clear gameplay loop for it.
- Do not let maintenance/bulk nutrition secretly remove fight weight.
- Do not tune core combat around the simplified persona-career probe without validating real matchmaking.
- Do not bless 1.25 until the full long fairness suite completes.

## Recommended next step after review

If validation passes, use 1.25 as the next playtest baseline and request the new playtest bundle whenever possible. The next audit should focus on real UFC matchmaking/title progression over 5–10 UFC bouts, weight-strategy choice frequency/outcomes, economy runway/debt, event repetition, and whether sponsor perks feel useful without becoming free-power exploits.
