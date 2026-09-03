#!/usr/bin/env python3
"""Mark repositories adopted once the standard is actually ON their default branch.

    python3 reconcile_adoption.py [--apply]

A repository is adopted when `.copier-answers.yml` is on its DEFAULT BRANCH. That
is what a merged adoption pull request leaves behind, and what a repository born
from the scaffold already carries. The conformance audit reads the same file, so
this is not a new signal.

WHY THIS IS NOT DONE BY THE ADOPTION WORKFLOW. It used to be, and it was wrong:
the property was written when the pull request OPENED, which meant a repository
was marked adopted -- and, under the organisation ruleset keyed on this property,
branch-protected -- while the pull request sat unreviewed. `adopted` has to mean
"the standard is on the default branch", not "somebody asked".

WHY A SWEEP AND NOT A WEBHOOK. It converges. A pull request merged while this is
down is picked up on the next run, a repository adopted by hand is picked up
without anybody remembering, and a property removed by accident comes back. An
event handler gets exactly one chance.

WHAT IT DELIBERATELY CANNOT DO. It only ever SETS `adopted`, and only on a
repository that demonstrably carries the file. It never removes a value, never
writes `exempt`, and never touches a repository it cannot see the file on. That
matters because the property now controls branch protection: a credential that
could clear it could unprotect a repository. This one cannot.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ORG = os.environ.get("ORG", "datumlabsio")
PROPERTY = "datum-standard"
ADOPTED = "adopted"
MARKER = ".copier-answers.yml"


def gh(*args: str) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout


def live_repos() -> list[dict]:
    out = gh("api", f"/orgs/{ORG}/repos?per_page=100&type=all", "--paginate",
             "-q", '[.[]|select(.archived==false and .fork==false)'
                   '|{name,default_branch}]')
    repos: list[dict] = []
    for chunk in out.strip().split("\n"):
        if chunk.strip():
            repos.extend(json.loads(chunk))
    return repos


def carries_standard(repo: str, branch: str) -> bool:
    """Is the marker on the DEFAULT branch? A branch is not an adoption.

    The ref goes in the QUERY STRING, not as `-f ref=...`. On a GET, `gh api -f`
    sends a body field, and the request 404s -- so every repository looked
    unadopted and the sweep reported success having checked nothing. Caught by
    dry-running against the real organisation, where polaris obviously carries
    the file and came back false.
    """
    return bool(gh("api", f"repos/{ORG}/{repo}/contents/{MARKER}?ref={branch}",
                   "-q", ".sha"))


def current_value(repo: str) -> str | None:
    out = gh("api", f"repos/{ORG}/{repo}/properties/values",
             "-q", f'.[]|select(.property_name=="{PROPERTY}")|.value')
    return out.strip() or None


def set_adopted(repo: str) -> bool:
    r = subprocess.run(
        ["gh", "api", "-X", "PATCH", f"repos/{ORG}/{repo}/properties/values",
         "-f", f"properties[][property_name]={PROPERTY}",
         "-f", f"properties[][value]={ADOPTED}"],
        capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    apply = "--apply" in sys.argv
    to_set, already, untouched = [], [], 0

    for r in live_repos():
        name, branch = r["name"], r["default_branch"]
        if not carries_standard(name, branch):
            untouched += 1
            continue
        value = current_value(name)
        if value == ADOPTED:
            already.append(name)
        elif value is None:
            to_set.append(name)
        else:
            # `exempt`, or anything a person chose. Never overwrite a human.
            print(f"::notice::{name} carries the standard but is marked "
                  f"'{value}' — left alone.")

    print(f"::notice::{len(already)} already marked, {len(to_set)} to mark, "
          f"{untouched} do not carry the standard.")

    failed = []
    for name in to_set:
        if not apply:
            print(f"    would set {PROPERTY}={ADOPTED} on {name}")
            continue
        if set_adopted(name):
            print(f"::notice::Set {PROPERTY}={ADOPTED} on {name}.")
        else:
            failed.append(name)

    if failed:
        print(f"::error::Could not set the property on: {', '.join(failed)}. "
              "The App needs custom-properties write.")
        return 1

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and (to_set or already):
        with open(summary, "a") as fh:
            fh.write(f"### Adoption\n\n**{len(already) + len(to_set)}** "
                     f"repositories carry the standard on their default branch.\n\n")
            if to_set:
                verb = "Marked" if apply else "Would mark"
                fh.write(f"{verb} adopted: {', '.join(f'`{n}`' for n in to_set)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
