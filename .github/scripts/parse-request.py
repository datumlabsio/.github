#!/usr/bin/env python3
"""Turn a rendered issue-form body back into copier answers.

The label -> field-id map is read from the form definition rather than
duplicated here. Rename a label in the form and this follows; add a field and
this picks it up. A second copy would drift, and the drift would be silent —
the request would render with a default nobody chose.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

FORM = Path(".github/ISSUE_TEMPLATE/new-repo.yml")

# GitHub renders an unanswered optional field as this exact string.
BLANK = "_No response_"


def field_map(form_path: Path) -> dict[str, str]:
    """label -> id, straight from the form the requester filled in."""
    import yaml

    doc = yaml.safe_load(form_path.read_text(encoding="utf-8"))
    out = {}
    for block in doc.get("body", []):
        fid = block.get("id")
        label = (block.get("attributes") or {}).get("label")
        if fid and label:
            out[label.strip()] = fid
    return out


def answers(body: str, labels: dict[str, str]) -> dict[str, object]:
    """Split the body on '### <label>' and read what follows each one."""
    parts = re.split(r"^###\s+(.+?)\s*$", body, flags=re.M)
    found: dict[str, object] = {}
    # parts[0] is anything before the first heading; then (label, value) pairs.
    for label, value in zip(parts[1::2], parts[2::2]):
        fid = labels.get(label.strip())
        if not fid:
            continue
        value = value.strip()
        if not value or value == BLANK:
            continue
        # A checkbox block with NOTHING ticked still looks like text. Detect the
        # block by shape, not by whether it produced any answers — otherwise an
        # empty selection is stored as the raw "- [ ] gitops" markdown and reads
        # as a real value downstream.
        if re.search(r"^-\s*\[[ xX]\]\s", value, flags=re.M):
            found[fid] = re.findall(r"^-\s*\[[xX]\]\s*(.+?)\s*$", value, flags=re.M)
        else:
            # Dropdowns render the whole option line; the machine-readable part
            # is everything before the em dash we use to explain it.
            found[fid] = value.split(" — ")[0].strip()
    return found


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        print("::error::The issue body is empty. Nothing to render from.")
        return 1

    if not FORM.is_file():
        print(f"::error::{FORM} not found, so the answers cannot be mapped.")
        return 1

    a = answers(body, field_map(FORM))

    required = ["repo_name", "repo_description", "owning_team", "archetype"]
    missing = [r for r in required if r not in a]
    if missing:
        print(f"::error::The request is missing: {', '.join(missing)}.")
        return 1

    name = a["repo_name"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,98}[a-z0-9]", name):
        print(f"::error::'{name}' is not a usable repository name — lowercase, digits and hyphens only.")
        return 1

    # `folders` only means anything for a monorepo, and an empty list would
    # render a repository with no components at all.
    if a.get("archetype") == "monorepo":
        if not a.get("folders"):
            print("::error::monorepo was chosen but no parts were ticked.")
            return 1
    else:
        a.pop("folders", None)

    for key, value in a.items():
        print(f"  {key} = {value!r}", file=sys.stderr)

    Path(os.environ["GITHUB_OUTPUT"]).open("a").write(
        f"repo_name={name}\n"
        f"description={a['repo_description']}\n"
        f"answers={json.dumps(a)}\n"
    )

    # The copier arguments are written here rather than assembled in the
    # workflow. Multi-line shell inside a YAML block scalar is where this broke
    # once already, and a list answer has to be JSON-encoded for copier to read
    # it as a list rather than a string.
    args = Path(os.environ["RUNNER_TEMP"]) / "copier-args"
    with args.open("w", encoding="utf-8") as fh:
        for key, value in a.items():
            fh.write(f"{key}={json.dumps(value) if isinstance(value, list) else value}\n")
    print(f"wrote {args}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
