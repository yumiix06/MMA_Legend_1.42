"""v1.38 living careers / promotion identity regression checks."""
from mma_legend import constants, living_careers, orgs
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


def npc(name="Prospect", wins=8, losses=1, streak=3, org="Balkan Combat"):
    f=Fighter.new_npc(name,{"name":"Bulgaria","flag":"BG","bonus":{}},style="Wrestling",team="Test")
    f.fid="npc_"+name.replace(" ","_")
    f.pro_debut=True; f.pro_record=[wins,losses,0]; f.organization=org; f.current_streak=streak
    f.weight_class="Lightweight"; f.fight_weight_class="Lightweight"; f.natural_weight_class="Lightweight"
    return f


def run():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1,38,0)

    # Motives persist through save/load instead of being ephemeral AI labels.
    f=npc()
    living_careers.ensure(f)
    assert f.career_personality in living_careers.PERSONALITIES
    assert living_careers.choose_goal(f) in {"move_up","rank_climb","title_chase","activity"}
    f.pro_record=[12,1,0]; f.current_streak=5; f.story_flags["org_rank"]=2
    assert living_careers.choose_goal(f)=="move_up"
    f.career_goal="move_up"; f.career_goal_week=44; f.career_log=[{"week":44,"to":"move_up"}]
    g=Fighter.from_dict(f.to_dict())
    assert g.career_goal=="move_up" and g.career_goal_week==44 and g.career_log

    # Distinct promotions actually expose distinct identities.
    assert living_careers.profile("LFA")["protect"] > living_careers.profile("ACA")["protect"]
    assert living_careers.profile("ACA")["tough"] > living_careers.profile("Cage Warriors")["tough"]
    assert living_careers.profile("Bellator")["stars"] > living_careers.profile("LFA")["stars"]

    # Promotion interest is political, not a pure random eligible-org shuffle.
    # Home/regional fit and relationships can move an already-eligible desk up.
    player=Fighter.new_player("Player","B",{"name":"Bulgaria","flag":"BG","bonus":{}},"Wrestling",height=180,weight=70)
    player.pro_debut=True; player.pro_record=[8,1,0]; player.current_streak=3; player.fame=20
    from mma_legend import people
    bprom=people.promoter_for("Balkan Combat")
    people.adjust_rapport(player,bprom.id,30)
    assert living_careers.offer_interest_score(player,"Balkan Combat") > living_careers.offer_interest_score(player,"Road FC")
    ranked=living_careers.rank_offer_orgs(player,["Balkan Combat","Road FC"])
    assert set(ranked)=={"Balkan Combat","Road FC"}

    # Player offers carry career meaning + promotion identity.
    player.pro_record=[4,0,0]; player.current_streak=4; player.organization=None; player.room="regional"
    opp=npc("Opponent",5,2,1,"Balkan Combat")
    off={"org":"Balkan Combat","opponent":opp,"tag":"feature","purse_win":1000,"purse_show":200,"date_week":player.week+6}
    decorated=living_careers.decorate_player_offers(player,[off])[0]
    assert decorated.get("career_opportunity")
    assert decorated.get("promotion_identity")
    assert 1 <= int(decorated.get("career_upside",0)) <= 5

    # Winning an opportunity has tangible but bounded career consequences.
    before=(player.fame,player.reputation,player.legacy_score)
    decorated["career_opportunity"]="Step-up fight"
    line=living_careers.resolve_player_opportunity(player,decorated,"win_decision","")
    assert "paid off" in line
    assert player.fame >= before[0] and player.reputation > before[1]

    # Backing out after inspecting a selected offer really leaves the flow.
    # This used to loop forever even though the screen explicitly said X=Back.
    from mma_legend import fights, orgs as _orgs
    class QuietConsole:
        def __init__(self): self.answers=["A","X"]; self.warnings=[]
        def ask(self,*a,**k): return self.answers.pop(0)
        def print(self,*a,**k): pass
        def header(self,*a,**k): pass
        def gold(self,*a,**k): pass
        def good(self,*a,**k): pass
        def info(self,*a,**k): pass
        def warn(self,msg,*a,**k): self.warnings.append(str(msg))
        def pause(self,*a,**k): pass
        def auto_pause(self,*a,**k): pass
    player.manager="Test Manager"; player.manager_id=None; player.booked_fight=None; player.fight_cooldown=0
    test_offer={"org":"Balkan Combat","opponent":opp,"opponent_id":opp.fid,"tag":"feature","purse_win":1000,"purse_show":200,"date_week":player.week+6}
    old_inbox=_orgs.inbox
    try:
        _orgs.inbox=lambda *a,**k:[dict(test_offer)]
        qc=QuietConsole(); fights.inbox_night(qc,player,None)
        assert player.booked_fight is None and qc.answers==[]
    finally:
        _orgs.inbox=old_inbox

    # A world tick assigns coherent persistent goals to the roster.
    pool=FighterPool(); pool.fighters=[f,opp]; pool.week=16
    lines=living_careers.tick_world(pool)
    assert f.career_goal and opp.career_goal
    assert isinstance(lines,list)

    print("v1.38 living careers checks: PASS")
    return True

if __name__ == "__main__": run()
