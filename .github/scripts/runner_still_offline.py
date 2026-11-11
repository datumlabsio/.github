#!/usr/bin/env python3
"""Decide whether runner-still-offline.yml says it again, and what it says.

runner-watch posts once, when the self-hosted runners go and CI moves to
GitHub-hosted. On 2 November 2026 that one message said the switch back
"returns by itself". It did not. Nothing more was said for eight days, while
every job ran on paid minutes, and the bill is what noticed. This is the
follow-up that message never had.

Input, from the environment:
  OFFLINE  DATUM_RUNNER_OFFLINE as the vars context reads it.
  SINCE    when that variable last changed, as the API reports it
           (2026-11-02T22:32:33Z). Empty when it could not be read.
  NOW      the same format. Tests only; defaults to the clock.

Output, to $GITHUB_OUTPUT: send, and when send is true, summary and detail.

The rule that matters: not knowing since when is a reason to say less, never a
reason to say nothing. An unreadable, malformed or future SINCE still sends.
There are two quiet cases and only two: the runners are up, or they went down
less than QUIET_FOR ago -- runner-watch has said so already, and repeating it
an hour later is how a channel gets muted.
"""

import datetime as dt
import os
import re
import sys

QUIET_FOR = dt.timedelta(hours=12)
SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

CHECKS = ("Is the VM on? On it, `df -h /` and "
          "`cat /opt/actions-runner-*/_diag/not-ready` say why the runners "
          "are waiting. This repeats every day until they are back.")


def parse(value):
    """A timestamp in exactly the API's format, or None. Never raises."""
    value = (value or "").strip()
    if not SHAPE.fullmatch(value):
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc)
    except ValueError:  # 2026-13-45T99:00:00Z has the right shape
        return None


def how_long(age):
    hours = int(age.total_seconds() // 3600)
    return f"{hours} hours" if hours < 48 else f"{hours // 24} days"


def decide(offline, since_raw, now):
    """Return (outputs, a line for the log)."""
    if offline != "true":
        return {"send": "false"}, (
            "DATUM_RUNNER_OFFLINE is not 'true': the runners are up. "
            "Nothing to say.")

    since = parse(since_raw)
    if since is not None and since > now:
        since = None  # a start in the future is not a start

    if since is None:
        return {
            "send": "true",
            "summary": ("The self-hosted runners are still offline, and CI "
                        "is still on paid minutes"),
            "detail": f"When they went down was not recorded. {CHECKS}",
        }, "Offline since an unknown time. Sending."

    age = now - since
    if age < QUIET_FOR:
        return {"send": "false"}, (
            f"Offline for {how_long(age)}, under "
            f"{int(QUIET_FOR.total_seconds() // 3600)} hours -- runner-watch "
            "has said so already. Not repeating it yet.")

    return {
        "send": "true",
        "summary": (f"The self-hosted runners have been offline for "
                    f"{how_long(age)}, and CI is still on paid minutes"),
        "detail": (f"Down since {since.day} {since:%b %H:%M} UTC. {CHECKS}"),
    }, f"Offline for {how_long(age)}. Sending."


def main():
    now = parse(os.environ.get("NOW")) or dt.datetime.now(dt.timezone.utc)
    outputs, log = decide(os.environ.get("OFFLINE", ""),
                          os.environ.get("SINCE", ""), now)
    print(log)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        for key, value in outputs.items():
            # Every value is built here from fixed text and a parsed date, so a
            # newline would be a bug -- and a newline in $GITHUB_OUTPUT is how
            # one output forges another. Refuse rather than write it.
            if "\n" in value:
                sys.exit(f"::error::output {key} contains a newline")
            fh.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
