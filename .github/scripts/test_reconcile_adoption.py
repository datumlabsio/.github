#!/usr/bin/env python3
"""The reconciler must never do the two things that would be dangerous.

    python3 .github/scripts/test_reconcile_adoption.py

The property now controls branch protection through an organisation ruleset, so
a job that can CLEAR it can unprotect a repository. This one is built so it
cannot: it only ever writes `adopted`, and only where the marker is on the
default branch.

Also asserted: the ref goes in the query string. `gh api -f ref=...` on a GET
sends a body field, the request 404s, and every repository looks unadopted --
the sweep then reports success having checked nothing. That is exactly what the
first version did, and it passed its own run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "reconcile_adoption.py").read_text()
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"    [{'ok' if ok else 'FAIL'}] {name}{'' if ok else f' — {detail}'}")
    if not ok:
        FAILURES.append(name)


# --- it must not be able to clear or downgrade -----------------------------
# The value is written through a constant, so assert on both: every write uses
# the constant, and the constant is `adopted`.
# The body is JSON now, not form fields: {"property_name": PROPERTY, "value": ADOPTED}
writes = set(re.findall(r'"value":\s*(\w+)', SRC))
const = re.search(r'^ADOPTED\s*=\s*"([^"]+)"', SRC, re.M)
check("every write goes through the ADOPTED constant",
      writes == {"ADOPTED"}, f"writes {writes}")
check("and that constant is 'adopted'",
      bool(const) and const.group(1) == "adopted",
      const.group(1) if const else "<not found>")

check("it never writes 'exempt'", "exempt" not in re.sub(r"#.*|\"\"\".*?\"\"\"", "", SRC, flags=re.S),
      "'exempt' appears outside comments")

check("it never issues a DELETE", "DELETE" not in SRC and '"-X", "DELETE"' not in SRC)

# It must refuse to overwrite a value a person chose.
check("a value other than 'adopted' is left alone",
      "left alone" in SRC and "value is None" in SRC,
      "no branch that skips a human-set value")

# --- the bug that made it check nothing ------------------------------------
check("the ref is a query string, not -f",
      "?ref=" in SRC and '"-f", f"ref=' not in SRC,
      "-f ref= on a GET 404s and every repo looks unadopted")

# --- it must look at the DEFAULT branch ------------------------------------
check("the marker is checked on the default branch",
      "default_branch" in SRC and "carries_standard(name, branch)" in SRC)

# --- archived and forks are out of scope ------------------------------------
check("archived repositories are skipped", "archived==false" in SRC)
check("forks are skipped — their standard is not ours to claim", "fork==false" in SRC)

# --- a failed write must not be silent --------------------------------------
check("a failed write fails the job", "return 1" in SRC and "::error::" in SRC)

if FAILURES:
    print(f"\nFAIL: {len(FAILURES)}: {', '.join(FAILURES)}")
    sys.exit(1)
print(f"\nOK: 10 constraints hold")
