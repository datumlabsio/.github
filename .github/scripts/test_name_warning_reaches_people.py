#!/usr/bin/env python3
"""The repository-name warning reaches a person, and never reaches a shell.

The parser stopped refusing off-convention names (#88: 39 existing
repositories could never be adopted). The trade only works if the warning is
SEEN -- a `::warning::` in a run log nobody opens is the same as no warning --
so both flows carry it to where the requester reads: the adoption pull request
body, and the new-repo issue comment.

It carries the requester's own text, though. `${{ ... }}` inside `run:` is
template-expanded BEFORE the shell sees it, so an expression there is script
injection by anyone who can open an issue. It must arrive through `env:` and
be printed with printf '%s'.

Run: python3 .github/scripts/test_name_warning_reaches_people.py
"""

import pathlib
import re
import sys

import yaml

WF = pathlib.Path(__file__).resolve().parents[1] / "workflows"
EXPR = "steps.request.outputs.name_warning"
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


for name in ("adopt-repo.yml", "new-repo.yml"):
    doc = yaml.safe_load((WF / name).read_text())
    steps = [s for job in doc["jobs"].values() for s in job.get("steps", [])]

    in_env = [s for s in steps if EXPR in str((s.get("env") or {}).values())]
    in_run = [s.get("name") for s in steps if EXPR in (s.get("run") or "")]

    check(not in_run,
          f"{name}: the warning is interpolated straight into run: in {in_run} "
          f"-- that is script injection by anyone who can open an issue")
    check(in_env, f"{name}: no step receives the warning, so nobody sees it")

    for s in in_env:
        run = s.get("run") or ""
        # The variable inside a double-quoted ARGUMENT to a '%s' format --
        # printed as data. Prefixing it with a label in the same argument is fine.
        check(re.search(r"""printf\s+'[^']*%s[^']*'\s+"[^"]*\$NAME_WARNING""", run),
              f"{name}/{s.get('name')}: receives NAME_WARNING but does not "
              f"print it with printf '%s' -- either it is dropped, or it is "
              f"echoed in a way that can interpret its contents")
        check('[ -n "${NAME_WARNING:-}" ]' in run,
              f"{name}/{s.get('name')}: prints the warning unconditionally -- "
              f"an empty heading on every conforming request trains people to "
              f"skip it")

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    sys.exit(1)
print("PASS  the name warning reaches the requester in both flows, through env only")
