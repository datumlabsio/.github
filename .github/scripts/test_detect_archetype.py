#!/usr/bin/env python3
"""The archetype detector must not guess quietly.

    python3 .github/scripts/test_detect_archetype.py

Getting this wrong lands the wrong linter config in a pull request -- cheap and
visible, because nobody has merged it. The failure worth preventing is the
CONFIDENT wrong answer: a root-only scan called `polaris` "generic" because a
monorepo keeps its markers in subdirectories, which would have put Python
linting on a repository that is mostly dbt and Kubernetes.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("da", HERE / "detect_archetype.py")
da = importlib.util.module_from_spec(spec)
spec.loader.exec_module(da)

CASES = [
    ("a python app",            ["pyproject.toml"],                       "application"),
    ("setup.py counts too",     ["setup.py"],                             "application"),
    ("a node front end",        ["package.json"],                         "web-app"),
    ("a dbt project",           ["dbt_project.yml"],                      "dbt-project"),
    ("gitops",                  ["kustomization.yaml"],                   "gitops"),
    ("nothing recognisable",    ["Makefile", "main.go"],                  "generic"),
    ("two markers at the root", ["pyproject.toml", "package.json"],       "monorepo"),
    # The polaris shape: no marker at the root at all.
    ("markers one level down",  ["warehouse/dbt_project.yml"],            "dbt-project"),
    ("a real monorepo",         ["app/pyproject.toml", "web/package.json"], "monorepo"),
    ("two dirs, same kind",     ["a/pyproject.toml", "b/pyproject.toml"], "monorepo"),
    # A marker inside a vendored tree is not a component.
    ("node_modules ignored",    ["node_modules/x/package.json"],          "generic"),
    ("dot-dirs ignored",        [".venv/pyproject.toml"],                 "generic"),
]

failures = []
for name, files, want in CASES:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for f in files:
            p = root / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x")
        got, why = da.detect(root)
    ok = got == want
    print(f"    [{'ok' if ok else 'FAIL'}] {name}: {got}" + ("" if ok else f" (wanted {want})"))
    if not ok:
        failures.append(name)

# It must always return something usable. A crash in detection would take the
# whole adoption run down for a repository shaped in a way nobody anticipated.
with tempfile.TemporaryDirectory() as td:
    got, _ = da.detect(Path(td))
    ok = got == "generic"
    print(f"    [{'ok' if ok else 'FAIL'}] an empty repository is generic, not a crash")
    if not ok:
        failures.append("empty repo")

if failures:
    print(f"\nFAIL: {len(failures)} case(s): {', '.join(failures)}")
    sys.exit(1)
print(f"\nOK: {len(CASES) + 1} cases")
