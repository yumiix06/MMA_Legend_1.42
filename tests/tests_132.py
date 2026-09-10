"""1.32 Part 2 regression checks: career depth, pacing and event identity."""
from __future__ import annotations

import random
from unittest.mock import patch

from mma_legend import data, events, persistence, promotion_events, systems15, timeline
from mma_legend.models import Fighter
from mma_legend.world import FighterPool


class Quiet:
    width = 44
    def __init__(self, answers=()): self.answers=list(answers); self.lines=[]; self.continues=0
    def ask(self, prompt="", *a, **k): self.lines.append(str(prompt)); return self.answers.pop(0) if self.answers else "A"
    def _add(self, value="", *a, **k): self.lines.append(str(value))
    print=info=warn=good=gold=header=section=_add
    def pause(self,*a,**k): pass
    def read_pause(self,*a,**k): pass
    def continue_prompt(self, prompt="Press Enter to continue", *a, **k): self.continues += 1; self.lines.append(str(prompt))


def player():
    p=Fighter.new_player("Part2 QA","B",data.country_by_name("Bulgaria"),"Combat Sambo",185,90)
    p.fid="PLAYER"; p.week=40
    return p


def test_career_life_fields_survive_roundtrip():
    p=player(); p.intl_camp="thailand"; p.intl_camp_weeks=3; p.connections=[{"who":"Coach"}]
    p.side_job="Bouncer"; p.job_shifts={"Bouncer":7}; p.job_reputation=9; p.job_history=[{"week":39,"job":"Bouncer","pay":280}]
    p.timeline=[{"week":10,"year":1,"text":"National champion"}]; p.notes=[{"text":"hello"}]; p.last_ledger={"net":12}; p.mileage=7.5
    q=Fighter.from_dict(p.to_dict())
    assert q.intl_camp=="thailand" and q.intl_camp_weeks==3 and q.connections
    assert q.side_job=="Bouncer" and q.job_shifts["Bouncer"]==7 and q.job_reputation==9 and q.job_history
    assert q.timeline and q.notes and q.last_ledger["net"]==12 and q.mileage==7.5
    return "career-life metadata no longer disappears on save/load"


def test_side_jobs_have_prereqs_progression_and_camp_lock():
    p=player(); p.strength=30; p.cardio=40; p.money=0; p.energy=100
    msg=systems15.work_shift(p,"F")
    assert msg.startswith("Requires Strength 40"), msg
    p.strength=45
    with patch("mma_legend.systems15.random.random", return_value=.99):
        for _ in range(6): systems15.work_shift(p,"F")
    assert p.job_shifts["Bouncer"]==6 and p.money >= 6*280 and p.side_job=="Bouncer"
    assert p.job_reputation==6
    p.intl_camp="thailand"
    before=p.money; msg=systems15.work_shift(p,"A")
    assert "cannot be worked" in msg and p.money==before
    return "ten-job system enforces prerequisites, raises and international-camp lock"


def test_event_choice_is_acknowledgement_not_second_enter():
    p=player(); q=Quiet(["A"])
    ev={"id":"qa_choice","title":"Coach question","description":"Pick one.","category":"training",
        "choices":[{"key":"A","label":"Technical reps","effects":{"fight_iq":1}},
                   {"key":"B","label":"Hard rounds","effects":{"energy":-2}}]}
    before=p.fight_iq; events.handle_event(q,p,ev)
    assert p.fight_iq==before+1 and q.continues==0, q.lines
    q2=Quiet(); events.handle_event(q2,p,{"id":"qa_info","title":"Notice","description":"Information only."})
    assert q2.continues==1
    return "choice cards resolve immediately; information-only cards retain deliberate acknowledgement"


def _pro(name, fid, org="Balkan Combat", wc="Lightweight", wins=6):
    f=Fighter.new_npc(name,data.country_by_name("Bulgaria")); f.fid=fid; f.pro_debut=True; f.organization=org
    f.weight_class=f.fight_weight_class=wc; f.pro_record=[wins,2,0]; f.idle_weeks=8
    return f


def test_cards_receive_persistent_numbered_or_fight_night_identity():
    random.seed(13201)
    pool=FighterPool(); pool.week=30
    pool.fighters=[_pro("F%s"%i,"F%s"%i,wins=5+i%4) for i in range(24)]
    pool.update_rankings()
    card=promotion_events._build_card(pool,"Balkan Combat",36)
    assert card["event_name"].startswith("Balkan Combat ") and card["number"]==1
    assert card["series"] in ("numbered","fight_night") and len(card["bouts"])>=5
    # A second card in the same series advances rather than reusing the number.
    pool.events=[card]
    card2=promotion_events._build_card(pool,"Balkan Combat",44)
    assert card2["event_name"] != card["event_name"]
    blob=persistence._pool_blob(player(),pool,pool.fighters)
    assert blob["event_counters"]["Balkan Combat"][card2["series"]] >= card2["number"]
    return "%s and %s have stable promotion-series identities" % (card["event_name"], card2["event_name"])


def test_legacy_scheduled_card_is_named_on_migration():
    pool=FighterPool(); pool.events=[{"id":"OLD-1","org":"LFA","week":9,"location":"Denver","status":"scheduled","bouts":[]}]
    pool.event_counters={}
    promotion_events.ensure(pool)
    assert pool.events[0].get("event_name")=="LFA Fight Night 1", pool.events[0]
    return "pre-1.32 unnamed cards are labelled once instead of remaining anonymous"


def test_timeline_splits_amateur_pro_and_shows_fight_stats():
    p=player(); p.fight_history=[
        {"week":12,"opponent":"A","result":"Win","method":"Decision","round":1,"event":"Combat Sambo Nationals","sport":"combat_sambo","pro":False,
         "stats":{"strikes_landed":8,"strikes_attempted":12,"takedowns_landed":2,"takedowns_attempted":3}},
        {"week":80,"opponent":"B","result":"Win","method":"TKO","round":2,"event":"Balkan Combat Fight Night 4","sport":"mma","pro":True,
         "performance_rating":8.7,"stats":{"strikes_landed":24,"strikes_attempted":39,"knockdowns":1}},
    ]
    q=Quiet(); timeline.render(q,p); text="\n".join(q.lines)
    assert "AMATEUR CAREER" in text and "PROFESSIONAL CAREER" in text
    assert "Combat Sambo Nationals" in text and "Balkan Combat Fight Night 4" in text
    assert "TD 2/3" in text and "rating 8.7" in text and "KD 1" in text
    return "timeline separates phases and surfaces fight-level statistics"


def test_record_fight_dates_new_rows():
    p=player(); p.week=77; p.record_fight("Opponent","Win","Decision",3,"Local MMA",sport="mma")
    assert p.fight_history[-1]["week"]==77
    return "new fight ledger rows retain career week for timeline ordering"


def run():
    tests=[v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        note=fn(); print("PASS",fn.__name__,note)
    print("ALL 1.32 PART-2 CHECKS OK")


if __name__=="__main__": run()
