#!/usr/bin/env python3
"""What adoption could not do for this repository, computed from the repository.

    python3 adoption_warnings.py <checkout-dir> [--package-hint ecap]

Boilerplate warnings get skimmed. These are only emitted when the condition is
actually true in the repository being adopted, so every line in the pull request
is a thing that is really wrong there and nowhere else.

Each finding is something a machine can DETECT but should not FIX -- deleting
somebody's existing workflow, or guessing which package their coverage should
point at, is not adoption's business. Anything that can be fixed automatically
should be, and is not in here.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ACTIONS_CALL = re.compile(
    r"datumlabsio/actions/\.github/workflows/([\w-]+)\.yml@([\w.\-]+)")


def existing_gate_callers(root: Path) -> list[tuple[str, str, str]]:
    """Workflows already calling our reusable workflows -- (file, workflow, ref).

    The retrofit only ever adds, so a repository that already adopted something
    by hand keeps it, and then runs the same scan twice at two different
    versions. ember carries datum-police.yml at v0.27.0 and would also get ci.yml.
    """
    out = []
    wf = root / ".github/workflows"
    if not wf.is_dir():
        return out
    for f in sorted(wf.glob("*.y*ml")):
        if f.name in {"ci.yml", "main-watch.yml", "release.yml", "scaffold-update.yml"}:
            continue  # the ones adoption just added
        for m in ACTIONS_CALL.finditer(f.read_text(encoding="utf-8", errors="replace")):
            out.append((f.name, m.group(1), m.group(2)))
    return out


def coverage_points_nowhere(root: Path) -> str | None:
    """`[tool.coverage.run] source` naming a directory that does not exist.

    pyproject.toml is _skip_if_exists, so a retrofitted repository keeps its own
    -- and the template's coverage config, which assumes a src/ layout, was never
    applied. Whatever is in theirs is what runs.
    """
    pp = root / "pyproject.toml"
    if not pp.is_file():
        return None
    text = pp.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\[tool\.coverage\.run\](.*?)(?=\n\[|\Z)", text, re.S)
    if not m:
        return "pyproject.toml has no [tool.coverage.run] at all"
    src = re.search(r"source\s*=\s*\[([^\]]*)\]", m.group(1))
    if not src:
        return None
    named = [s.strip().strip("\"'") for s in src.group(1).split(",") if s.strip()]
    missing = [d for d in named if not (root / d).exists()]
    return f"coverage points at {', '.join(missing)}, which does not exist" if missing else None


def python_packages(root: Path) -> list[str]:
    """Top-level directories that look like a Python package."""
    return sorted(
        p.name for p in root.iterdir()
        if p.is_dir() and not p.name.startswith((".", "_"))
        and (p / "__init__.py").exists()
    )


def warnings_for(root: Path) -> list[str]:
    out: list[str] = []

    dupes = existing_gate_callers(root)
    if dupes:
        lines = "\n".join(
            f"  - `{f}` calls `{w}@{ref}`" for f, w, ref in dupes)
        out.append(
            "**You already call our workflows, and this pull request adds "
            f"`ci.yml` which calls them too.**\n\n{lines}\n\n"
            "Delete the old file, or the same scans run twice on every pull "
            "request — at two different versions, reporting two different things.")

    cov = coverage_points_nowhere(root)
    if cov:
        pkgs = python_packages(root)
        hint = f" Yours look like: {', '.join(f'`{p}`' for p in pkgs)}." if pkgs else ""
        out.append(
            f"**Coverage is not measuring your code** — {cov}.{hint}\n\n"
            "`pyproject.toml` was left as yours, so the template's coverage "
            "config was never applied. Fix it before switching the coverage "
            "gate on, or it reports a number about nothing.")

    if not (root / "CLAUDE.md").is_file():
        out.append(
            "**`CLAUDE.md` is a skeleton.** It is prose about *this* codebase and "
            "nothing can generate it — what the repository is, how to run it, and "
            "the two or three things that are not obvious from reading the code.")

    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: adoption_warnings.py <checkout-dir>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"::error::{root} is not a directory", file=sys.stderr)
        return 1
    found = warnings_for(root)
    if not found:
        return 0
    print("## Needs a human\n")
    print("Everything below was found in this repository. Nothing here is "
          "boilerplate.\n")
    for w in found:
        print(f"- {w}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
