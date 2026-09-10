"""Run every versioned regression module.

Usage: python3 -m tests.runner
A regression module may expose either main() or run(); both are supported so a
new suite cannot be silently skipped merely because its entry-point name differs.
"""
from __future__ import annotations

import importlib
import pkgutil
import traceback

import tests


def module_names() -> list[str]:
    return sorted(
        "tests." + item.name
        for item in pkgutil.iter_modules(tests.__path__)
        if item.name.startswith("tests_")
    )


def run_module(name: str) -> bool:
    module = importlib.import_module(name)
    entry = getattr(module, "main", None) or getattr(module, "run", None)
    if not callable(entry):
        raise RuntimeError(f"{name} has no callable main() or run()")
    entry()
    return True


def main() -> int:
    bad = 0
    for name in module_names():
        print("====", name)
        try:
            run_module(name)
        except Exception:
            bad += 1
            traceback.print_exc()
    print("FAILED MODULES", bad)
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
