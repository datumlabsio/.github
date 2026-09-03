#!/usr/bin/env python3
"""Warnings appear only when the condition is real.

    python3 .github/scripts/test_adoption_warnings.py

A pull request full of boilerplate caveats gets skimmed, and then the one that
mattered gets skimmed with it. So the test that matters most is the NEGATIVE one:
a repository with none of these problems must produce no output at all.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "aw", Path(__file__).resolve().parent / "adoption_warnings.py")
aw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aw)

FAILURES: list[str] = []


def build(files: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp())
    for rel, body in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return d


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"    [{'ok' if ok else 'FAIL'}] {name}{'' if ok else f' — {detail}'}")
    if not ok:
        FAILURES.append(name)


CLEAN = {
    "CLAUDE.md": "# demo\n",
    "pyproject.toml": '[tool.coverage.run]\nsource = ["src"]\n',
    "src/demo/__init__.py": "",
}

# --- the one that matters most -------------------------------------------
w = aw.warnings_for(build(CLEAN))
check("a clean repository produces NO warnings", w == [], f"got {len(w)}: {w}")

# --- duplicate gate callers ----------------------------------------------
w = aw.warnings_for(build({**CLEAN,
    ".github/workflows/datum-police.yml":
        "on: [pull_request]\njobs:\n  s:\n    uses: datumlabsio/actions/.github/workflows/security-baseline.yml@v0.27.0\n"}))
check("an existing caller is reported", any("twice" in x for x in w), str(w))
check("...naming the file and the version",
      any("datum-police.yml" in x and "v0.27.0" in x for x in w), str(w))

# The files adoption just added are not "existing" callers, or every single
# adoption would warn about itself.
w = aw.warnings_for(build({**CLEAN,
    ".github/workflows/ci.yml":
        "jobs:\n  a:\n    uses: datumlabsio/actions/.github/workflows/application.yml@v1.0.0\n"}))
check("the files adoption just added are not reported as duplicates",
      not any("twice" in x for x in w), str(w))

# --- coverage ------------------------------------------------------------
# CLEAN deliberately has src/, so this case must NOT reuse it -- the ember shape
# is a repository whose code is in ecap/ while coverage still names src/.
w = aw.warnings_for(build({
    "CLAUDE.md": "# demo\n",
    "ecap/__init__.py": "",
    "pyproject.toml": '[tool.coverage.run]\nsource = ["src"]\n'}))
check("coverage naming a missing directory is reported",
      any("does not exist" in x for x in w), str(w))
check("...and it names the packages that DO exist",
      any("`ecap`" in x for x in w), str(w))

w = aw.warnings_for(build({**CLEAN, "ecap/__init__.py": "",
    "pyproject.toml": '[tool.coverage.run]\nsource = ["ecap"]\n'}))
check("coverage naming a real directory is NOT reported",
      not any("Coverage" in x for x in w), str(w))

w = aw.warnings_for(build({**CLEAN, "ecap/__init__.py": "",
    "pyproject.toml": "[project]\nname='x'\n"}))
check("no coverage config at all is reported, and names the real packages",
      any("no [tool.coverage.run]" in x and "`ecap`" in x for x in w), str(w))

# --- CLAUDE.md -----------------------------------------------------------
w = aw.warnings_for(build({k: v for k, v in CLEAN.items() if k != "CLAUDE.md"}))
check("a missing CLAUDE.md is reported", any("CLAUDE.md" in x for x in w), str(w))

# --- it must never crash -------------------------------------------------
for name, files in [("empty repo", {}), ("binary pyproject", {"pyproject.toml": "\x00\xff"}),
                    ("unreadable workflow", {".github/workflows/x.yml": "\x00"})]:
    try:
        aw.warnings_for(build(files))
        check(f"survives {name}", True)
    except Exception as e:  # noqa: BLE001
        check(f"survives {name}", False, repr(e))

if FAILURES:
    print(f"\nFAIL: {len(FAILURES)}: {', '.join(FAILURES)}")
    sys.exit(1)
print("\nOK: warnings fire only on real conditions")
