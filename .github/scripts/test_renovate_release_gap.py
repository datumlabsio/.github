#!/usr/bin/env python3
"""A bump that must ship cannot be typed as one that never ships.

    python3 .github/scripts/test_renovate_release_gap.py

scaffolds/copier.yml carries `actions_version`, and that single value decides
which CI version every newly adopted repository is born on. Adoption renders
from the latest scaffolds RELEASE -- not from main.

Renovate typed that bump `chore`. scaffolds cuts a release from feat, fix and
breaking commits only, so the release workflow ran, reported success, and
produced nothing:

    ##[notice]No feat, fix or breaking commits since the last tag.
              Nothing to release.

v1.5.0 sat on main while every adoption still landed v1.4.0, and would have
until an unrelated feat or fix happened along. ember was adopted onto a version
we had already moved off that morning.

THE SCOPE IS THE OTHER HALF OF THE FIX. Typing every datumlabsio/** bump `fix`
org-wide would work and would also make polaris -- which has release.yml AND
promote-release.yml -- cut a release, and a promotion, on every actions bump.
The override belongs to the pin that gates a release, not to all of them.

This asserts the CONFIGURATION. It cannot prove how Renovate resolves rules at
run time; the proof of that is the next actions bump cutting a scaffolds tag.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CFG = json.loads((Path(__file__).resolve().parents[2] / "default.json").read_text())
RULES = CFG["packageRules"]
RELEASABLE = {"feat", "fix"}
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"    [{'ok' if ok else 'FAIL'}] {name}{'' if ok else f' — {detail}'}")
    if not ok:
        FAILURES.append(name)


def matches_copier(rule: dict) -> bool:
    return any("copier.yml" in f for f in rule.get("matchFileNames", []))


check("the default commit type is still one that cuts NO release",
      CFG.get("semanticCommitType") == "chore",
      "if this stops being chore the override below is pointless, not wrong")

copier = [r for r in RULES if matches_copier(r)]
check("exactly one rule speaks for the copier.yml pin",
      len(copier) == 1, f"{len(copier)} rules")

if copier:
    r = copier[0]
    check("...and types it so a release is actually cut",
          r.get("semanticCommitType") in RELEASABLE,
          f"{r.get('semanticCommitType')!r} — scaffolds releases on feat/fix only")
    check("...and is narrowed to the org's own packages",
          r.get("matchPackageNames") == ["datumlabsio/**"], str(r.get("matchPackageNames")))
    check("...and to the manager that actually reads copier.yml",
          r.get("matchManagers") == ["custom.regex"], str(r.get("matchManagers")))
    check("...and matches the pin at the repository root, not only nested",
          "copier.yml" in r.get("matchFileNames", []),
          "`**/copier.yml` alone can miss a root-level file")

    grouped = next(n for n, x in enumerate(RULES) if x.get("groupName") == "datumlabsio actions")
    check("...and comes AFTER the datumlabsio rule, so the type wins",
          RULES.index(r) > grouped,
          "packageRules merge in order; an earlier rule cannot override a later one")
    check("...and does not re-group, so it inherits its own pull request",
          "groupName" not in r,
          "setting a group here would split the pin out of the one it belongs to")

# --- the blast radius, which is the reason this is scoped -----------------
wide = [r for r in RULES
        if r.get("semanticCommitType") in RELEASABLE
        and r.get("matchPackageNames") == ["datumlabsio/**"]
        and not matches_copier(r)]
check("NO rule types every datumlabsio bump as releasable",
      not wide,
      "polaris has release.yml and promote-release.yml — that would cut a "
      "release and a promotion on every actions bump")

gha = [r for r in RULES
       if "github-actions" in (r.get("matchManagers") or [])
       and r.get("semanticCommitType") in RELEASABLE]
check("...and the github-actions manager keeps its non-releasing type",
      not gha, str(gha))

if FAILURES:
    print(f"\nFAIL: {len(FAILURES)}: {', '.join(FAILURES)}")
    sys.exit(1)
print("\nOK: the pin that gates a release is typed to cut one, and only that pin")
