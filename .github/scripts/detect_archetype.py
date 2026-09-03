#!/usr/bin/env python3
"""Read a repository's archetype off the files it already has.

    python3 detect_archetype.py <checkout-dir>   -> prints one archetype

Copier cannot do this itself. Its Jinja context exposes the destination as a
`PurePosixPath` with no filesystem access; `_external_data` parses whatever it
reads as YAML and dies on a `pyproject.toml`; and a Jinja extension has to be
pip-installed alongside copier rather than shipped in the template. All three
were tried. A shell step before copier has none of those problems, which is why
adoption belongs in a workflow rather than on somebody's laptop.

Wrong here is cheap and visible: it lands the wrong linter config in a pull
request nobody has merged yet. Silent is the expensive failure, so an ambiguous
repository says so rather than guessing.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ordered: the first match wins only when nothing else matches too. Several
# matches mean monorepo, which is a real answer rather than a tie-break.
MARKERS = {
    "application": ("pyproject.toml", "setup.py", "requirements.txt"),
    "web-app": ("package.json",),
    "dbt-project": ("dbt_project.yml",),
    "gitops": ("kustomization.yaml", "kustomization.yml"),
}


# Directories that are never a component, so a marker inside one means nothing.
IGNORE = {
    ".git", ".github", "node_modules", "venv", ".venv", "dist", "build",
    "target", "vendor", "__pycache__", ".terraform", "site-packages",
}


def markers_in(d: Path) -> list[tuple[str, str]]:
    return [
        (archetype, f)
        for archetype, files in MARKERS.items()
        for f in files
        if (d / f).exists()
    ]


def detect(root: Path) -> tuple[str, str]:
    """Return (archetype, why).

    Looks at the root AND one level down. A monorepo carries its markers in
    subdirectories -- polaris has none at the root at all, and a root-only scan
    called it `generic`, which would have landed Python linters on a repository
    that is mostly dbt and Kubernetes.
    """
    at_root = markers_in(root)
    if at_root:
        kinds = {a for a, _ in at_root}
        why = "; ".join(f"{a} ({f})" for a, f in at_root)
        if len(kinds) > 1:
            return "monorepo", "several markers at the root: " + why
        return at_root[0][0], why

    # Nothing at the root. A monorepo puts each component in its own folder.
    per_dir: dict[str, set[str]] = {}
    for sub in sorted(p for p in root.iterdir() if p.is_dir()):
        if sub.name in IGNORE or sub.name.startswith("."):
            continue
        found = markers_in(sub)
        if found:
            per_dir[sub.name] = {a for a, _ in found}

    if not per_dir:
        return "generic", "no recognised marker file at the root or one level down"

    kinds = set().union(*per_dir.values())
    where = "; ".join(f"{d}/ -> {', '.join(sorted(k))}" for d, k in sorted(per_dir.items()))
    if len(per_dir) > 1 or len(kinds) > 1:
        return "monorepo", "markers in subdirectories: " + where
    return next(iter(kinds)), "markers in subdirectories: " + where


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: detect_archetype.py <checkout-dir>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"::error::{root} is not a directory", file=sys.stderr)
        return 1
    archetype, why = detect(root)
    print(archetype)
    print(f"::notice::Detected archetype '{archetype}' — {why}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
