#!/usr/bin/env python3
"""A check that could not run is not a check that failed.

    python3 .github/scripts/test_preflight_team_check.py

preflight.sh read the repository's team list through `gh api ... 2>/dev/null`.
Listing a repository's teams needs a permission datum-police does not hold, so
the call failed, the error went to /dev/null, and an empty result was reported
as `team 'X' has NO access` -- with a printed fix that granted a permission the
team already had. The first real adoption to reach this check was blocked by
it, and the team was fine.

The first fix assumed the call FAILED. It does not: the endpoint returns 200
and a list filtered to what the caller may see, which for datum-police is
EMPTY. So "our team has no access" and "this token sees no teams at all"
arrived identically, and the second was reported as the first -- twice, because
the first fix did not change what happens when the call succeeds.

THE COUNT IS THE TELL. Zero teams is not an answer about one team. Every
repository in the organisation has at least one, so an empty list describes the
token, not the team.

    call fails                    -> ? unknown, print what GitHub said
    call works, ZERO teams        -> ? unknown, it is a visibility limit
    call works, teams but not ours-> ✗ the real failure
    call works, ours has push     -> ✓

Only the COUNT is ever printed, never team names: this repository is public and
so are its Actions logs.

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
        # 200 with an EMPTY list -- what datum-police actually gets.
        invisible) echo "[]" ;;
        # Teams exist and ours is genuinely not among them.
        none)      echo '[{"slug":"admin-core","permission":"admin"}]' ;;
        read)      echo '[{"slug":"admin-core","permission":"admin"},{"slug":"ember-capital","permission":"read"}]' ;;
        *)         echo '[{"slug":"admin-core","permission":"admin"},{"slug":"ember-capital","permission":"push"}]' ;;
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
# --- the case the first fix missed ---------------------------------------
code, out = preflight("invisible")
check("200 with an EMPTY list is unknown, not 'your team has no access'",
      "NO teams" in out and "?" in out and "NO access" not in out,
      "the endpoint does not fail — it returns a filtered list, and for this "
      "token the filter removes everything")
check("...and does not block adoption either",
      code == 0, f"exit {code}")
check("...and says plainly it describes the token, not the team",
      "limit on what the token may see" in out, out)
check("...and prints no team NAMES — this repo's logs are public",
      "admin-core" not in out, "only the count may be printed")

# A leak needs teams to exist before it can leak them, so check every mode
# where the stub returns some. `ember-capital` is fine — it came from the form
# and is already in the log; `admin-core` is a name preflight learned.
for _m in ("forbidden", "invisible", "none", "read", "push"):
    _, _o = preflight(_m)
    check(f"no unrelated team name reaches the log in mode '{_m}'",
          "admin-core" not in _o,
          "this repository is public and so are its Actions logs")

# --- the real failure still fails ----------------------------------------
code, out = preflight("none")
check("teams exist but ours is not among them -- still ✗",
      "not among the 1 team(s)" in out and "✗" in out and code == 1,
      f"exit {code}: {out}")
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
