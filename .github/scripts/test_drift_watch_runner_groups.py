#!/usr/bin/env python3
"""A runner group is the only thing between a fork's pull request on a public
repository and code running on our own hardware, on the office LAN.

Nothing blocks that change. `allows_public_repositories` is a checkbox in a
settings page nobody visits, it leaves no trace anywhere else, and this
organisation has no audit log — so detection is the only control available,
which is the argument drift-watch was built on in the first place.

The scanner is lifted out of the workflow and run for real against a stubbed
`gh`, so api(), the response shapes and the blind-vs-clean rule are all
exercised. Reading the YAML would not catch a scanner that looks right and
never calls the endpoint.

Run: python3 .github/scripts/test_drift_watch_runner_groups.py
"""

import io
import json
import os
import pathlib
import re
import sys
import types
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[2]
WF = ROOT / ".github" / "workflows" / "drift-watch.yml"

m = re.search(r"python3 - <<'PY'\n(.*?)\n\s*PY\n", WF.read_text(), re.S)
assert m, "could not find the scanner in drift-watch.yml"
SCANNER = "\n".join(l[10:] if l.startswith(" " * 10) else l
                    for l in m.group(1).splitlines())
CODE = compile(SCANNER, "drift-watch.yml:scanner", "exec")

REPOS = [{"name": "polaris", "visibility": "private"}]
GROUPS = [{"name": "datum-private", "allows_public_repositories": False,
           "visibility": "selected", "repos": ["polaris"]}]

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def run(groups_live, selected=("polaris",), fail_on=None, tmp_path="/tmp"):
    """Execute the real scanner with `gh` stubbed out. Returns (code, output)."""
    canned = {
        "repos/datumlabsio/polaris": {"private": True},
        "repos/datumlabsio/polaris/rulesets": [{"id": 9, "name": "protect-main"}],
        "repos/datumlabsio/polaris/rulesets/9": {"enforcement": "active",
                                                 "bypass_actors": []},
        "orgs/datumlabsio/actions/runner-groups": {"runner_groups": groups_live},
    }
    for g in groups_live:
        canned[f"orgs/datumlabsio/actions/runner-groups/{g['id']}/repositories"] = \
            {"repositories": [{"name": r} for r in selected]}

    seen = []

    class Result:
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    def fake_run(argv, **kw):
        assert argv[0] == "gh" and argv[1] == "api", argv
        path = argv[2]
        seen.append(path)
        if fail_on and fail_on in path:
            return Result(1, err="boom")
        if path not in canned:
            return Result(1, err=f"unexpected path {path}")
        return Result(0, out=json.dumps(canned[path]))

    watched = pathlib.Path(tmp_path) / "drift-watch-test-watched.json"
    watched.write_text(json.dumps({"repos": REPOS, "runner_groups": GROUPS}))
    out_file = pathlib.Path(tmp_path) / "drift-watch-test-output.txt"
    out_file.write_text("")

    real_sub = sys.modules.get("subprocess")
    sys.modules["subprocess"] = types.SimpleNamespace(run=fake_run)
    os.environ.update(OWNER="datumlabsio", WATCHED=str(watched),
                      GITHUB_OUTPUT=str(out_file))
    buf = io.StringIO()
    code = 0
    try:
        with redirect_stdout(buf):
            exec(CODE, {"__name__": "__main__"})
    except SystemExit as e:
        code = e.code or 0
    finally:
        sys.modules["subprocess"] = real_sub

    check(seen, "the scanner made no API calls at all")
    return code, buf.getvalue() + out_file.read_text()


DP = {"id": 3, "name": "datum-private", "allows_public_repositories": False,
      "visibility": "selected"}

code, out = run([dict(DP)])
check(code == 0 and "match what was decided" in out,
      f"a healthy organisation does not report clean: {out[-200:]!r}")

# The one that matters.
code, out = run([dict(DP, allows_public_repositories=True)])
check("allows PUBLIC" in out,
      "a runner group opened to public repositories was not reported")

code, out = run([dict(DP, visibility="all")])
check("visible to all" in out, "a group widened to every repository was missed")

code, out = run([dict(DP)], selected=("polaris", "dl-assessment-platform"))
check("dl-assessment-platform" in out,
      "a repository added to the group was not reported")

code, out = run([])
check("is gone" in out, "a deleted runner group was not reported")

code, out = run([dict(DP), {"id": 7, "name": "shadow", "visibility": "all",
                            "allows_public_repositories": True}])
check("Nobody decided it" in out,
      "an undeclared group is a second, unwatched path onto the hardware")

# Blind is not clean — the rule the repository half already follows.
code, out = run([dict(DP)], fail_on="runner-groups")
check(code == 1 and "Could not read" in out,
      f"a failed runner-group read did not stop a clean report: {out[-200:]!r}")

# The same rule one level down: failing to read WHICH repositories a group
# grants is not "the group grants nothing".
code, out = run([dict(DP)], fail_on="/repositories")
check(code == 1 and "Could not read" in out,
      f"a failed read of a group's repository list reported clean: {out[-200:]!r}")

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    sys.exit(1)
print("PASS  8 runner-group drift cases, run against the real scanner")
