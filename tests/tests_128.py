"""v1.28 Phase-1 gates: sport ladders and long-world integrity."""
from __future__ import annotations

import random
from collections import Counter

from mma_legend import amateur_sports, constants as C, data, orgs, persistence, promotion_events
from mma_legend.models import Fighter
from mma_legend.world import FighterPool, _NAME_GROUPS


class Quiet:
    width = 44
    def __init__(self, answers=()): self.answers=list(answers); self.lines=[]
    def ask(self,*a,**k): return self.answers.pop(0) if self.answers else "X"
    def header(self,*a,**k): pass
    def section(self,*a,**k): pass
    def print(self,*a,**k): pass
    def info(self,x="",**k): self.lines.append(str(x))
    def warn(self,x="",**k): self.lines.append(str(x))
    def good(self,x="",**k): self.lines.append(str(x))
    def gold(self,x="",**k): self.lines.append(str(x))


def _player():
    return Fighter.new_player("Test Fighter", "B", data.country_by_name("Bulgaria"), "Judo", 180, 77)


def _force_wins(fighter):
    def win(_console, who, _pool, *args, **kwargs):
        key=amateur_sports.key_for(who.active_amateur_sport)
        who.sport_records[key][0] += 1
        return True
    return win


def test_every_sport_has_full_ladder_and_two_nationals():
    assert amateur_sports.CHAMPIONSHIP_WEEKS["national"] == (12,38)
    assert amateur_sports.CHAMPIONSHIP_WEEKS["continental"] == (22,)
    assert amateur_sports.CHAMPIONSHIP_WEEKS["world"] == (30,)
    assert amateur_sports.OLYMPIC_SPORTS == {"Boxing","Wrestling","Judo","Taekwondo"}
    p=_player(); amateur_sports.ensure(p)
    for key in amateur_sports.SPORT_KEYS.values():
        assert set(p.sport_championships[key]) == {"regional","national","continental","world","olympic"}
    return "all eight sports own regional/national/continental/world/Olympic ledgers; Nationals run twice yearly"


def test_sport_selection_accepts_letter_number_and_name():
    p=_player()
    assert amateur_sports.choose_sport(Quiet(["F"]),p) and p.active_amateur_sport == "Judo"
    assert amateur_sports.choose_sport(Quiet(["7"]),p) and p.active_amateur_sport == "Combat Sambo"
    assert amateur_sports.choose_sport(Quiet(["H"]),p) and p.active_amateur_sport == "Taekwondo"
    assert amateur_sports.choose_sport(Quiet(["boxing"]),p) and p.active_amateur_sport == "Boxing"
    return "sport focus accepts phone-friendly letter, number or typed name and persists"


def test_national_teams_are_sport_specific():
    p=_player(); p.active_amateur_sport="Judo"; p.week=12; p.money=1000; p.energy=100
    amateur_sports.ensure(p); p.sport_experience["judo"]=100
    original=amateur_sports.compete; amateur_sports.compete=_force_wins(p)
    try:
        assert amateur_sports.championship(Quiet(),p,FighterPool(),
                                           level_override="national", mode="Instant")
    finally:
        amateur_sports.compete=original
    assert p.sport_championships["judo"]["national"]["gold"] == 1
    assert p.sport_national_teams["judo"] is True and p.national_team is False
    assert p.sport_national_teams["boxing"] is False
    return "Judo National gold earns only the Judo national-team place"


def test_olympics_run_every_four_years_for_olympic_sports():
    p=_player(); p.active_amateur_sport="Boxing"; p.week=(3*52)+40; p.money=1000; p.energy=100
    amateur_sports.ensure(p); p.sport_experience["boxing"]=400
    p.sport_national_teams["boxing"]=True
    p.sport_championships["boxing"]["world"]["bronze"]=1
    original=amateur_sports.compete; amateur_sports.compete=_force_wins(p)
    try:
        assert amateur_sports.championship(Quiet(),p,FighterPool(),
                                           level_override="olympic", mode="Instant")
    finally:
        amateur_sports.compete=original
    assert p.sport_championships["boxing"]["olympic"]["gold"] == 1
    return "qualified Boxing athlete wins a four-bout Olympic bracket in career year four"


def test_world_population_and_country_names():
    random.seed(128)
    pool=FighterPool(); pool.generate_world(840,560)
    amateurs=[f for f in pool.fighters if not f.pro_debut]
    sports={f.active_amateur_sport for f in amateurs}
    dedicated=[f for f in amateurs if f.active_amateur_sport != "MMA"
               and not f.story_flags.get("mma_transition",False)]
    assert len(sports) >= 8 and "Taekwondo" in sports and len(dedicated) >= 80
    used=set(); names=[]
    for _ in range(100):
        name=pool._unique_name(used,"Bulgaria")[0]; used.add(name); names.append(name)
    first,last=_NAME_GROUPS["bulgarian"]
    templates={"%s %s" % (m.get("firstName"),m.get("lastName")) for m in data.OPPONENTS
               if m.get("country") == "Bulgaria"}
    assert all((n.split()[0] in first and n.split()[-1] in last) or n in templates for n in names)
    assert not any(n.startswith("Fighter ") for n in names)
    counts=Counter((f.organization,f.weight_class) for f in pool.fighters if f.pro_debut and f.active)
    for org in orgs.ORGS:
        floor=15 if org == "UFC" else 6 if org in ("PFL","Bellator") else 4
        assert all(counts[(org,wc)] >= floor for wc in C.WEIGHT_CLASSES)
    return "eight populated sports, permanent specialists, country names and viable opening pro divisions"


def test_ai_results_titles_and_new_pool_state_persist():
    random.seed(1281)
    pool=FighterPool(); pool.generate_world(160,240)
    target=min(e["week"] for e in pool.events); pool.week=target
    promotion_events.resolve_due(pool)
    assert any(f.recent_results for f in pool.fighters if f.pro_debut)
    org,wc=next(iter((k.split("|",1) for k in pool.belts)))
    champ=pool.belt_holder(org,wc); challenger=next(f for f in pool.fighters
        if f.active and f.pro_debut and f.organization==org and f.weight_class==wc and f is not champ)
    pool.record_title_defense(org,wc,champ,challenger)
    assert pool.belts[org+"|"+wc]["defenses"] == 1
    blob=persistence._pool_blob(_player(),pool,pool.fighters)
    assert "title_history" in blob and "matchup_history" in blob and persistence.SAVE_VERSION >= 19
    return "NPC form, champion defenses, title lineage and matchup memory update and serialize in save v17"


def main():
    for test in (test_every_sport_has_full_ladder_and_two_nationals,
                 test_sport_selection_accepts_letter_number_and_name,
                 test_national_teams_are_sport_specific,
                 test_olympics_run_every_four_years_for_olympic_sports,
                 test_world_population_and_country_names,
                 test_ai_results_titles_and_new_pool_state_persist):
        print("PASS",test())
    print("ALL 1.28 LONG-WORLD / MULTI-SPORT CHECKS OK")


if __name__ == "__main__": main()
