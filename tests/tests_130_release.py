"""v1.30 milestone gates: Phase 1+2 completion, regional calendar and Phase 3."""
from __future__ import annotations

import random

from mma_legend import amateur_sports, career, contracts, cut, data, fights, identity, legacy, persistence, phase3, promotion_events, ui
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


class Quiet:
    width = 44
    def __init__(self, answers=()): self.answers=list(answers); self.lines=[]
    def ask(self, prompt="", *a, **k): self.lines.append(str(prompt)); return self.answers.pop(0) if self.answers else "A"
    def _add(self, value="", *a, **k): self.lines.append(str(value))
    print=info=warn=good=gold=header=section=_add
    def pause(self,*a,**k): pass
    def auto_pause(self,*a,**k): pass
    def continue_prompt(self, prompt="Press Enter to continue", *a, **k): self.lines.append(str(prompt))
    def read_pause(self,*a,**k): pass


def player(country="Bulgaria", sport="Judo"):
    p=Fighter.new_player("Release Test", "B", data.country_by_name(country), sport, 180, 77)
    p.fid="PLAYER"; amateur_sports.ensure(p); p.active_amateur_sport=sport
    return p


def test_region_specific_amateur_calendar():
    bg=player("Bulgaria","Judo"); bg.week=1; bg.sport_experience["judo"]=500; bg.sport_national_teams["judo"]=True
    bg.sport_championships["judo"]["continental"]["gold"]=1
    y=[e for e in amateur_sports.calendar_entries(bg,"Judo",2) if e["career_year"]==1]
    assert not [e for e in y if e["level"]=="regional"]
    assert len([e for e in y if e["level"]=="continental"])==1
    assert [e for e in y if e["level"]=="continental"][0]["name"].endswith("European Championships")
    us=player("USA","Boxing"); us.week=1; us.sport_experience["boxing"]=500; us.sport_national_teams["boxing"]=True; us.sport_championships["boxing"]["continental"]["gold"]=1
    uy=[e for e in amateur_sports.calendar_entries(us,"Boxing",2) if e["career_year"]==1]
    assert len([e for e in uy if e["level"]=="regional"])==2
    assert [e for e in uy if e["level"]=="continental"][0]["name"].endswith("Pan-American Championships")
    jp=player("Japan","Judo"); jp.week=1; jp.sport_experience["judo"]=500; jp.sport_national_teams["judo"]=True; jp.sport_championships["judo"]["continental"]["gold"]=1
    jy=[e for e in amateur_sports.calendar_entries(jp,"Judo",2) if e["career_year"]==1]
    assert [e for e in jy if e["level"]=="continental"][0]["name"].endswith("Asian Championships")
    return "small countries skip regionals; Europe/Pan-America/Asia route correctly"


def test_world_generation_and_matchmaking_roles_no_unhashable():
    random.seed(13001)
    pool=FighterPool(); pool.generate_world(140,100)
    assert pool.events
    roles={b.get("matchup_role") for e in pool.events for b in e.get("bouts",[])}
    assert roles & {"activity_fight","title_defense","title_eliminator","prospect_vs_gatekeeper","rebuild"}
    return "fresh world builds semantic promotion cards without Fighter-key crash"


def test_fourth_meeting_hard_block():
    random.seed(13002)
    pool=FighterPool(); pool.generate_world(40,80)
    org="LFA"; wc="Lightweight"
    names=[f for f in pool.fighters if f.pro_debut and f.organization==org and f.weight_class==wc][:3]
    if len(names)<3:
        return "thin fixture skipped safely"
    a,b,c=names
    pool.matchup_history[promotion_events._pair_key(a.fid,b.fid)]={"count":3,"last_week":pool.week-200}
    pair=promotion_events._best_pair(pool,org,wc,[a,b],"competitive")
    assert pair is None
    pair=promotion_events._best_pair(pool,org,wc,[a,b,c],"competitive")
    assert pair and set(pair) != {a,b}
    return "trilogies are the hard maximum when another opponent exists"


def test_stale_saturated_roster_refreshes_without_fourth_fights():
    pool=FighterPool(); pool.week=100
    fighters=[]
    for org,prefix in (("LFA","L"),("Balkan Combat","B")):
        for i in range(5):
            f=Fighter.new_npc("%s%s"%(prefix,i),data.country_by_name("USA")); f.fid="%s%s"%(prefix,i); f.pro_debut=True
            f.organization=org; f.weight_class=f.fight_weight_class="Lightweight"; f.pro_record=[5+i,2,0]; f.idle_weeks=10
            fighters.append(f)
    pool.fighters=fighters; pool.update_rankings()
    stuck=fighters[0]; stuck.idle_weeks=120
    for peer in fighters[1:5]:
        pool.matchup_history[promotion_events._pair_key(stuck.fid,peer.fid)]={"count":3,"last_week":60}
    moved=pool._refresh_stale_rosters(limit=1)
    assert moved==1 and stuck.organization=="Balkan Combat" and stuck.idle_weeks<=12
    assert sum(f.organization=="LFA" for f in fighters)==5 and sum(f.organization=="Balkan Combat" for f in fighters)==5
    return "saturated long-idle divisions refresh by roster swap instead of fourth meetings"



def test_extreme_idle_beats_story_role_priority():
    pool=FighterPool(); pool.week=100
    urgent=Fighter.new_npc("Forgotten Veteran",data.country_by_name("USA")); urgent.fid="U"; urgent.pro_debut=True; urgent.organization="LFA"; urgent.weight_class=urgent.fight_weight_class="Lightweight"; urgent.pro_record=[4,8,0]; urgent.idle_weeks=70
    prospect=Fighter.new_npc("Hot Prospect",data.country_by_name("USA")); prospect.fid="P"; prospect.pro_debut=True; prospect.organization="LFA"; prospect.weight_class=prospect.fight_weight_class="Lightweight"; prospect.pro_record=[6,1,0]; prospect.age=23; prospect.current_streak=3; prospect.idle_weeks=8
    gate=Fighter.new_npc("Gatekeeper",data.country_by_name("USA")); gate.fid="G"; gate.pro_debut=True; gate.organization="LFA"; gate.weight_class=gate.fight_weight_class="Lightweight"; gate.pro_record=[11,5,0]; gate.age=31; gate.idle_weeks=10
    pool.fighters=[urgent,prospect,gate]; pool.update_rankings()
    a,b,role=promotion_events._role_pair(pool,"LFA","Lightweight",[urgent,prospect,gate],pool.week)
    assert urgent in (a,b) and role=="activity_fight"
    return "a fighter idle for a year cannot be repeatedly skipped by showcase/eliminator logic"


def test_severely_overdue_second_title_slot():
    pool=FighterPool(); pool.week=1
    fighters=[]
    for wc,prefix in (("Flyweight","F"),("Bantamweight","B")):
        champ=Fighter.new_npc(prefix+" Champ",data.country_by_name("USA")); champ.fid=prefix+"C"; champ.pro_debut=True; champ.organization="EFC"; champ.weight_class=champ.fight_weight_class=wc; champ.pro_record=[12,2,0]
        chal=Fighter.new_npc(prefix+" Challenger",data.country_by_name("USA")); chal.fid=prefix+"X"; chal.pro_debut=True; chal.organization="EFC"; chal.weight_class=chal.fight_weight_class=wc; chal.pro_record=[10,3,0]
        fighters.extend([champ,chal])
    pool.fighters=fighters; pool.update_rankings()
    pool.award_belt("EFC","Flyweight",fighters[0]); pool.award_belt("EFC","Bantamweight",fighters[2])
    pool.week=70
    for info in pool.belts.values():
        if info.get("org")=="EFC":
            info["won_week"]=1; info["last_defense_week"]=1
    pool.update_rankings()
    card=promotion_events._build_card(pool,"EFC",75)
    title_bouts=[b for b in card["bouts"] if b.get("title")]
    assert len(title_bouts)==2
    assert {b["weight_class"] for b in title_bouts}=={"Flyweight","Bantamweight"}
    return "slower promotions can schedule a second title only when another belt is severely overdue"



def test_saturated_champion_imports_fresh_challenger():
    pool=FighterPool(); pool.week=4
    champ=Fighter.new_npc("Saturated Champ",data.country_by_name("USA")); champ.fid="CH"; champ.pro_debut=True; champ.organization="LFA"; champ.weight_class=champ.fight_weight_class="Lightweight"; champ.pro_record=[14,2,0]
    p1=Fighter.new_npc("Old One",data.country_by_name("USA")); p1.fid="P1"; p1.pro_debut=True; p1.organization="LFA"; p1.weight_class=p1.fight_weight_class="Lightweight"; p1.pro_record=[8,5,0]
    p2=Fighter.new_npc("Old Two",data.country_by_name("USA")); p2.fid="P2"; p2.pro_debut=True; p2.organization="LFA"; p2.weight_class=p2.fight_weight_class="Lightweight"; p2.pro_record=[7,6,0]
    fresh=Fighter.new_npc("Fresh Challenger",data.country_by_name("Bulgaria")); fresh.fid="FR"; fresh.pro_debut=True; fresh.organization="Balkan Combat"; fresh.weight_class=fresh.fight_weight_class="Lightweight"; fresh.pro_record=[10,3,0]
    swap=Fighter.new_npc("Swap Peer",data.country_by_name("Bulgaria")); swap.fid="SW"; swap.pro_debut=True; swap.organization="Balkan Combat"; swap.weight_class=swap.fight_weight_class="Lightweight"; swap.pro_record=[5,5,0]
    pool.fighters=[champ,p1,p2,fresh,swap]; pool.update_rankings(); pool.award_belt("LFA","Lightweight",champ)
    info=pool.belts["LFA|Lightweight"]; info["won_week"]=1; info["last_defense_week"]=1
    pool.week=100
    pool.matchup_lifetime={
        promotion_events._pair_key("CH","P1"):3,
        promotion_events._pair_key("CH","P2"):3,
    }
    moved=pool._refresh_title_challengers(limit=1)
    assert moved==1
    newcomer=next(x for x in (fresh,swap) if x.organization=="LFA")
    assert promotion_events._meeting_count(pool,"CH",newcomer.fid)==0
    assert p1.organization=="Balkan Combat" or p2.organization=="Balkan Combat"
    return "an exhausted champion pool imports a real fresh contender instead of allowing fight #4"


def test_contract_structure_and_major_exclusivity():
    f=player("USA","MMA"); f.pro_debut=True; f.pro_record=[12,2,0]; f.fame=60
    terms={"org":"UFC","fights":6,"weeks":130,"purse_win":15000,"purse_show":3000,"exclusive":True,"clauses":[]}
    # Major non-exclusivity is a structural refusal, not RNG.
    ok,_,line=contracts.negotiate(f,terms,"nonexclusive")
    assert not ok and "non-exclusive" in line
    contracts.sign(f,"UFC",6,130,15000,3000,"ufc",True,["short_notice","title_escalator"])
    offer=contracts.apply_offer_clauses(f,{"org":"UFC","purse_win":10000,"purse_show":2000,"short_notice":True,"title":True})
    assert offer["purse_win"]==15000
    allowed,_=contracts.can_accept(f,"KSW")
    assert not allowed
    return "major deal keeps exclusivity while negotiated short-notice/title clauses compound"


def test_phase3_fight_week_and_staredown_are_gated():
    f=player("USA","MMA"); f.pro_debut=True; f.organization="UFC"; f.pro_record=[10,2,0]; f.fame=50
    o=Fighter.new_npc("Opponent",data.country_by_name("Brazil")); o.pro_debut=True; o.pro_record=[12,2,0]
    q=Quiet(["C"])
    booked={"org":"UFC","title":True,"weight_class":f.weight_class,"location":"Las Vegas","slot":"main"}
    assert phase3.fight_week_open(q,f,o,booked,True)
    assert phase3.staredown(q,f,o,booked,True)
    shown="\n".join(q.lines)
    assert "FIGHT WEEK" in shown and "WEIGH-IN STAREDOWN" in shown and "Press Enter" in shown
    assert f.story_flags.get("last_trash_talk_opponent") in (o.fid,o.name)
    low=player("Bulgaria","MMA"); low.pro_debut=True; low.organization="Balkan Combat"
    assert not phase3.fight_week_open(Quiet(),low,o,{"org":"Balkan Combat"},False)
    return "major/title fights get paced fight-week + staredown; routine cards do not"


def test_rivalry_causes_and_post_event_bonus():
    f=player("USA","MMA"); f.pro_debut=True; f.organization="UFC"; f.fame=60; f.money=1000; f.performance_rating=9.2
    o=Fighter.new_npc("Close Rival",data.country_by_name("Canada")); o.pro_debut=True; o.team="AKA"; f.team="AKA"
    f.record_fight(o.name,"Win","Split Decision",3,"UFC",9.2,sport="mma")
    f.record_fight(o.name,"Win","Split Decision",3,"UFC",9.2,sport="mma")
    pool=FighterPool(); pool.fighters=[o]; pool.event_history=[{"id":"UFC-X","org":"UFC","week":10,"location":"Vegas","bouts":[],"results":[]}]
    q=Quiet()
    out=phase3.post_event(q,f,o,"Win","Split Decision",pool,{"org":"UFC","event_id":"UFC-X","slot":"main"},old_rank=None)
    assert out["bonus"]==50000 and f.money==51000
    assert "close decision" in out["rivalry_reasons"] and "rematch history" in out["rivalry_reasons"] and "gym history" in out["rivalry_reasons"]
    assert f.rival==o.name
    assert pool.event_history[0]["post_event"][0]["bonus"]==50000
    return "post-event layer awards major bonus and rivalries emerge from real bout context"


def test_double_champion_offer_and_belt_persistence():
    f=player("USA","MMA"); f.pro_debut=True; f.organization="UFC"; f.room="ufc"; f.fame=80; f.pro_record=[18,2,0]; f.recent_results=["W","W","W"]; f.current_streak=3
    f.weight_class=f.fight_weight_class="Lightweight"; f.week=100; f.story_flags["ufc_rank"]=1
    o=Fighter.new_npc("Middle Champ",data.country_by_name("Brazil")); o.fid="MWC"; o.pro_debut=True; o.organization="UFC"; o.weight_class=o.fight_weight_class="Welterweight"; o.pro_record=[20,3,0]
    pool=FighterPool(); pool.week=100; pool.fighters=[o]; pool._player=f
    pool.award_belt("UFC","Lightweight",f); pool.belts["UFC|Lightweight"].update({"defenses":2,"won_week":90,"last_defense_week":94})
    pool.award_belt("UFC","Welterweight",o)
    shot=identity.title_shot(f,pool)
    assert shot and shot["role"]=="double_champ" and shot["wc"]=="Welterweight" and shot["opponent"] is o
    pool.award_belt("UFC","Welterweight",f,defeated=o)
    assert f.story_flags.get("double_champion") is True
    pool._sync_belts(player=f)
    assert pool.belt_holder("UFC","Lightweight") is f and pool.belt_holder("UFC","Welterweight") is f
    return "proven UFC champion can earn and retain a legitimate adjacent-division second belt"


def test_hall_of_fame_and_record_book():
    f=player("USA","MMA"); f.pro_debut=True; f.pro_record=[28,4,0]; f.fame=90; f.legacy_score=90
    pool=FighterPool(); pool._player=f
    pool.award_belt("UFC",f.weight_class,f)
    for _ in range(5): pool.record_title_defense("UFC",f.weight_class,f)
    row=legacy.maybe_induct(pool,f)
    assert row and row["score"]>=65 and pool.hall_of_fame
    book=legacy.record_book(pool,player=f)
    assert book["pro_wins"][0][1] is f and book["ufc_defenses"][0][0]>=5
    return "Hall of Fame uses résumé/title ledger and record book exposes real career records"


def test_completed_card_summary_surfaces_title_and_consequences():
    pool=FighterPool(); pool.event_history=[{
        "id":"UFC-1","week":50,"org":"UFC","location":"London",
        "results":["A def. B","C def. D"],
        "title_changes":[{"weight_class":"Lightweight","winner":"A","previous":"B"}],
        "post_event":[{"fighter":"A","bonus":50000,"rank_before":2,"rank_after":1}],
    }]
    lines=promotion_events.completed_card_lines(pool,3); text="\n".join(lines)
    assert "A def. B" in text and "TITLE Lightweight" in text and "bonus $50,000" in text and "rank #2→#1" in text
    return "completed-card view surfaces results, championship changes, bonuses and rankings"



def test_mma_calendar_uses_one_home_continental_championship():
    fixtures = (("Bulgaria", "European Championships"),
                ("Venezuela", "Pan-American Championships"),
                ("Japan", "Asian Championships"))
    for country, expected in fixtures:
        f=player(country,"MMA"); f.week=14; f.amateur_record=[10,1,0]; f.national_team=True
        rows=fights._next_competition_info(f)
        continental=[r for r in rows if expected in r["name"]]
        assert len(continental)==1, (country, continental)
        assert continental[0]["event_week"]==22
        assert not any("European Championships" in r["name"] for r in rows if country != "Bulgaria")
    return "amateur MMA shares the one-per-year European/Pan-American/Asian route"


def test_semantic_roles_and_replacements_respect_trilogy_cap():
    random.seed(13009)
    pool=FighterPool(); pool.week=100
    a=Fighter.new_npc("Prospect",data.country_by_name("USA")); a.fid="A"; a.pro_debut=True; a.organization="LFA"; a.weight_class=a.fight_weight_class="Lightweight"; a.pro_record=[6,1,0]; a.age=23; a.current_streak=2
    b=Fighter.new_npc("Gatekeeper",data.country_by_name("USA")); b.fid="B"; b.pro_debut=True; b.organization="LFA"; b.weight_class=b.fight_weight_class="Lightweight"; b.pro_record=[10,5,0]; b.age=31; b.current_streak=0
    c=Fighter.new_npc("Alternative",data.country_by_name("USA")); c.fid="C"; c.pro_debut=True; c.organization="LFA"; c.weight_class=c.fight_weight_class="Lightweight"; c.pro_record=[5,2,0]; c.age=26; c.current_streak=1
    pool.fighters=[a,b,c]; pool.update_rankings()
    pool.matchup_history[promotion_events._pair_key(a.fid,b.fid)]={"count":3,"last_week":20}
    old_random=random.random
    try:
        random.random=lambda: 0.0
        x,y,role=promotion_events._role_pair(pool,"LFA","Lightweight",[a,b,c],pool.week)
    finally:
        random.random=old_random
    assert set((x.fid,y.fid)) != {"A","B"}, role
    # Replacement selection must also skip a saturated pairing.
    ev={"org":"LFA","week":101,"status":"scheduled","bouts":[{"red_id":"A","blue_id":"C","weight_class":"Lightweight","status":"scheduled","replacement":False}]}
    pool.events=[ev]; a.npc_injury_weeks=4
    pool.matchup_history[promotion_events._pair_key(b.fid,c.fid)]={"count":3,"last_week":20}
    old_random=random.random
    try:
        random.random=lambda: 0.0
        promotion_events.process_world_withdrawals(pool)
    finally:
        random.random=old_random
    bout=ev["bouts"][0]
    assert bout.get("status") == "cancelled" or bout.get("blue_id") != "B"
    return "semantic matchmaking and emergency replacements both enforce the trilogy ceiling"

def test_dashboard_surfaces_fight_weight_and_contract_qol():
    import contextlib, io
    f=player("USA","MMA"); f.pro_debut=True; f.organization="LFA"; f.week=50; f.walking_weight=90.0; f.fight_weight_class=f.weight_class
    contracts.sign(f,"LFA",4,80,4000,1000,"local",False,["short_notice","title_escalator"])
    f.booked_fight={"org":"LFA","date_week":55,"title":True,"short_notice":True,"opponent_snap":{"name":"Test Opp"}}
    from mma_legend import cut
    cut.ensure_weight_campaign(f,reset=True)
    c=ui.GameConsole(width=44,fast=True,color=False)
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf): ui.render_dashboard(c,f)
    text=buf.getvalue(); lines=text.splitlines()
    assert "TITLE" in text and "SHORT NOTICE" in text and "Weight:" in text
    assert "short-notice +25%" in text and "non-exclusive" in text
    assert max((len(line) for line in lines), default=0) <= 60
    return "weekly dashboard exposes title/short-notice, weight trajectory and negotiated deal terms"


def test_lifetime_trilogy_survives_recent_memory_prune():
    pool=FighterPool(); pool.week=900
    a=Fighter.new_npc("Old Rival A",data.country_by_name("USA")); a.fid="A"; a.pro_debut=True; a.organization="LFA"; a.weight_class=a.fight_weight_class="Lightweight"
    b=Fighter.new_npc("Old Rival B",data.country_by_name("USA")); b.fid="B"; b.pro_debut=True; b.organization="LFA"; b.weight_class=b.fight_weight_class="Lightweight"
    pool.fighters=[a,b]
    key=promotion_events._pair_key("A","B")
    # Recent tactical memory has aged out, but the lifetime ledger remembers the trilogy.
    pool.matchup_history={}
    pool.matchup_lifetime={key:3}
    assert promotion_events._meeting_count(pool,"A","B")==3
    assert promotion_events._best_pair(pool,"LFA","Lightweight",[a,b],"competitive") is None
    blob=persistence._pool_blob(a,pool,[a,b])
    assert blob["matchup_lifetime"][key]==3
    return "five-season recency pruning can never reopen a completed trilogy"


def test_lifetime_title_stats_survive_recent_lineage_cap():
    f=player("USA","MMA"); f.pro_debut=True; f.organization="UFC"; f.fid="PLAYER"
    pool=FighterPool(); pool._player=f
    pool.award_belt("UFC",f.weight_class,f)
    for _ in range(6):
        pool.record_title_defense("UFC",f.weight_class,f)
    before=legacy.title_stats(pool,f)
    assert before["ufc_title_wins"]>=1 and before["ufc_defenses"]==6
    # Simulate the recent lineage feed rolling over after decades.
    pool.title_history=[{"fighter_id":"OTHER","action":"defended","org":"UFC","weight_class":"Lightweight"} for _ in range(2000)]
    after=legacy.title_stats(pool,f)
    assert after["ufc_title_wins"]==before["ufc_title_wins"] and after["ufc_defenses"]==6
    return "Hall-of-Fame and record-book totals no longer depend on the capped lineage feed"


def test_weight_campaign_pace_qol_and_lifestyle_has_no_dead_gym_entry():
    f=player("USA","MMA"); f.pro_debut=True; f.week=40
    f.walking_weight=80.0; f.weight_class=f.fight_weight_class="Welterweight"
    f.booked_fight={"org":"LFA","date_week":46,"opponent_snap":{"name":"Pace Test"}}
    cut.ensure_weight_campaign(f,reset=True)
    f.week=42; f.walking_weight=79.6
    prog=cut.weight_campaign_summary(f)
    assert prog["weeks_left"]==4 and "pace" in prog and "required_weekly" in prog
    q=Quiet(["X"])
    career.lifestyle_menu(q,f)
    text="\n".join(q.lines)
    assert " G)" not in text and "Gym & Team moved" not in text
    return "cut pacing is visible and the obsolete Lifestyle gym path is fully removed"


def main():
    for test in (
        test_region_specific_amateur_calendar,
        test_mma_calendar_uses_one_home_continental_championship,
        test_world_generation_and_matchmaking_roles_no_unhashable,
        test_semantic_roles_and_replacements_respect_trilogy_cap,
        test_fourth_meeting_hard_block,
        test_stale_saturated_roster_refreshes_without_fourth_fights,
        test_extreme_idle_beats_story_role_priority,
        test_severely_overdue_second_title_slot,
        test_saturated_champion_imports_fresh_challenger,
        test_contract_structure_and_major_exclusivity,
        test_phase3_fight_week_and_staredown_are_gated,
        test_rivalry_causes_and_post_event_bonus,
        test_double_champion_offer_and_belt_persistence,
        test_hall_of_fame_and_record_book,
        test_completed_card_summary_surfaces_title_and_consequences,
        test_lifetime_trilogy_survives_recent_memory_prune,
        test_lifetime_title_stats_survive_recent_lineage_cap,
        test_weight_campaign_pace_qol_and_lifestyle_has_no_dead_gym_entry,
        test_dashboard_surfaces_fight_weight_and_contract_qol,
    ):
        print("PASS", test.__name__, test())
    print("ALL 1.30 RELEASE MILESTONE CHECKS OK")


if __name__ == "__main__": main()
