#!/usr/bin/env python3
"""runner-watch decides, on a schedule, whether every repository's CI runs on
our own hardware or on GitHub's. Four ways that goes wrong, and all four are
silent:

  * it flips on a failed read, and a timed-out API call moves the whole
    organisation onto metered minutes;
  * it takes the verdict from the repository_dispatch payload, and anything
    that can reach a public dispatch endpoint gets the same power;
  * it alerts on recovery as well as on failure, and the channel whose
    acceptance criterion is silence stops being read;
  * it uses datum-runner, whose private key sits on the VM, to write the
    variable that every repository trusts.

Run: python3 .github/scripts/test_runner_watch.py
"""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

WF = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "runner-watch.yml"
DOC = yaml.safe_load(WF.read_text())
TEXT = WF.read_text()
WATCH = DOC["jobs"]["watch"]
STEPS = {s.get("id") or s["name"]: s for s in WATCH["steps"]}

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# --- the dispatch asks, it does not tell -----------------------------------
triggers = (DOC.get(True) or DOC.get("on"))
check("repository_dispatch" in triggers,
      "the heartbeat cannot shorten the detection lag without a dispatch trigger")
check("client_payload" not in TEXT,
      "the workflow reads the dispatch payload — a public endpoint would then "
      "be able to assert the runner is dead and move every repo off it")

# --- the probe runs under a token that can only look ------------------------
probe_token = STEPS["token"]["with"]
check(probe_token.get("permission-organization-self-hosted-runners") == "read",
      "the probe token is not downscoped to reading runners")
check(not any(k.endswith("write") or v == "write"
              for k, v in probe_token.items() if isinstance(v, str)),
      "the probe token asks for a write permission")

# --- the broad token exists only on the runs that write ---------------------
write_token = STEPS["write-token"]
check("permission-" not in yaml.safe_dump(write_token["with"]),
      "the write token claims to be downscoped; create-github-app-token has no "
      "input for organisation variables, so that claim would be a fiction")
check(write_token.get("if", "").strip() != "",
      "the broad token is minted on every run, including the ones that change "
      "nothing")
for sid in ("write-token", "flip"):
    check("flip-to" in STEPS[sid].get("if", ""),
          f"step {sid} is not guarded by the decision")

# --- datum-runner's key never touches this ----------------------------------
check("DATUM_RUNNER_APP" not in TEXT and "DATUM_RUNNER_PRIVATE" not in TEXT,
      "the workflow references datum-runner, whose key lives on the VM")

# --- alerting: on failure, and only on failure ------------------------------
tell = DOC["jobs"]["tell-somebody"]
check(tell["needs"] == "watch", "the alert does not wait for the decision")
check(tell["if"].strip() == "needs.watch.outputs.went-offline == 'true'",
      f"the alert fires on {tell['if']!r} — recovery must not reach the channel")
check(tell["with"]["severity"] == "warn",
      "severity is not warn")
flip_run = STEPS["flip"]["run"]
before, _, after = flip_run.partition('if [ "$OFFLINE" = true ]')
check("went-offline=true" in after.split("else")[0],
      "the offline branch does not set the output the alert keys off")
check("went-offline" not in after.split("else", 1)[1],
      "the recovery branch sets went-offline — the channel would carry good news")

# --- the decision logic, exercised rather than read -------------------------
SCRIPT = r"""
set -euo pipefail
probe() { [ "$PROBE" = "up" ] || { [ "$PROBE" = "flaky" ] && [ -f "$SEEN" ]; }; }
if probe; then offline=false
else
  touch "$SEEN"
  if probe; then offline=false; else offline=true; fi
fi
current="${CURRENT:-false}"
if [ "$offline" = "$current" ]; then echo "nochange"; exit 0; fi
echo "flip-to=$offline"
"""

CASES = [
    # probe,   variable, expected
    ("up", "", "nochange"),             # first run ever, runner healthy
    ("up", "false", "nochange"),
    ("up", "true", "flip-to=false"),    # recovery
    ("down", "", "flip-to=true"),
    ("down", "false", "flip-to=true"),
    ("down", "true", "nochange"),       # already failed over, stay quiet
    ("flaky", "false", "nochange"),     # a restart is not an outage
    ("flaky", "true", "flip-to=false"), # ...and it counts as recovered
]

with tempfile.TemporaryDirectory() as tmp:
    for probe, current, want in CASES:
        seen = pathlib.Path(tmp) / f"{probe}-{current}"
        got = subprocess.run(
            ["bash", "-c", SCRIPT],
            env={"PROBE": probe, "CURRENT": current, "SEEN": str(seen),
                 "PATH": "/usr/bin:/bin"},
            capture_output=True, text=True).stdout.strip()
        check(got == want,
              f"probe={probe} variable={current!r}: got {got!r}, want {want!r}")

# The model above is only worth anything if it matches the real script.
real = STEPS["check"]["run"]
check('current="${CURRENT:-false}"' in real,
      "an unset variable is no longer read as 'the runner is up'")
check('if [ "$offline" = "$current" ]' in real,
      "the no-change comparison changed shape; the model above is now fiction")
check(re.search(r"sleep 60\s*\n\s*if probe", real) is not None,
      "the second probe is gone — one blip would declare an outage")
check(real.count("exit 1") >= 1 and "Refusing to decide" in real,
      "a failed read no longer stops the job before it decides")
check("flip-to=$offline" in real, "the decision output changed name")


# --- the flags actually exist ---------------------------------------------
# `gh variable set --value` shipped. It is not a flag; the flag is --body. The
# shape tests above all passed, and the run was green, because the write step
# skips whenever nothing needs changing — so the one command that matters had
# never executed. Ask the real binary instead of reading the line again.
#
# Deliberately not skippable. "gh is not installed, assume it is fine" is the
# same shrug that let --value through.
if shutil.which("gh") is None:
    failures.append("gh is not installed, so the flags in this workflow are "
                    "unverified — this check does not get to pass by default")
else:
    runs = "\n".join(s["run"] for s in WATCH["steps"] if "run" in s)
    runs = runs.replace("\\\n", " ")          # join shell continuations
    seen = set()
    for m in re.finditer(r"\bgh((?:\s+[a-z][a-z0-9-]*)+)([^\n|)&;]*)", runs):
        sub = m.group(1).split()
        flags = set(re.findall(r"--[a-z][a-z0-9-]*", m.group(2)))
        # Trailing words that are arguments, not subcommands, stop the chain.
        while sub and sub[-1] not in {"api", "set", "list", "view", "delete"}:
            sub.pop()
        if not sub or not flags:
            continue
        key = (tuple(sub), frozenset(flags))
        if key in seen:
            continue
        seen.add(key)
        help_text = subprocess.run(["gh", *sub, "--help"],
                                   capture_output=True, text=True).stdout
        known = set(re.findall(r"--[a-z][a-z0-9-]*", help_text))
        for flag in sorted(flags - known):
            failures.append(f"`gh {' '.join(sub)}` has no {flag} flag")
    check(seen, "no gh invocation was found to check — the parser broke, and a "
                "parser that finds nothing reports success")

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    sys.exit(1)
print(f"PASS  dispatch cannot assert, a failed read cannot flip, "
      f"{len(CASES)} decision cases hold")
