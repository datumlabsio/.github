#!/usr/bin/env python3
"""runner-still-offline repeats a runner outage once a day until it ends. The
outage it exists for was silent, so the ways this can go wrong that matter are
the ones that make it silent again:

  * a missing, malformed or future start time stops the message, instead of
    making it say less;
  * a token that will not mint, or a read that fails, fails the job before the
    message is decided;
  * it fires while the runners are up, and the channel whose acceptance
    criterion is silence learns to be ignored;
  * it repeats runner-watch within the hour, which is the same lesson faster.

Run: python3 .github/scripts/test_runner_still_offline.py
"""

import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "runner_still_offline.py"
WF = ROOT / ".github" / "workflows" / "runner-still-offline.yml"
WATCH = ROOT / ".github" / "workflows" / "runner-watch.yml"
DOC = yaml.safe_load(WF.read_text())
RUNBOOK = "self-hosted-runners.md#if-it-is-on-fire"

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def outputs_of(path):
    """Parse $GITHUB_OUTPUT strictly: every line key=value, no key twice."""
    seen = {}
    for line in pathlib.Path(path).read_text().splitlines():
        key, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[a-z]+", key):
            failures.append(f"malformed output line {line!r}")
            continue
        if key in seen:
            failures.append(f"output {key} written twice -- one forged the other")
        seen[key] = value
    return seen


# --- the decision, exercised ------------------------------------------------
NOW = "2026-11-10T04:17:00Z"

# offline, since, expected send, text the summary or detail must carry
CASES = [
    ("true", "2026-11-02T22:32:33Z", "true", ["7 days", "Down since 2 Nov 22:32 UTC"]),
    ("true", "2026-11-09T15:00:00Z", "true", ["13 hours"]),
    ("true", "2026-11-08T05:00:00Z", "true", ["47 hours"]),
    ("true", "2026-11-08T04:17:00Z", "true", ["2 days"]),
    ("true", "2026-11-09T16:17:00Z", "true", ["12 hours"]),   # exactly the window
    ("true", "2026-11-09T16:17:01Z", "false", []),            # a second inside it
    ("true", "2026-11-10T03:00:00Z", "false", []),            # runner-watch just said it
    ("true", "", "true", ["not recorded"]),                   # the read failed
    ("true", "yesterday", "true", ["not recorded"]),
    ("true", "2026-13-45T99:00:00Z", "true", ["not recorded"]),
    ("true", "2026-11-11T00:00:00Z", "true", ["not recorded"]),  # from the future
    ("true", "2026-11-02T22:32:33Z\nsend=false", "true", ["not recorded"]),
    ("false", "2026-11-02T22:32:33Z", "false", []),           # dispatched, runners up
    ("", "", "false", []),
]

with tempfile.TemporaryDirectory() as tmp:
    for n, (offline, since, want, carries) in enumerate(CASES):
        out = pathlib.Path(tmp) / f"out-{n}"
        out.touch()
        run = subprocess.run(
            [sys.executable, str(SCRIPT)],
            env={"OFFLINE": offline, "SINCE": since, "NOW": NOW,
                 "GITHUB_OUTPUT": str(out), "PATH": os.environ["PATH"]},
            capture_output=True, text=True)
        label = f"OFFLINE={offline!r} SINCE={since!r}"
        check(run.returncode == 0, f"{label}: exited {run.returncode}: {run.stderr}")
        got = outputs_of(out)
        check(got.get("send") == want,
              f"{label}: send={got.get('send')!r}, want {want!r}")
        if want == "true":
            text = got.get("summary", "") + " " + got.get("detail", "")
            check(got.get("summary") and got.get("detail"),
                  f"{label}: sends with an empty summary or detail")
            for piece in carries:
                check(piece in text, f"{label}: message does not say {piece!r}: {text!r}")
            # What a person does first. Without it the message is a complaint.
            for step in ("df -h /", "_diag/not-ready"):
                check(step in text, f"{label}: message drops the check {step!r}")
            check("yesterday" not in text and "99:00" not in text,
                  f"{label}: the raw value reached the message")
        else:
            check(set(got) == {"send"},
                  f"{label}: quiet, but still wrote {sorted(set(got) - {'send'})}")


# --- the workflow around it -------------------------------------------------
triggers = DOC.get(True) or DOC.get("on")
crons = [s["cron"] for s in triggers.get("schedule", [])]
check(len(crons) == 1, f"expected one daily schedule, found {crons}")
check(all(c.split()[0] not in {"0", "*"} for c in crons),
      "the schedule runs on the hour, when GitHub delays and drops the most")
check("workflow_dispatch" in triggers,
      "no dispatch, so the token and the read cannot be proven for real")
check(DOC.get("permissions") == {}, "the workflow grants permissions by default")

job = DOC["jobs"]["how-long"]
check("vars.DATUM_RUNNER_OFFLINE == 'true'" in job["if"],
      "the scheduled run is not gated on the failover being on")
steps = {s.get("id") or s["name"]: s for s in job["steps"]}

token = steps["token"]
check(token.get("continue-on-error") is True,
      "a token that will not mint fails the job, and the reminder with it")
check("permission-" not in yaml.safe_dump(token["with"]),
      "the token claims to be narrowed; create-github-app-token cannot narrow "
      "to organisation variables, so that claim would be a fiction")

since = steps["since"]
check(since.get("if", "").strip() == "steps.token.outcome == 'success'",
      "the read is not skipped when the token did not mint")
check("GH_TOKEN" in since.get("env", {}), "the read has no token")

decide = steps["decide"]
check("GH_TOKEN" not in decide.get("env", {}),
      "the broad token reaches the decision -- keep it to the one fixed read")
check(decide["env"].get("OFFLINE") == "${{ vars.DATUM_RUNNER_OFFLINE }}",
      "the decision does not see the variable, so a dispatch would send while up")
check(decide["env"].get("SINCE") == "${{ steps.since.outputs.at }}",
      "the decision does not get the read")
check(str(SCRIPT.relative_to(ROOT)) in decide["run"],
      "the decision step does not run the script this file tests")
for key in ("send", "summary", "detail"):
    check(job["outputs"].get(key) == "${{ steps.decide.outputs.%s }}" % key,
          f"job output {key} is not the decision's")

tell = DOC["jobs"]["tell-somebody"]
check(tell["needs"] == "how-long", "the alert does not wait for the decision")
check(tell["if"].strip() == "needs.how-long.outputs.send == 'true'",
      f"the alert fires on {tell['if']!r}")
check(tell["uses"].startswith("datumlabsio/actions/.github/workflows/notify.yml@"),
      "the alert does not go through notify.yml")
check(tell["with"]["severity"] == "critical",
      "a reminder is sent at warn -- the outage it repeats did not end in the hour")
check(tell["secrets"]["webhook"] == "${{ secrets.SLACK_ALERTS_WEBHOOK }}",
      "the alert is not given the webhook runner-watch uses")
check(tell["with"]["summary"] == "${{ needs.how-long.outputs.summary }}"
      and tell["with"]["detail"] == "${{ needs.how-long.outputs.detail }}",
      "the alert does not carry the decision's words")
check(tell["with"]["url"].endswith(RUNBOOK),
      "the alert does not link the runbook's checklist")
check(RUNBOOK in WATCH.read_text(),
      "runner-watch's first message does not link the same checklist")


# --- the read, exercised: a failure must not fail the job -------------------
READ = since["run"]
GH = """#!/bin/sh
printf '%s\\n' "$*" >> "$CALLS"
if [ "$MODE" = ok ]; then echo 2026-11-02T22:32:33Z; exit 0; fi
echo "HTTP 403: Resource not accessible by integration" >&2
exit 1
"""

with tempfile.TemporaryDirectory() as tmp:
    bindir = pathlib.Path(tmp) / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(GH)
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    for mode, flags in (("ok", "-e"), ("fail", "-e"), ("fail", "-eo pipefail")):
        out = pathlib.Path(tmp) / f"out-{mode}{flags.replace(' ', '')}"
        calls = pathlib.Path(tmp) / f"calls-{mode}{flags.replace(' ', '')}"
        out.touch()
        run = subprocess.run(
            ["bash", *flags.split(), "-c", READ],
            env={"MODE": mode, "CALLS": str(calls), "OWNER": "acme",
                 "GITHUB_OUTPUT": str(out),
                 "PATH": f"{bindir}:/usr/bin:/bin"},
            capture_output=True, text=True)
        label = f"read with gh {mode} under bash {flags}"
        check(run.returncode == 0,
              f"{label}: exited {run.returncode} -- the job stops and nobody is told")
        got = outputs_of(out)
        if mode == "ok":
            check(got == {"at": "2026-11-02T22:32:33Z"}, f"{label}: wrote {got}")
        else:
            check(got == {}, f"{label}: wrote {got} from a failed read")
            check("::warning::" in run.stdout, f"{label}: the failure is not said")
        called = calls.read_text() if calls.exists() else ""
        check("api /orgs/acme/actions/variables/DATUM_RUNNER_OFFLINE" in called,
              f"{label}: did not ask for the variable: {called!r}")


# --- the flags actually exist -----------------------------------------------
# Same rule as runner-watch: ask the real binary, never the line again, and do
# not pass by default when there is no binary to ask.
if shutil.which("gh") is None:
    failures.append("gh is not installed, so the flags in this workflow are "
                    "unverified -- this check does not get to pass by default")
else:
    seen = set()
    for m in re.finditer(r"\bgh((?:\s+[a-z][a-z0-9-]*)+)([^\n|)&;]*)", READ):
        sub = m.group(1).split()
        flags = set(re.findall(r"--[a-z][a-z0-9-]*", m.group(2)))
        if not sub or not flags:
            continue
        seen.add(tuple(sub))
        help_text = subprocess.run(["gh", *sub, "--help"],
                                   capture_output=True, text=True).stdout
        for flag in sorted(flags - set(re.findall(r"--[a-z][a-z0-9-]*", help_text))):
            failures.append(f"`gh {' '.join(sub)}` has no {flag} flag")
    check(seen, "no gh invocation was found to check -- the parser broke")

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    sys.exit(1)
print(f"PASS  {len(CASES)} decision cases hold, a failed read still sends, "
      f"the runners being up sends nothing")
