#!/usr/bin/env python3
"""A check that could not run is not a check that failed.

    python3 .github/scripts/test_preflight_team_check.py

preflight.sh read the repository's team list through `gh api ... 2>/dev/null`.
Listing a repository's teams needs a permission datum-police does not hold, so
the call failed, the error went to /dev/null, and an empty result was reported
as `team 'X' has NO access` -- with a printed fix that granted a permission the
team already had. The first real adoption to reach this check was blocked by
it, and the team was fine.

That is the second time a discarded error sent somebody to fix the wrong thing.
The first was the property's edit permission, and it cost a granted permission
and an afternoon. So the distinction is asserted, not remembered:

    call fails            -> ? UNKNOWN, and print what GitHub actually said
    call works, no team   -> ✗ the real failure
    call works, has push  -> ✓

`gh` is stubbed on PATH. Nothing here touches the network.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "preflight.sh"
FAILURES: list[str] = []

# Every endpoint preflight touches, in the shape it reads them.
STUB = r'''#!/usr/bin/env bash
# A fake `gh`. TEAMS_MODE decides only what the team endpoint does.
args="$*"
case "$args" in
  *"repos/datumlabsio/ember/teams"*)
      case "${TEAMS_MODE}" in
        forbidden) echo "gh: Resource not accessible by integration (HTTP 403)" >&2; exit 1 ;;
        none)      exit 0 ;;
        read)      echo "read" ;;
        *)         echo "push" ;;
      esac ;;
  *"contents/.copier-answers.yml"*) exit 1 ;;
  *"repos/datumlabsio/ember"*".default_branch"*) echo "master" ;;
  *"repos/datumlabsio/ember"*".name"*) echo "ember" ;;
  *"properties/schema/datum-standard"*) echo "org_and_repo_actors" ;;
  *) exit 1 ;;
esac
'''


def preflight(mode: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as td:
        binn = Path(td) / "bin"
        binn.mkdir()
        (binn / "gh").write_text(STUB)
        (binn / "gh").chmod(0o755)
        r = subprocess.run(["bash", str(SCRIPT), "datumlabsio", "ember", "ember-capital"],
                           env={**os.environ, "PATH": f"{binn}:{os.environ['PATH']}",
                                "TEAMS_MODE": mode},
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"    [{'ok' if ok else 'FAIL'}] {name}{'' if ok else f' — {detail}'}")
    if not ok:
        FAILURES.append(name)


# --- the regression ------------------------------------------------------
code, out = preflight("forbidden")
team = next((l for l in out.splitlines() if "team" in l or "CODEOWNERS" in l), "")
check("a team list we cannot READ is reported as unknown, not as no access",
      "?" in team and "NO access" not in out,
      "the team was fine; the token was not")
check("...and it does not block adoption on a thing that may be correct",
      code == 0, f"exit {code}")
check("...and prints what GitHub actually said, rather than a guess",
      "403" in out or "not accessible" in out,
      "the discarded error is the whole reason this took an afternoon twice")
check("...and says which permission would make it a real check",
      "Administration (read)" in out, out)

# --- the real failure still fails ----------------------------------------
code, out = preflight("none")
check("a team that genuinely has no access is still ✗",
      "NO access" in out and "✗" in out and code == 1, f"exit {code}")
check("...and the printed fix grants it",
      "permission=push" in out)

# --- wrong-but-present, and the happy path -------------------------------
code, out = preflight("read")
check("read-only access is ✗ too — CODEOWNERS would be inert",
      "not write" in out and code == 1, f"exit {code}")

code, out = preflight("push")
check("push is ✓ and preflight passes",
      "has push" in out and "✓" in out and code == 0, f"exit {code}")
check("...and a passing run says nothing about unknown teams",
      "?" not in out.split("DATUM_POLICE_APP_ID")[0].split("team")[-1][:80]
      or "cannot read" not in out, out[:200])

if FAILURES:
    print(f"\nFAIL: {len(FAILURES)}: {', '.join(FAILURES)}")
    sys.exit(1)
print("\nOK: cannot-read and no-access are told apart")
