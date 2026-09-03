#!/usr/bin/env python3
"""Any step that runs copier against the private scaffold must give it a token.

    python3 .github/scripts/test_copier_has_a_credential.py

copier shells out to its OWN `git clone`. actions/checkout's credential is local
to the clone it made, so a step that runs copier without configuring git gets:

    fatal: could not read Username for 'https://github.com'

on a machine with no terminal. actions/CLAUDE.md records this as rediscovered
four times before someone wrote it down. Writing it down did not stop the fifth
-- adopt-repo.yml hit it in production, six steps away from new-repo.yml which
does it correctly.

So it is a check now. A rule that depends on reading a document is not a rule.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"
# Distinguishing a real invocation from prose about one. Both exist in these
# files: a comment saying `copier update` is the right tool, and a PR body
# telling somebody to run `copier update -d ...`. An earlier version of this
# anchored on the start of the line and quietly missed new-repo.yml, whose call
# is `if ! uvx --from copier copier copy ...` -- a gate checking less than it
# claims, which is the failure it exists to prevent.
CALL = re.compile(r"\bcopier\s+(?:copy|update)\b")


def invocations(text: str) -> int:
    """Lines that actually RUN copier, ignoring comments and backticked prose."""
    n = 0
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # Drop anything inside backticks before looking -- that is documentation.
        without_prose = re.sub(r"`[^`]*`", "", line)
        if CALL.search(without_prose):
            n += 1
    return n


HAS_CREDENTIAL = re.compile(r'url\."https://x-access-token:\$\{?GH_TOKEN\}?@github\.com/"\.insteadOf')

failures: list[str] = []
checked = 0

for wf in sorted(WORKFLOWS.glob("*.y*ml")):
    text = wf.read_text(encoding="utf-8")
    # Split on step boundaries so a credential configured in a DIFFERENT step
    # does not count -- `git config --global` persists across steps in practice,
    # but relying on that makes the two steps silently order-dependent.
    steps = re.split(r"\n      - name:", text)
    for step in steps:
        if not invocations(step):
            continue
        checked += 1
        name = step.split("\n")[0].strip() or wf.name
        if not HAS_CREDENTIAL.search(step):
            failures.append(f"{wf.name} :: {name}")

print(f"    checked {checked} step(s) that run copier")
for f in failures:
    print(f"    [FAIL] {f} runs copier with no credential for the private scaffold")

if not checked:
    print("    [FAIL] found no copier steps at all — has the pattern changed?")
    sys.exit(1)
if failures:
    print("\nAdd this to the step, before copier runs:\n")
    print('    git config --global \\')
    print('      url."https://x-access-token:${GH_TOKEN}@github.com/".insteadOf \\')
    print('      "https://github.com/"')
    sys.exit(1)
print("    [ok] every copier step configures a credential")
