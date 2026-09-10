# MMA Legend 1.36.1 Release Audit

## Scope
Focused menu cleanup requested after v1.36.0. No simulation redesign. Save format remains v17.

## Player-facing changes
- Local amateur fight booking moved from the weekly Fight route into Amateur.
- Unbooked amateur careers no longer show Fight on the weekly action list.
- Weekly menu descriptions and browse/time labels removed.
- Restrained emoji set on primary actions; decorative section markers removed.
- Tutorial/help updated to match the flatter navigation.

## Safety checks
- v1.36.1 menu relocation regression: PASS
- v1.36 navigation/back-out regression: PASS
- v1.35 and v1.34 UI regression: PASS
- v1.33/v1.32 maintenance regression: PASS
- v1.30 release milestone suite: PASS
- v1.29 amateur calendar suite: PASS
- v1.28/v1.27/v1.26 sport/combat suites: PASS
- system self-check: ALL SYSTEMS OK
