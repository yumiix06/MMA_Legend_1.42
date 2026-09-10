"""Deterministic long-career audit for the living MMA/multi-sport world."""
from __future__ import annotations

import collections
import json
import random
import statistics
import time

from mma_legend.world import FighterPool


def run(years: int = 20, amateurs: int = 840, pros: int = 560,
        seed: int = 12801) -> dict:
    random.seed(seed)
    pool = FighterPool()
    pool.generate_world(amateurs, pros)
    initial = {f.fid: (list(f.recent_results), int(f.current_streak)) for f in pool.fighters}
    pairs = collections.Counter()
    pair_details = {}
    title_weeks = collections.defaultdict(list)
    event_counts = collections.Counter()
    bout_counts = collections.Counter()
    duplicate_weeks = 0
    invalid_titles = 0
    started = time.time()

    for _ in range(max(1, int(years)) * 52):
        open_ids = []
        for event in pool.events:
            if event.get("status") != "scheduled":
                continue
            for bout in event.get("bouts", []):
                if bout.get("status") != "scheduled":
                    continue
                open_ids.extend(x for x in (bout.get("red_id"), bout.get("blue_id")) if x)
                if bout.get("title"):
                    holder = pool.belt_holder(event["org"], bout["weight_class"])
                    if holder is None or holder.fid not in (bout.get("red_id"), bout.get("blue_id")):
                        invalid_titles += 1
        duplicate_weeks += int(len(open_ids) != len(set(open_ids)))

        due = [e for e in pool.events if e.get("status") == "scheduled"
               and int(e.get("week", 0)) <= pool.week + 1]
        for event in due:
            event_counts[event["org"]] += 1
            for bout in event.get("bouts", []):
                if bout.get("status") != "scheduled" or "PLAYER" in (bout.get("red_id"), bout.get("blue_id")):
                    continue
                a, b = str(bout["red_id"]), str(bout["blue_id"])
                pair_key = "|".join(sorted((a, b)))
                pairs[pair_key] += 1
                red, blue = pool.get_by_id(a), pool.get_by_id(b)
                pair_details[pair_key] = {
                    "fighters": "%s / %s" % (
                        getattr(red, "name", a), getattr(blue, "name", b)),
                    "org": event["org"], "weight_class": bout["weight_class"],
                }
                bout_counts[event["org"]] += 1
                if bout.get("title"):
                    title_weeks[(event["org"], bout["weight_class"])].append(int(event["week"]))
        pool.simulate_week()

    active = [f for f in pool.fighters if f.active]
    active_pros = [f for f in active if f.pro_debut]
    active_amateurs = [f for f in active if not f.pro_debut]
    idles = sorted(int(f.idle_weeks) for f in active_pros)

    def percentile(values, q):
        if not values:
            return 0
        return values[min(len(values) - 1, int((len(values) - 1) * q))]

    gaps = []
    for weeks in title_weeks.values():
        ordered = sorted(set(weeks))
        gaps.extend(b - a for a, b in zip(ordered, ordered[1:]))
    olympians = 0
    for f in pool.fighters:
        for table in (getattr(f, "sport_championships", None) or {}).values():
            if isinstance(table, dict) and sum((table.get("olympic") or {}).values()):
                olympians += 1
                break

    return {
        "years": int(years), "runtime_seconds": round(time.time() - started, 2),
        "fighters_total": len(pool.fighters), "active_pros": len(active_pros),
        "active_amateurs": len(active_amateurs),
        "dedicated_side_athletes": sum(
            f.active_amateur_sport != "MMA" and not (f.story_flags or {}).get("mma_transition", False)
            for f in active_amateurs),
        "sport_population": dict(collections.Counter(f.active_amateur_sport for f in active_amateurs)),
        "org_population": dict(collections.Counter(f.organization for f in active_pros)),
        "career_goals": dict(collections.Counter(getattr(f, "career_goal", "") for f in active_pros)),
        "career_personalities": dict(collections.Counter(getattr(f, "career_personality", "") for f in active_pros)),
        "career_goal_changes": sum(len(getattr(f, "career_log", None) or []) for f in active_pros),
        "events": dict(event_counts), "bouts": dict(bout_counts),
        "idle_weeks": {"median": percentile(idles, .5), "p90": percentile(idles, .9),
                       "p99": percentile(idles, .99), "max": max(idles or [0])},
        "form_updated": sum(list(f.recent_results) != initial[f.fid][0]
                            for f in pool.fighters if f.fid in initial),
        "streak_updated": sum(int(f.current_streak) != initial[f.fid][1]
                              for f in pool.fighters if f.fid in initial),
        "matchups": {"unique": len(pairs), "rematches": sum(v >= 2 for v in pairs.values()),
                     "maximum_pairings": max(pairs.values() or [0]),
                     "most_repeated": [dict(pair_details.get(k, {}), meetings=v)
                                       for k, v in pairs.most_common(5)]},
        "titles": {"fights": sum(len(v) for v in title_weeks.values()),
                   "divisions": len(title_weeks),
                   "median_gap": statistics.median(gaps) if gaps else 0,
                   "p90_gap": percentile(sorted(gaps), .9) if gaps else 0,
                   "lineage_entries": len(pool.title_history)},
        "olympic_medalists": olympians,
        "duplicate_booking_weeks": duplicate_weeks,
        "invalid_title_slots": invalid_titles,
        "ufc_champion_mismatches": sum(
            pool.champions.get(wc) is not pool.belt_holder("UFC", wc)
            for wc in pool.champions),
    }


def main() -> None:
    print(json.dumps(run(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
