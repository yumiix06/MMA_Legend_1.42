"""Save auditor and repair tool.

Older saves predate systems that later code assumes exist. A 1.15 save, for
example, records `organization = "Cage Warriors"` but has no `org_contract`,
so `contracts.active()` reports the fighter as a free agent even though every
screen says they are signed. This module finds those gaps and closes them.

Run it against a save file:

    python3 -m tools.save_repair /path/to/save.json          # audit only
    python3 -m tools.save_repair /path/to/save.json --write  # write repaired copy
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def audit_player(p: dict) -> list:
    """Return a list of (severity, message, fix_key) findings."""
    out = []
    from mma_legend import record as _rec

    hist = list(p.get("fight_history") or [])
    pro_rows = [h for h in hist if _rec.is_mma(h) and _rec.is_pro_row(h)]
    am_rows = [h for h in hist if _rec.is_mma(h) and not _rec.is_pro_row(h)]

    def wl(rows):
        w = sum(1 for h in rows if str(h.get("result", "")).startswith("W"))
        l = sum(1 for h in rows if str(h.get("result", "")).startswith("L"))
        return [w, l, len(rows) - w - l]

    stored = list(p.get("pro_record") or [0, 0, 0])
    derived = wl(pro_rows)
    if pro_rows and stored != derived:
        out.append(("HIGH", "pro record %s disagrees with ledger %s (%d pro rows)"
                    % (stored, derived, len(pro_rows)), "pro_record"))

    stored_am = list(p.get("amateur_record") or [0, 0, 0])
    derived_am = wl(am_rows)
    if am_rows and stored_am != derived_am:
        out.append(("LOW", "amateur record %s vs untagged-MMA rows %s"
                    % (stored_am, derived_am), None))

    org = str(p.get("organization") or "")
    contract = p.get("org_contract")
    if org and org not in ("", "Regional", "none") and not isinstance(contract, dict):
        out.append(("HIGH", "signed to %s but no org_contract exists — the game "
                    "will treat you as a free agent" % org, "org_contract"))
    elif isinstance(contract, dict) and contract.get("org"):
        if "weeks_left" not in contract:
            out.append(("MED", "contract has no weeks_left (pre-1.9 shape)", "contract_weeks"))

    if p.get("money") is not None and p.get("debt") is None:
        out.append(("LOW", "no debt field — overdraft tracking inactive", "debt"))

    if p.get("story_flags") is None:
        out.append(("MED", "no story_flags block", "story_flags"))

    return out


def repair_player(p: dict) -> list:
    """Apply fixes. Returns list of applied descriptions."""
    from mma_legend import record as _rec
    done = []

    flags = p.get("story_flags")
    if not isinstance(flags, dict):
        flags = {}
        p["story_flags"] = flags
        done.append("added story_flags")

    # Record baseline, so later derived-record syncs cannot wipe the career.
    _rec.repair_dict(p)
    done.append("record baseline set: %s" % flags.get("record_baseline"))

    org = str(p.get("organization") or "")
    contract = p.get("org_contract")
    if org and org not in ("", "Regional", "none") and not isinstance(contract, dict):
        wins = int((p.get("pro_record") or [0, 0, 0])[0])
        p["org_contract"] = {
            "org": org,
            "fights_left": 3 if wins >= 10 else 4,
            "fights_total": 3 if wins >= 10 else 4,
            "weeks_left": 78,
            "signed_week": int(p.get("week") or 1),
            "purse_win": 0,
            "purse_show": 0,
            "exclusive": True,
            "room": "mid" if wins >= 10 else "regional",
        }
        done.append("created %s contract (was reading as free agent)" % org)
    elif isinstance(contract, dict) and contract.get("org") and "weeks_left" not in contract:
        contract["weeks_left"] = 78
        contract.setdefault("fights_left", 3)
        contract.setdefault("exclusive", True)
        done.append("gave legacy contract a term")

    if p.get("debt") is None:
        p["debt"] = 0
        done.append("added debt field")

    return done


def audit_file(path: Path, write: bool = False) -> int:
    from mma_legend import record as _rec
    data = json.loads(path.read_text(encoding="utf-8"))
    p = data.get("player") or {}
    print("== %s ==" % path.name)
    print("   game_version %s  save_version %s" % (
        data.get("game_version"), data.get("save_version")))
    print("   %s, week %s, %s-%s pro" % (
        p.get("name"), p.get("week"),
        (p.get("pro_record") or [0])[0], (p.get("pro_record") or [0, 0])[1]))
    findings = audit_player(p)
    if not findings:
        print("   no issues found")
    for sev, msg, _k in findings:
        print("   [%s] %s" % (sev, msg))
    if write:
        applied = repair_player(p)
        pool = data.get("pool") or {}
        n = 0
        for row in (pool.get("fighters") or []):
            if isinstance(row, dict):
                _rec.repair_dict(row)
                n += 1
        out = path.with_name(path.stem + "_repaired.json")
        out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print("   repaired -> %s" % out.name)
        for a in applied:
            print("     - %s" % a)
        print("     - baselined %d pool fighters" % n)
    return len(findings)


def main(argv=None) -> int:
    argv = list(argv or sys.argv[1:])
    write = "--write" in argv
    paths = [Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 1
    for pth in paths:
        if pth.exists():
            audit_file(pth, write)
        else:
            print("missing: %s" % pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
