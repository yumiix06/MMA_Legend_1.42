"""1.33 maintenance/refactor regression gates."""
from __future__ import annotations

import json
import tempfile
import types
import sys
from pathlib import Path
from unittest.mock import patch

from mma_legend import constants, record
from tools import build_release, save_repair
from tests import runner

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_package_is_free_of_versioned_regression_modules():
    stray = sorted(p.name for p in (ROOT / "mma_legend").glob("tests*.py"))
    assert not stray, stray
    assert not (ROOT / "mma_legend" / "rng.py").exists(), "unused replay RNG helper should not ship"
    assert (ROOT / "tests" / "runner.py").is_file()
    return "regression code is separated from runtime and the unused replay RNG stub is removed"


def test_runner_executes_run_only_suites():
    class Suite:
        called = False
        @staticmethod
        def run():
            Suite.called = True
    with patch("tests.runner.importlib.import_module", return_value=Suite):
        assert runner.run_module("tests.fake") is True
    assert Suite.called
    return "full-suite runner accepts run() as well as main() and cannot silently skip 1.32-style suites"


def test_save_repair_write_path_is_import_safe():
    payload = {
        "save_version": 17,
        "game_version": "1.32.0",
        "player": {
            "name": "Repair QA", "week": 10, "pro_record": [1, 0, 0],
            "amateur_record": [0, 0, 0], "fight_history": [],
            "organization": "LFA", "org_contract": None,
            "money": 100, "story_flags": {},
        },
        "pool": {"fighters": []},
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "legacy.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        save_repair.audit_file(path, write=True)
        repaired = path.with_name("legacy_repaired.json")
        assert repaired.is_file()
        row = json.loads(repaired.read_text(encoding="utf-8"))["player"]
        assert row["org_contract"]["org"] == "LFA"
    return "save repair write mode works when imported, without relying on __main__ globals"




def test_launcher_drops_only_cached_foreign_builds():
    import main as launcher
    real_pkg = sys.modules.get("mma_legend")
    real_app = sys.modules.get("mma_legend.app")
    fake = types.ModuleType("mma_legend")
    fake.__file__ = "/tmp/old_build/mma_legend/__init__.py"
    fake_app = types.ModuleType("mma_legend.app")
    sys.modules["mma_legend"] = fake
    sys.modules["mma_legend.app"] = fake_app
    launcher._clear_stale_package()
    assert "mma_legend" not in sys.modules and "mma_legend.app" not in sys.modules
    if real_pkg is not None:
        sys.modules["mma_legend"] = real_pkg
    if real_app is not None:
        sys.modules["mma_legend.app"] = real_app
    return "launcher removes a cached foreign build without scanning sibling folders"

def test_explicit_side_sport_history_is_not_mma():
    assert record.is_mma({"sport": "combat_sambo", "ruleset": "combat_sambo"}) is False
    assert record.is_mma({"sport": "boxing", "ruleset": "boxing"}) is False
    assert record.is_mma({"sport": "judo", "ruleset": "judo"}) is False
    assert record.is_mma({"sport": "mma", "ruleset": "mma"}) is True
    assert record.is_mma({"event": "Balkan Combat Fight Night 4"}) is True
    assert record.is_mma({"event": "Combat Sambo National Championships"}) is False
    return "explicit side-sport ledgers no longer leak into MMA history classification"

def test_release_tree_has_no_runtime_artifacts_or_redundant_launcher():
    probes = [
        ROOT / "mma_legend" / "__pycache__" / "x.pyc",
        ROOT / "debug_log.txt",
        ROOT / "playtest_trace.jsonl",
        ROOT / "save_auto.json",
    ]
    assert all(build_release.keep(p) is False for p in probes)
    assert not (ROOT / "run.py").exists()
    assert (ROOT / "START.py").is_file() and (ROOT / "main.py").is_file()
    return "release builder excludes caches/logs/saves and the redundant third launcher is gone"


def test_version_and_document_layout():
    assert tuple(map(int, constants.GAME_VERSION.split("."))) >= (1, 33, 0)
    assert (ROOT / "docs" / "current" / "ARCHITECTURE.md").is_file()
    assert (ROOT / "docs" / "current" / "VERSION_HISTORY.md").is_file()
    assert (ROOT / "tools" / "build_release.py").is_file()
    return "runtime, developer tools/tests and documentation have explicit homes"


def run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        note = fn()
        print("PASS", fn.__name__, note)
    print("ALL 1.33 MAINTENANCE CHECKS OK")


def main():
    run()


if __name__ == "__main__":
    run()
