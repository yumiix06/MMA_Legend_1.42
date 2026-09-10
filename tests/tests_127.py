"""v1.27 release gates: sports, identity/media and living cards."""
from __future__ import annotations

import random

from mma_legend.models import Fighter
from mma_legend import data, amateur_sports, nicknames, notoriety, promotion_events
from mma_legend.engine import JudoRuleset, CombatSamboRuleset
from mma_legend.world import FighterPool


class Quiet:
    width = 44
    def __init__(self, answers=None): self.lines=[]; self.answers=list(answers or [])
    def header(self,*a,**k): self.lines.append(" ".join(map(str,a)))
    def section(self,*a,**k): self.lines.append(" ".join(map(str,a)))
    def print(self,x="",**k): self.lines.append(str(x))
    def ask(self,*a,**k): return self.answers.pop(0) if self.answers else "X"
    def info(self,x="",**k): self.lines.append(str(x))
    def good(self,x="",**k): self.lines.append(str(x))
    def gold(self,x="",**k): self.lines.append(str(x))
    def warn(self,x="",**k): self.lines.append(str(x))
    def pause(self,*a,**k): pass
    def read_pause(self,*a,**k): pass
    def continue_prompt(self,*a,**k): pass
    def moment(self,*a,**k): pass


def _player():
    return Fighter.new_player("Test Fighter", "B", data.country_by_name("Bulgaria"), "Judo", 180, 77)


def test_side_sports_and_rules():
    p=_player(); amateur_sports.ensure(p)
    assert len(amateur_sports.SPORT_KEYS) >= 8 and "Taekwondo" in amateur_sports.SPORT_KEYS
    assert "throw" in JudoRuleset.allowed_actions and "jab" not in JudoRuleset.allowed_actions
    assert "throw" in CombatSamboRuleset.allowed_actions and "jab" in CombatSamboRuleset.allowed_actions
    assert p.sport_records["mma"] == [0,0,0] and p.sport_records["judo"] == [0,0,0]
    return "original sport ledgers plus Taekwondo; Judo and Combat Sambo keep distinct rules"


def test_bjj_and_judo_belts_are_earned():
    p=_player(); q=Quiet()
    p.bjj_belt="white"; p.bjj_grade_points=80; p.bjj_weeks=20; p.money=1000
    assert amateur_sports.evaluate_belt(q,p,"bjj") and p.bjj_belt == "blue"
    p.judo_belt="white"; p.judo_grade_points=35; p.judo_weeks=8
    assert amateur_sports.evaluate_belt(q,p,"judo") and p.judo_belt == "yellow"
    assert p.money == 845
    return "BJJ white->blue and Judo white->yellow require points, mat weeks and grading fees"


def test_belt_training_and_save_fields():
    p=_player(); amateur_sports.train_belt(p,"bjj",20); amateur_sports.train_belt(p,"judo",20)
    d=p.to_dict(); q=Fighter.from_dict(d)
    assert q.bjj_grade_points == 20 and q.judo_grade_points == 20
    assert q.bjj_belt == "white" and q.judo_belt == "white"
    return "both belt systems persist their mat time and grading points"


def test_nickname_catalog_and_org_uniqueness():
    assert len(nicknames.NICKNAMES) >= 120 and max(map(len,nicknames.NICKNAMES)) <= 18
    pool=FighterPool(); a=_player(); b=_player(); a.is_player=b.is_player=False
    a.pro_record=[5,0,0]; b.pro_record=[5,0,0]; a.organization=b.organization="UFC"
    pool.fighters=[a,b]
    random.seed(127); nicknames.assign_npc(a,pool); nicknames.assign_npc(b,pool)
    assert a.nickname and b.nickname and a.nickname != b.nickname
    return "%s short nicknames; duplicates avoided inside an organization" % len(nicknames.NICKNAMES)


def test_media_gates():
    p=_player(); p.pro_debut=False
    assert not notoriety.should_interview(p,{"org":"Local Amateur"})
    p.pro_debut=True; p.organization="LFA"; p.fame=2
    assert not notoriety.should_interview(p,{"org":"LFA","slot":"prelim"})
    p.organization="UFC"; p.fame=40
    assert notoriety.should_press(p,{"org":"UFC","title":True,"slot":"main"})
    return "amateur/low-pro media suppressed; UFC title press is mandatory"


def test_living_cards_and_no_double_booking():
    random.seed(1270)
    pool=FighterPool(); pool.generate_world(80,160)
    promotion_events.maintain(pool,18)
    assert pool.events
    ids=[]
    for ev in pool.events:
        assert ev.get("id") and ev.get("org") and ev.get("location") and ev.get("week") > pool.week
        for b in ev.get("bouts",[]): ids += [b.get("red_id"),b.get("blue_id")]
    ids=[x for x in ids if x]
    assert len(ids) == len(set(ids)), "fighter double-booked across cards"
    before=sum(sum(f.pro_record) for f in pool.fighters if f.pro_debut)
    target=min(e["week"] for e in pool.events); pool.week=target
    lines=promotion_events.resolve_due(pool)
    after=sum(sum(f.pro_record) for f in pool.fighters if f.pro_debut)
    assert lines and after > before and pool.event_history
    return "%s scheduled cards resolve only when their event week arrives" % len(pool.event_history)


def test_accepted_offer_replaces_opponents_existing_slot():
    random.seed(1271)
    pool=FighterPool(); pool.generate_world(80,160)
    promotion_events.maintain(pool,18)
    ev=next(e for e in pool.events if e.get("bouts"))
    old=next(b for b in ev["bouts"] if b.get("status") == "scheduled")
    opponent_id=old["blue_id"]
    player=_player(); player.pro_debut=True; player.organization=ev["org"]
    offer={"event_id":ev["id"], "opponent_id":opponent_id, "title":False}
    promotion_events.attach_player_bout(pool,player,offer)
    open_bouts=[b for event in pool.events for b in event.get("bouts",[])
                if b.get("status") == "scheduled"]
    assert sum("PLAYER" in (b.get("red_id"),b.get("blue_id")) for b in open_bouts) == 1
    assert sum(opponent_id in (b.get("red_id"),b.get("blue_id")) for b in open_bouts) == 1
    assert old.get("status") == "cancelled"
    return "accepting an offer removes the opponent's previous card slot"


def test_ufc_title_intro():
    from mma_legend.fights import _ufc_title_introductions
    p=_player(); o=Fighter.new_npc("Rival Name",data.country_by_name("USA")); p.pro_debut=o.pro_debut=True
    p.nickname="The Wall"; p.pro_record=[10,1,0]; o.pro_record=[14,2,0]
    pool=FighterPool(); pool.fighters=[o]; pool.champions[p.weight_class]=o
    q=Quiet(); _ufc_title_introductions(q,p,o,pool)
    text="\n".join(q.lines)
    assert "CHALLENGER" in text and "CHAMPION" in text and '"The Wall"' in text
    return "UFC title introduction presents challenger first and champion second"


def main():
    for test in (test_side_sports_and_rules, test_bjj_and_judo_belts_are_earned,
                 test_belt_training_and_save_fields, test_nickname_catalog_and_org_uniqueness,
                 test_media_gates, test_living_cards_and_no_double_booking,
                 test_accepted_offer_replaces_opponents_existing_slot, test_ufc_title_intro):
        print("PASS", test())
    print("ALL 1.27 SPORTS / MEDIA / EVENT-CALENDAR CHECKS OK")


if __name__ == "__main__": main()
