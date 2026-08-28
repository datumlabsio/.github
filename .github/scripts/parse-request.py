#!/usr/bin/env python3
"""Turn a rendered issue-form body back into copier answers.

The label -> field-id map is read from the form definitions rather than
duplicated here. Rename a label in a form and this follows; add a field and this
picks it up. A second copy would drift, and the drift would be silent — the
request would render with a default nobody chose.

There is more than one form. GitHub Issue Forms have no conditional logic, so a
single form showed every requester every field: someone asking for a `docs`
repository was asked which front-end framework they wanted. The forms are split
by shape instead, and this reads whichever one was used.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TEMPLATES = Path(".github/ISSUE_TEMPLATE")

# The contract between a form and this script is the LABEL, never the filename.
# Forms are found by the label they apply to the issue, which is also what the
# workflow triggers on.
TRIGGER_LABEL = "repo-request"

# GitHub renders an unanswered optional field as this exact string.
BLANK = "_No response_"

# The one place a display string has to be mapped by hand. `framework` is folded
# into the kind/parts choice so nobody is asked about a front end they are not
# building. Keep in step with `framework` in scaffolds/copier.yml.
FRAMEWORK_OF = {
    "web-app (Next.js)": ("web-app", "next"),
    "web-app (React + Vite)": ("web-app", "react-vite"),
}


def forms() -> dict[Path, dict[str, str]]:
    """{form path: {label: field id}} for every form carrying the trigger label."""
    import yaml

    out: dict[Path, dict[str, str]] = {}
    for path in sorted(TEMPLATES.glob("*.yml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            print(f"::error::{path} is not valid YAML: {exc}")
            raise SystemExit(1) from exc
        if not isinstance(doc, dict) or TRIGGER_LABEL not in (doc.get("labels") or []):
            continue
        fields = {}
        for block in doc.get("body", []):
            fid = block.get("id")
            label = (block.get("attributes") or {}).get("label")
            if fid and label:
                fields[label.strip()] = fid
        out[path] = fields
    return out


def check_no_collisions(defs: dict[Path, dict[str, str]]) -> None:
    """The same label must mean the same field on every form.

    Sharing a label is normal and intended — `Repository name` is on both. What
    is not survivable is one label mapping to two different ids: the merged map
    would take whichever form was read last and quietly write an answer into the
    wrong field.
    """
    seen: dict[str, tuple[Path, str]] = {}
    for path, fields in defs.items():
        for label, fid in fields.items():
            if label in seen and seen[label][1] != fid:
                other, other_fid = seen[label]
                print(
                    f"::error::'{label}' maps to '{other_fid}' in {other.name} but "
                    f"'{fid}' in {path.name}. One label must mean one field."
                )
                raise SystemExit(1)
            seen.setdefault(label, (path, fid))


def headings(body: str) -> list[str]:
    return [h.strip() for h in re.findall(r"^###\s+(.+?)\s*$", body, flags=re.M)]


def which_form(body: str, defs: dict[Path, dict[str, str]]) -> Path:
    """Identify the form from the headings the body actually carries.

    GitHub renders `### <label>` for EVERY field, answered or not — an untouched
    optional field still appears, with `_No response_` under it. So the set of
    headings identifies the form on its own.

    Deliberately not a marker checkbox: the requester can leave a checkbox
    unticked, and an unticked checkbox is the exact shape that has already
    caused one bug here. Nothing about this asks the requester to do anything.
    """
    present = set(headings(body))
    scores = {}
    for path, fields in defs.items():
        others = set().union(*(set(f) for p, f in defs.items() if p != path)) if len(defs) > 1 else set()
        exclusive = set(fields) - others
        scores[path] = len(exclusive & present)

    matched = [p for p, n in scores.items() if n > 0]
    if len(matched) == 1:
        return matched[0]
    if not matched:
        print(
            "::error::This issue does not match any repository-request form. "
            f"Forms checked: {', '.join(sorted(p.name for p in defs))}."
        )
    else:
        print(
            "::error::This issue matches more than one form "
            f"({', '.join(sorted(p.name for p in matched))}), so the answers are ambiguous."
        )
    raise SystemExit(1)


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
        # block by shape — the `[ ]` as well as the `[x]` — not by whether it
        # produced any answers. Match only `[xX]` here and an empty selection is
        # stored as the raw "- [ ] gitops" markdown and reads as a real value
        # downstream. That was a real bug, found by a control case.
        if re.search(r"^-\s*\[[ xX]\]\s", value, flags=re.M):
            found[fid] = re.findall(r"^-\s*\[[xX]\]\s*(.+?)\s*$", value, flags=re.M)
            continue
        # Dropdowns render the whole option line; the machine-readable part is
        # everything before the em dash we use to explain it.
        found[fid] = value.split(" — ")[0].strip()
    return found


def unfold_framework(a: dict[str, object]) -> None:
    """`web-app (Next.js)` is one choice to a requester and two to copier."""
    kind = a.get("archetype")
    if isinstance(kind, str) and kind in FRAMEWORK_OF:
        a["archetype"], a["framework"] = FRAMEWORK_OF[kind]

    folders = a.get("folders")
    if isinstance(folders, list):
        picked = [f for f in folders if f in FRAMEWORK_OF]
        if len(picked) > 1:
            print(
                "::error::Both web-app rows are ticked. There is one `web-app/` folder "
                "and it is built either with Next.js or with React + Vite, not both. "
                "Tick one."
            )
            raise SystemExit(1)
        if picked:
            base, framework = FRAMEWORK_OF[picked[0]]
            a["folders"] = [base if f == picked[0] else f for f in folders]
            a["framework"] = framework


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        print("::error::The issue body is empty. Nothing to render from.")
        return 1

    defs = forms()
    if not defs:
        print(f"::error::No form under {TEMPLATES} carries the '{TRIGGER_LABEL}' label.")
        return 1
    check_no_collisions(defs)

    form = which_form(body, defs)
    print(f"form: {form.name}", file=sys.stderr)
    a = answers(body, defs[form])

    # A form with no `archetype` field IS the monorepo form. Derived from the
    # form definition rather than from its filename, so renaming the file cannot
    # silently change what gets rendered.
    if "archetype" not in defs[form].values():
        a["archetype"] = "monorepo"

    unfold_framework(a)

    # `has_proposals` is a bool to copier and a one-option checkbox to a person.
    if "has_proposals" in a:
        a["has_proposals"] = bool(a["has_proposals"])

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
            print("::error::No parts were ticked. A monorepo with no components is an empty repository.")
            return 1
    else:
        a.pop("folders", None)

    # Everything else is passed through as answered. copier's `when:` decides
    # what it actually asks, and it silently drops data for a question it did
    # not ask — verified against v0.11.1. Re-deriving those conditions here
    # would be a second copy of a rule that already exists in copier.yml.
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
            if isinstance(value, list):
                out = json.dumps(value)
            elif isinstance(value, bool):
                out = "true" if value else "false"
            else:
                out = value
            fh.write(f"{key}={out}\n")
    print(f"wrote {args}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
