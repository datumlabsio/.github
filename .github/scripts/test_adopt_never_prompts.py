#!/usr/bin/env python3
"""The adoption run must never stop to ask about a file.

    python3 .github/scripts/test_adopt_never_prompts.py

`--defaults` answers the QUESTIONS. It does nothing about a FILE that already
exists: copier stops and asks, there is no terminal, and the run dies with

    Warning: Input is not a terminal (fd=0).

That is what happened to dl-assessment-platform on `pnpm-workspace.yaml`.

The template's `_skip_if_exists` is not the fix. It lists eleven files, chosen by
looking at one Python repository; the template can ship 38, and the first web-app
repository adopted found one of the other 27. Fixing it by extending that list
requires the list to be complete, forever, for every archetype.

`--skip '*'` is the semantics of a retrofit in one flag: never touch anything
already there. This asserts the workflow passes it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WF = Path(__file__).resolve().parent.parent / "workflows/adopt-repo.yml"
text = WF.read_text(encoding="utf-8")
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"    [{'ok' if ok else 'FAIL'}] {name}{'' if ok else f' — {detail}'}")
    if not ok:
        FAILURES.append(name)


# The copier invocation, ignoring comments.
lines = [l for l in text.split("\n") if not l.lstrip().startswith("#")]
call = "\n".join(lines)
m = re.search(r"copier copy[^\n]*(?:\\\n[^\n]*)*", call)
invocation = m.group(0) if m else ""

check("the workflow invokes copier", bool(invocation), "no `copier copy` found")
check("it passes --skip '*' so an existing file is never asked about",
      "--skip '*'" in invocation,
      "without it, any collision the template's _skip_if_exists misses kills the run")
check("it still passes --defaults for the questions",
      "--defaults" in invocation)
check("it does NOT pass --overwrite",
      "--overwrite" not in invocation and "--force" not in invocation and " -w " not in invocation,
      "overwrite would clobber the repository's own files")
check("it does not pass -f, which means --defaults --overwrite",
      not re.search(r"(?<![\w-])-f(?![\w-])", invocation))

if FAILURES:
    print(f"\nFAIL: {len(FAILURES)}: {', '.join(FAILURES)}")
    sys.exit(1)
print("\nOK: a retrofit cannot stop to ask, and cannot overwrite")
