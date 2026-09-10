"""1.25 junior-handoff regression checks from the 1.24 human playtest."""
from __future__ import annotations

import builtins
import random
from unittest.mock import patch

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.world import FighterPool
from mma_legend import ai, career, contracts, cut, data, diagnostics, economy, events, identity, orgs, persistence
from mma_legend.ui import GameConsole


def _player(wc="Middleweight"):
    f = Fighter.new_player("QA", "P", country_by_name("Greece"), "Boxing")
    f.pro_debut = True
    f.pro_record = [8, 2, 0]
    f.organization = "UFC"
    f.room = "ufc"
    f.promotion_tier = 10
    f.weight_class = wc
    f.fight_weight_class = wc
    f.natural_weight_class = "Light Heavyweight" if wc == "Middleweight" else wc
    f.weight = cut.CLASS_LIMIT[wc]
    f.natural_weight = 84.0 if wc == "Middleweight" else f.weight * 1.04
    f.walking_weight = 87.9 if wc == "Middleweight" else f.weight * 1.05
    f.story_flags = {"ufc_signed": True, "ufc_rank": 7, "org_rank": 1, "org_board": "UFC"}
    return f


def _npc(name="Opponent", org="UFC", wc="Middleweight"):
    f = Fighter.new_npc(name, country_by_name("USA"), style="MMA")
    f.pro_debut = True
    f.pro_record = [10, 2, 0]
    f.organization = org
    f.room = "ufc" if org == "UFC" else "national"
    f.weight_class = wc
    return f


def test_ufc_contract_corruption_repairs_toward_visible_org():
    raw = _player().to_dict()
    raw["organization"] = "UFC"
    raw["room"] = "ufc"
    raw["org_contract"] = {"org": "", "fights_left": 6, "fights_total": 6,
                           "weeks_left": 130, "purse_win": 13721, "purse_show": 2744,
                           "exclusive": True, "room": "ufc"}
    raw["story_flags"]["org_belt"] = "LFA"
    fixed = identity.repair_save(raw)
    assert fixed["org_contract"]["org"] == "UFC", fixed["org_contract"]
    assert fixed["story_flags"].get("org_belt") is None
    assert "LFA" in fixed["story_flags"].get("former_belts", [])
    f = Fighter.from_dict(fixed)
    assert contracts.active(f)["org"] == "UFC"
    assert not contracts.can_accept(f, "ACA")[0]
    return "blank UFC contract self-heals, stale LFA belt becomes history, exclusivity holds"


def test_ufc_title_requires_ufc_resume_and_specific_rank():
    p = _player(); p.current_streak = 4; p.recent_results = ["W", "W", "W", "W"]
    p.fight_history = [{"event": "DWCS", "pro": True, "result": "Win", "method": "TKO"}]
    pool = FighterPool(); champ = _npc("Champion")
    champ.fid = "champ"; pool.fighters = [champ]; pool.attach_player(p)
    pool.belts[identity.belt_key("UFC", p.weight_class)] = {"fid": champ.fid, "name": champ.name,
                                                             "org": "UFC", "wc": p.weight_class}
    # Generic rank #1 must not create a title shot when UFC-specific rank is #7
    assert identity.title_shot(p, pool) is None
    p.story_flags["ufc_rank"] = 2
    # Still no shot on debut: DWCS is not a UFC bout.
    assert identity.title_shot(p, pool) is None
    p.fight_history += [
        {"event": "UFC", "pro": True, "result": "Loss", "method": "Decision"},
        {"event": "UFC", "pro": True, "result": "Win", "method": "TKO"},
        {"event": "UFC", "pro": True, "result": "Win", "method": "Decision"},
    ]
    p.current_streak = 2; p.recent_results = ["L", "W", "W"]
    shot = identity.title_shot(p, pool)
    assert shot and shot["org"] == "UFC" and shot["opponent"] is champ, shot
    p.recent_results = ["W", "W", "L"]; p.current_streak = -1
    assert identity.title_shot(p, pool) is None
    return "DWCS/UFC debut cannot be a title fight; top-3 + UFC résumé + win streak can"


def test_weight_campaign_tracks_real_loss_and_bully_tradeoff():
    p = _player(); p.week = 10; p.booked_fight = {"date_week": 15, "org": "UFC"}
    p.meal_plan = "Weight-Cut Strict"
    cut.set_weight_strategy(p, "performance")
    perf_target = cut.target_walk_weight(p)
    start = p.walking_weight
    for _ in range(4):
        cut.tick_body(p)
        p.week += 1
    summary = cut.weight_campaign_summary(p)
    assert summary["start"] == round(start, 1), summary
    assert summary["lost"] >= 2.0, summary
    assert len(p.story_flags["weight_camp"]["history"]) >= 4
    p2 = _player(); p2.week = 10; p2.booked_fight = {"date_week": 15, "org": "UFC"}
    cut.set_weight_strategy(p2, "bully")
    bully_target = cut.target_walk_weight(p2)
    assert bully_target > perf_target, (perf_target, bully_target)
    return "nutrition removes real camp mass, records start→weekly trend, bully plan deliberately stays heavier"


def test_supplement_brand_sponsor_supplies_legal_products_free():
    p = _player(); p.money = 0; p.sponsors = ["Optimum Nutrition"]
    assert career.supplement_sponsor(p) == "Optimum Nutrition"
    class Q:
        def __init__(self): self.lines=[]
        def header(self,*a,**k): pass
        def print(self,x="",**k): self.lines.append(str(x))
        def ask(self,*a,**k): return "1"
        def warn(self,x,*a,**k): self.lines.append(str(x))
        def good(self,x,*a,**k): self.lines.append(str(x))
        def pause(self,*a,**k): pass
    q=Q(); career._show_supplement_list(q, p, "legal")
    assert p.money == 0
    assert p.supplement_active, q.lines
    assert any("FREE (Optimum Nutrition)" in x for x in q.lines), q.lines
    return "supplement-company sponsorship has a concrete perk: legal supplements are supplied free"


def test_money_ledger_and_debt_are_one_balance_sheet():
    p = _player(); p.age = 18; p.money = 1000; p.debt = 500; p.fame = 78
    p.sponsors = ["A", "B", "C"]; p.side_job = "Night porter"; p.booked_fight = None
    income, expenses = economy.weekly_breakdown(p)
    assert income == {"sponsor retainer": 45}, income
    assert "side job" not in income
    start = p.money
    cut.weekly_costs(p)
    assert p.last_ledger["net"] == 45 - sum(expenses.values())
    assert p.money == start + p.last_ledger["net"], (p.money, p.last_ledger)
    p.money = -50; before = p.debt
    from mma_legend.systems15 import clamp_money, repay_debt
    clamp_money(p)
    assert p.money == 0 and p.debt == before + 50
    p.money = 200; debt0 = p.debt
    repay_debt(p, 100)
    assert p.money == 100 and p.debt == debt0 - 100
    return "displayed weekly ledger changes actual cash; overdraft becomes debt once; repayment reduces both"


def test_event_pack_balanced_and_media_is_automatic_content():
    assert len(data.EVENTS_V125) == 36
    cats = {}
    for e in data.EVENTS_V125:
        cats[e.get("category")] = cats.get(e.get("category"), 0) + 1
    assert cats.get("media") == 12, cats
    assert events.validate_event_pack() == []
    assert len(data.all_events()) >= 487 + len(getattr(data, "EVENTS_V127", []))
    # An absurd legacy reward gets stage-capped rather than breaking economy.
    am = Fighter.new_player("AM", "P", country_by_name("Greece"), "Boxing")
    capped = events.balanced_event_effects(am, {"money": 99999, "striking": 30, "fame": 50})
    assert capped["money"] == 750 and capped["striking"] == 4 and capped["fame"] == 6, capped
    # Same-category repetition is deliberately damped.
    pro = _player(); evt = next(e for e in data.EVENTS_V125 if e.get("category") == "media")
    ctx = events.context_pack(pro); base = ai.event_score(pro, evt, ctx)
    pro.story_flags["last_event_category"] = "media"; pro.story_flags["event_category_streak"] = 2
    assert ai.event_score(pro, evt, ctx) < base
    return "36 contextual events added (12 media); effects are capped and repeated categories are damped"



def test_v125_events_do_not_swallow_old_content():
    from .tests_123 import _profile
    random.seed(1250)
    shares = {}
    for kind in ("rising_am", "hurt_loss", "pro", "contender", "camp"):
        f = _profile(kind); ctx = events.context_pack(f)
        pool = [e for e in data.all_events(newest_first=True) if events.eligible(f, e, ctx)]
        weights = [ai.event_score(f, e, ctx) for e in pool]
        picks = random.choices(pool, weights=weights, k=1800)
        share = sum(str(e.get("id", "")).startswith("v125_") for e in picks) / len(picks)
        shares[kind] = share
        assert share <= 0.15, (kind, share)
    return "1.25 pack stays supplemental: " + ", ".join("%s %.0f%%" % (k, v*100) for k,v in shares.items())

def test_event_debt_choice_really_repays_debt():
    p = _player(); p.age = 18; p.money = 500; p.debt = 1000
    events.apply_effects(p, {"money": -100, "debt": -100})
    assert p.money == 400 and p.debt == 900, (p.money, p.debt)
    return "debt event/payment effects use currency scale instead of being clamped like a 0-100 stat"


def test_long_screen_pause_does_not_depend_on_tty():
    c = GameConsole(width=44, fast=True, color=False)
    seen=[]
    with patch.object(builtins, "input", side_effect=lambda prompt="": seen.append(prompt) or ""):
        c.continue_prompt("Press Enter to continue")
    assert seen and "Press Enter to continue" in seen[0]
    return "phone consoles that report non-TTY still get an Enter-to-continue prompt"


def test_lifestyle_has_no_dead_g_or_manual_media_menu():
    p = _player(); p.fame = 10
    class Q:
        def __init__(self): self.lines=[]
        def header(self,*a,**k): pass
        def print(self,x="",**k): self.lines.append(str(x))
        def ask(self,*a,**k): return "X"
        def warn(self,*a,**k): pass
        def pause(self,*a,**k): pass
    q=Q(); career.lifestyle_menu(q, p, None)
    visible="\n".join(q.lines)
    assert "  G)" not in visible
    assert "Social media" not in visible and "Media" not in visible
    assert "Gym" not in visible
    q2=Q(); career.coach_talk_menu(q2, p)
    coach_visible="\n".join(q2.lines)
    assert "Gym rooms & teammates" in coach_visible
    return "gym lives only under Coach; media is no longer a manual weekly menu"


def test_forensic_audit_catches_ufc_playtest_shape():
    p = _player(); p.org_contract = {"org":"", "fights_left":6, "purse_win":1000, "purse_show":500,
                                     "exclusive":True, "room":"ufc"}
    p.story_flags.update({"org_belt":"LFA", "title_offer_week":426, "ufc_rank":7})
    p.fight_history = [{"event":"DWCS", "pro":True, "result":"Win"}]
    codes={x["code"] for x in diagnostics.audit_playtest_state(p)}
    assert {"blank_contract_org", "stale_promotion_belt", "premature_ufc_title_offer"} <= codes, codes
    return "playtest exporter automatically flags the UFC contract/belt/title contradiction family"


def main():
    tests=(
        test_ufc_contract_corruption_repairs_toward_visible_org,
        test_ufc_title_requires_ufc_resume_and_specific_rank,
        test_weight_campaign_tracks_real_loss_and_bully_tradeoff,
        test_supplement_brand_sponsor_supplies_legal_products_free,
        test_money_ledger_and_debt_are_one_balance_sheet,
        test_event_pack_balanced_and_media_is_automatic_content,
        test_v125_events_do_not_swallow_old_content,
        test_event_debt_choice_really_repays_debt,
        test_long_screen_pause_does_not_depend_on_tty,
        test_lifestyle_has_no_dead_g_or_manual_media_menu,
        test_forensic_audit_catches_ufc_playtest_shape,
    )
    for t in tests:
        print("PASS", t())
    print("ALL 1.25 JUNIOR-HANDOFF CHECKS OK")

if __name__ == "__main__":
    main()
