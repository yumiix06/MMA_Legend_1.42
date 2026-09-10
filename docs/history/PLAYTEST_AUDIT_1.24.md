# v1.24 PLAYTEST AUDIT -> v1.25 JUNIOR PATCH

Source artifact: the supplied `save_auto(3).json` from v1.24.0. The original save is not bundled and was not modified.

## Reproduced contradictions

1. **UFC identity split** — visible organization UFC, exclusive six-fight paper, but contract `org` was blank. Booking therefore described the fighter as a free agent and could surface ACA/KSW/LFA/Cage Warriors offers.
2. **Premature UFC title logic** — generic promotion rank was #1 while UFC-specific rank was #7; a title-offer flag existed and the first UFC fight in history was five rounds. Generic rank leaked into title selection.
3. **Stale LFA belt** — active belt field still said LFA after the UFC signing.
4. **Economy split-brain** — weekly displayed ledger and actual deducted living-cost model did not use the same income/expense set; side-job income appeared passively in the ledger, and debt/cash presentation was difficult to interpret.
5. **Weight-camp opacity** — walking weight was ~87.9 kg for a Middleweight booking but the UI did not show how much real mass had been lost during camp versus what remained for fight-week water.
6. **Sponsorship lacked utility** — multiple nutrition/supplement brands were signed but legal supplements still behaved like ordinary purchases.
7. **Reading pace** — long event/calendar screens could disappear on a timer before a phone player finished reading.

## After applying the v1.25 branch to the save in read-only diagnostics

- active contract: UFC; outside ACA date is blocked by exclusivity;
- current ranking reconciles to UFC #9 in the loaded 948-fighter world;
- stale LFA belt is no longer active and is retained as former history;
- `identity.title_shot()` returns no title shot;
- playtest audit explicitly reports the old premature-title flag rather than silently accepting it.

## Patch philosophy

The save is evidence, not a compatibility contract. New careers must be internally coherent. Load-time repair exists only for high-confidence contradictions (named UFC + blank exclusive contract, stale previous-promotion belt), not to preserve every historical mistake.
