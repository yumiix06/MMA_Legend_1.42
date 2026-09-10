"""1.24 playtest intelligence/observability regression checks."""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import zipfile

from mma_legend.data import country_by_name
from mma_legend.models import Fighter
from mma_legend.world import FighterPool
from mma_legend import booking, diagnostics, orgs, persistence, telemetry


def _pro(name, org="Balkan Combat", record=(1, 0, 0), skill=55):
    f = Fighter.new_npc(name, country_by_name("Greece"), style="Boxing")
    f.pro_debut = True
    f.organization = org
    f.room = "regional"
    f.weight_class = "Lightweight"
    f.pro_record = list(record)
    for s in ("striking", "kicks", "grappling", "submissions", "takedown_defense",
              "ground_control", "cardio", "strength", "speed", "ko_power", "durability", "fight_iq"):
        if hasattr(f, s):
            setattr(f, s, skill)
    return f


def test_resume_beats_hidden_power_in_rankings():
    p = Fighter.new_player("Player", "M", country_by_name("Greece"), "Boxing")
    p.pro_debut = True; p.organization = "Balkan Combat"; p.room = "regional"
    p.weight_class = "Lightweight"; p.pro_record = [0, 2, 0]; p.fame = 204
    for s in ("striking", "kicks", "grappling", "submissions", "takedown_defense",
              "ground_control", "cardio", "strength", "speed", "ko_power", "durability", "fight_iq"):
        if hasattr(p, s): setattr(p, s, 90)
    winner = _pro("Winner", record=(2, 0, 0), skill=50)
    one = _pro("One", record=(1, 0, 0), skill=50)
    pool = FighterPool(); pool.fighters = [winner, one]; pool.attach_player(p); pool.update_rankings()
    row = pool.get_org_top("Balkan Combat", "Lightweight", 10)
    names = [x.name for x in row]
    assert names.index("Player") > names.index("Winner"), names
    assert int(p.story_flags.get("org_rank", 99)) >= 3, p.story_flags
    return "0-2 high-skill/fame no longer ranks above 2-0 résumé"


def test_cross_org_exclusivity_and_early_pro_band():
    p = _pro("P", record=(0, 1, 0), skill=60); p.is_player = True
    ksw = _pro("KSW Vet", org="KSW", record=(6, 0, 0), skill=60)
    assert not booking.opponent_fits(p, ksw), "0-1 should not be fed 6-0"
    same = _pro("Balkan Peer", org="Balkan Combat", record=(1, 1, 0), skill=59)
    pool = FighterPool(); pool.fighters = [ksw, same]
    random.seed(2)
    opp = booking.pick_pool_opponent(p, pool, "regional", "Balkan Combat")
    assert opp.organization == "Balkan Combat", (opp.name, opp.organization)
    assert opp is not ksw
    return "exclusive cards stay in-org/free-agent and early pro band rejects 6-0"


def test_generated_fill_joins_card_org():
    p = _pro("P", record=(0, 0, 0), skill=60); p.is_player = True
    outsider = _pro("Outsider", org="KSW", record=(1, 0, 0), skill=60)
    pool = FighterPool(); pool.fighters = [outsider]; pool.next_id = 9000
    random.seed(7)
    opp = booking.pick_pool_opponent(p, pool, "regional", "Balkan Combat")
    assert opp.organization == "Balkan Combat", opp.organization
    assert opp in pool.fighters
    return "emergency opponent is registered onto the promotion roster"


def test_contract_has_real_terms():
    p = _pro("P", record=(3, 1, 0), skill=55)
    p.org_contract = None
    random.seed(4)
    orgs.sign_org(p, "Balkan Combat")
    c = p.org_contract or {}
    assert int(c.get("purse_win", 0)) > 0 and int(c.get("purse_show", 0)) > 0, c
    return "direct signing no longer stores $0/$0 paper"


def test_autosave_keeps_full_world():
    p = Fighter.new_player("P", "M", country_by_name("Greece"), "Boxing")
    pool = FighterPool(); pool.generate_world(120, 80)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "auto.json"
        persistence.autosave(p, pool, path=path, phase="test")
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["debug"]["world_pool_n"] == len(pool.fighters)
        assert raw["debug"]["saved_pool_n"] == len(pool.fighters)
        assert len(raw["pool"]["fighters"]) == len(pool.fighters)
    return "autosave serializes the same world the player was playing"


def test_playtest_bundle_contains_replay_evidence():
    class Q:
        def good(self, *a, **k): pass
        def warn(self, *a, **k): pass
        def print(self, *a, **k): pass
        def pause(self, *a, **k): pass
    p = Fighter.new_player("P", "M", country_by_name("Greece"), "Boxing")
    pool = FighterPool(); pool.generate_world(12, 8)
    telemetry.reset_runtime(); telemetry.set_screen("DASHBOARD"); telemetry.ui_output("Visible line")
    telemetry.prompt("Choice > "); telemetry.answer("A")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bundle.zip"
        assert persistence.export_playtest_bundle(Q(), p, pool, path=path)
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            assert {"playtest_snapshot.json", "playtest_summary.json"} <= names, names
            snap = json.loads(zf.read("playtest_snapshot.json"))
            tail = snap.get("playtest", {}).get("ui_tail", [])
            assert any(x.get("text") == "Visible line" for x in tail)
    return "one ZIP carries canonical save + exact recent UI/input evidence"


def test_audit_flags_supplied_playtest_shape():
    p = _pro("P", record=(0, 2, 0), skill=80); p.is_player = True
    p.story_flags["org_rank"] = 1
    p.narrative_tags = ["prospect", "pro", "contender", "journeyman", "title_contender"]
    p.org_contract = {"org": "Balkan Combat", "purse_win": 0, "purse_show": 0, "exclusive": True}
    codes = {x["code"] for x in diagnostics.audit_playtest_state(p)}
    assert {"rank_resume_mismatch", "title_tag_resume_mismatch", "career_tags_fragmented", "zero_contract_terms"} <= codes
    return "forensic audit surfaces contradictory career state automatically"


def main():
    for t in (
        test_resume_beats_hidden_power_in_rankings,
        test_cross_org_exclusivity_and_early_pro_band,
        test_generated_fill_joins_card_org,
        test_contract_has_real_terms,
        test_autosave_keeps_full_world,
        test_playtest_bundle_contains_replay_evidence,
        test_audit_flags_supplied_playtest_shape,
    ):
        print("PASS", t())
    print("ALL 1.24 OBSERVABILITY / INTELLIGENCE CHECKS OK")


if __name__ == "__main__":
    main()
