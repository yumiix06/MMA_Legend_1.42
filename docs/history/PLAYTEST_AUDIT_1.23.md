# 1.23 playtest forensic audit — Francisco Ferrari, week 205

These saves are diagnostic references only. They are not compatibility targets and must
not ship in a future release.

## Highest-confidence logic faults

1. **Autosave world truncation:** `save.json` / `save_auto.json` hold 520 NPCs while the
   same-week manual save holds 907. The debug header still says 907, and the loader does
   not reseed a 520-NPC pool. Loading autosave therefore changes future rankings,
   matchmaking and world simulation.
2. **Autosave occurs before post-fight finalization:** same-week manual and autosave
   disagree on KO-loss/takedown/body-shot career counters and perk grant. The fight
   autosave was written inside `fight_result()` before caller-level perk bookkeeping.
3. **Career ranking/story contradiction:** a 0-2 pro is #1 in Balkan Combat and carries
   prospect/pro/contender/journeyman/title-contender tags simultaneously. Ranking was
   too dependent on hidden ability/fame, while story chains used total/amateur wins.
4. **Matchmaking experience/cross-promotion logic:** the old pro filter could allow a
   0-1 fighter against a 6-0 opponent, and local/regional promotion cards explicitly
   allowed candidates assigned to other organizations.
5. **Contract semantics:** the exclusive Balkan deal has zero win and show purse fields.
6. **Fight ledger observability:** KO/TKO summaries do not contain the exchange sequence,
   AI rationale, pre-finish energy/damage or exact displayed commentary. Several
   stoppages therefore cannot be reconstructed from final stats.
7. **Performance rating telemetry is inert:** all supplied career ledger rows store 0.0.
8. **Perk system needs a real effects audit:** perks are awarded (`film_room`, `glass` in
   this playtest), but current source use is concentrated in the award module rather than
   combat/system consumers.

## Data capture required for future playtests

- exact rendered screen lines;
- exact prompt + player input;
- screen/menu breadcrumb;
- save phase marker;
- full world vs saved world counts;
- matchmaker candidate set and rejection/selection reason;
- event eligible pool and weighted selection reason;
- fight plan and opponent snapshot;
- every exchange's action, legal fallback, hit chance/RNG roll, position, gas, damage,
  momentum, control and body map;
- AI top action weights / selection reason;
- finish event plus final stats/body maps;
- automatic contradiction audit;
- single ZIP export for upload.

The active 1.24 WIP branch implements this capture layer and the high-confidence fixes
above. See `VERSION_HISTORY.md` for exact code paths and test evidence.
