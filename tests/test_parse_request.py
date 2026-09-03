#!/usr/bin/env python3
"""Offline tests for parse-request.py.

Every case here used to require a real issue, a real approval and a real
repository — ten of them, each blocking on one human. None of that tested the
parser any better than this does, and none of it could be re-run on a pull
request.

The bodies are BUILT FROM THE FORMS, the same way GitHub builds them: a
`### <label>` heading for every field, `_No response_` under an untouched
optional one, and every checkbox option listed whether ticked or not. If a form
changes, these bodies change with it, which is the point — a test carrying its
own hardcoded copy of the form would pass while the real thing broke.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/parse-request.py"
TEMPLATES = ROOT / ".github/ISSUE_TEMPLATE"

SINGLE = TEMPLATES / "new-repo.yml"
MONOREPO = TEMPLATES / "new-monorepo.yml"


def build_body(form: Path, answers: dict[str, object]) -> str:
    """Render an issue body the way GitHub renders one.

    Unanswered optional fields still get a heading — that is what makes the
    heading set identify the form, and it is why `_No response_` exists.
    """
    doc = yaml.safe_load(form.read_text(encoding="utf-8"))
    out = []
    for block in doc.get("body", []):
        fid, kind = block.get("id"), block.get("type")
        if not fid:
            continue
        label = block["attributes"]["label"]
        out.append(f"### {label}\n")
        given = answers.get(fid)
        if kind == "checkboxes":
            ticked = set(given or [])
            for opt in block["attributes"]["options"]:
                mark = "x" if opt["label"] in ticked else " "
                out.append(f"- [{mark}] {opt['label']}")
            out.append("")
        elif given is None:
            # An untouched field does NOT render the same way for every type,
            # and assuming it did is what let a real request through:
            #
            #   input     -> "_No response_"
            #   dropdown  -> "None"
            #
            # This builder previously wrote "_No response_" for both, so the
            # suite agreed with the parser and neither matched GitHub. Copied
            # from a real issue body, not from memory.
            out.append("None\n" if kind == "dropdown" else "_No response_\n")
        else:
            out.append(f"{given}\n")
    return "\n".join(out)


def run(body: str, templates: Path | None = None, label: str | None = None) -> tuple[int, dict[str, str], str]:
    """Run the parser exactly as the workflow does, in a throwaway working dir."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        out_file, runner_tmp = tmp / "gh-output", tmp / "runner"
        out_file.touch()
        runner_tmp.mkdir()

        work = tmp / "work"
        (work / ".github/scripts").mkdir(parents=True)
        (work / ".github/scripts/parse-request.py").write_text(SCRIPT.read_text())
        src = templates or TEMPLATES
        (work / ".github/ISSUE_TEMPLATE").mkdir(parents=True)
        for f in src.glob("*.yml"):
            (work / ".github/ISSUE_TEMPLATE" / f.name).write_text(f.read_text())

        proc = subprocess.run(
            [sys.executable, ".github/scripts/parse-request.py"],
            cwd=work,
            env={
                **{k: v for k, v in os.environ.items() if k != "TRIGGER_LABEL"},
                "ISSUE_BODY": body,
                "GITHUB_OUTPUT": str(out_file),
                "RUNNER_TEMP": str(runner_tmp),
                # Unset means the default, which is what repo-request relies on.
                **({"TRIGGER_LABEL": label} if label else {}),
            },
            capture_output=True,
            text=True,
        )
        args = {}
        argfile = runner_tmp / "copier-args"
        if argfile.is_file():
            for line in argfile.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    args[k] = v
        return proc.returncode, args, proc.stdout + proc.stderr


BASE = {
    "repo_name": "acme-insights",
    "repo_description": "Ingestion and models for the Acme engagement",
    "owning_team": "polaris",
}

CASES: list[tuple[str, object]] = []


def case(name):
    def wrap(fn):
        CASES.append((name, fn))
        return fn
    return wrap


# ---------------------------------------------------------------- happy paths

@case("1  web-app (Next.js) unfolds to archetype + framework")
def _():
    rc, a, log = run(build_body(SINGLE, {**BASE, "archetype": "web-app (Next.js)"}))
    assert rc == 0, log
    assert a["archetype"] == "web-app", a
    assert a["framework"] == "next", a


@case("2  web-app (React + Vite) unfolds to react-vite")
def _():
    rc, a, log = run(build_body(SINGLE, {**BASE, "archetype": "web-app (React + Vite)"}))
    assert rc == 0, log
    assert a["archetype"] == "web-app", a
    assert a["framework"] == "react-vite", a


@case("3  docs carries no framework, warehouse or source_name")
def _():
    rc, a, log = run(build_body(SINGLE, {**BASE, "archetype": "docs"}))
    assert rc == 0, log
    assert a["archetype"] == "docs", a
    for k in ("framework", "warehouse", "source_name"):
        assert k not in a, f"{k} leaked into a docs request: {a}"


@case("4  monorepo: gitops + web-app (Next.js)")
def _():
    rc, a, log = run(build_body(MONOREPO, {**BASE, "folders": ["gitops", "web-app (Next.js)"]}))
    assert rc == 0, log
    assert a["archetype"] == "monorepo", a
    assert json.loads(a["folders"]) == ["gitops", "web-app"], a
    assert a["framework"] == "next", a


@case("5  monorepo with BOTH web-app rows ticked is refused, reason named")
def _():
    rc, a, log = run(build_body(
        MONOREPO, {**BASE, "folders": ["web-app (Next.js)", "web-app (React + Vite)"]}))
    assert rc != 0, f"both variants were accepted: {a}"
    assert "one `web-app/` folder" in log, log


@case("6  monorepo with NOTHING ticked is refused  [control case]")
def _():
    rc, a, log = run(build_body(MONOREPO, {**BASE, "folders": []}))
    assert rc != 0, f"an empty monorepo was accepted: {a}"
    assert "no components" in log or "No parts" in log, log


@case("16 an untouched dropdown says the word None, and is not an answer")
def _():
    # The live forms no longer carry an OPTIONAL dropdown — every question left
    # is required — so this is exercised against a synthetic one. The guard has
    # to stay: the next optional dropdown somebody adds must not reintroduce the
    # bug that reached a real requester.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in TEMPLATES.glob("*.yml"):
            (tmp / f.name).write_text(f.read_text())
        form = yaml.safe_load((tmp / "new-repo.yml").read_text())
        form["body"].append({
            "type": "dropdown",
            "id": "warehouse",
            "attributes": {"label": "Warehouse", "options": ["clickhouse", "bigquery"]},
        })
        (tmp / "new-repo.yml").write_text(yaml.safe_dump(form, sort_keys=False))
        body = build_body(tmp / "new-repo.yml", {**BASE, "archetype": "docs"})
        assert "\nNone\n" in body, "the builder stopped rendering an untouched dropdown as None"
        rc, a, log = run(body, templates=tmp)
    assert rc == 0, log
    assert "warehouse" not in a, f"the word None was taken as a warehouse: {a}"


@case("17 a required field's real answer still comes through")
def _():
    rc, a, log = run(build_body(SINGLE, {**BASE, "archetype": "docs"}))
    assert rc == 0, log
    assert a["owning_team"] == "polaris", a


@case("18 free text that really says None is kept")
def _():
    rc, a, log = run(build_body(SINGLE, {**BASE, "repo_description": "None", "archetype": "docs"}))
    assert rc == 0, log
    assert a["repo_description"] == "None", f"a typed word was discarded: {a}"


@case("10 the same label meaning two different fields is refused at startup")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in TEMPLATES.glob("*.yml"):
            (tmp / f.name).write_text(f.read_text())
        clash = yaml.safe_load((tmp / "new-monorepo.yml").read_text())
        for b in clash["body"]:
            if b.get("id") == "repo_name":
                b["id"] = "project_name"
        (tmp / "new-monorepo.yml").write_text(yaml.safe_dump(clash, sort_keys=False))
        rc, a, log = run(build_body(SINGLE, {**BASE, "archetype": "docs"}), templates=tmp)
    assert rc != 0, "a colliding label was merged silently"
    assert "One label must mean one field" in log, log


@case("11 an unrecognisable body is refused rather than guessed at")
def _():
    rc, a, log = run("### Something else\n\nhello\n")
    assert rc != 0, f"a foreign body was parsed: {a}"
    assert "does not match any repository-request form" in log, log


@case("12 a bad repository name is refused")
def _():
    rc, a, log = run(build_body(SINGLE, {**BASE, "repo_name": "Acme Insights", "archetype": "docs"}))
    assert rc != 0, f"accepted: {a}"
    assert "not a usable repository name" in log, log


# ------------------------------------------------- adopting a repo that exists
#
# B-79. The adopt form reuses this parser rather than forking it -- the docstring
# is right that a second copy drifts silently. Two things in the parser were
# hardcoded to the repo-request form and rejected every valid adopt request: the
# required-field list, and a direct a['repo_description'] on the way out. Both now
# read from the form definition instead.
#
# The regression that matters runs the other way. Repo creation is a live path;
# breaking it to add adoption would be a bad trade nobody notices until somebody
# cannot get a repository.

ADOPT = {"repo_name": "ember", "owning_team": "datum-core"}


@case("an adopt request parses")
def _():
    code, args, log = run(build_body(TEMPLATES / "adopt-repo.yml", ADOPT),
                          label="adopt-request")
    assert code == 0, log
    assert args["repo_name"] == "ember", args
    assert args["owning_team"] == "datum-core", args


@case("adoption never asks for a description, and does not need one")
def _():
    # On a retrofit the description feeds only README.md, CLAUDE.md and
    # pyproject.toml, all of which are skip_if_exists, so the answer is
    # discarded. A hardcoded required list rejected the request outright.
    code, _args, log = run(build_body(TEMPLATES / "adopt-repo.yml", ADOPT),
                           label="adopt-request")
    assert code == 0, log
    assert "missing" not in log.lower(), log


@case("an adopt request with no repo name is REFUSED, not crashed")
def _():
    # A non-zero exit is not enough on its own. With the required set emptied the
    # request is accepted and then dies on a KeyError -- identical from outside,
    # and it tells the requester nothing.
    code, _args, log = run(
        build_body(TEMPLATES / "adopt-repo.yml", {"owning_team": "datum-core"}),
        label="adopt-request")
    assert code != 0, "a nameless adopt request was accepted"
    assert "Traceback" not in log, f"crashed instead of refusing:\n{log}"
    assert "missing" in log.lower(), log


@case("the archetype dropdown left alone does not become a real archetype")
def _():
    # Detection decides it. A dropdown nobody touched must not silently override
    # detection with a value no one chose.
    code, args, log = run(build_body(TEMPLATES / "adopt-repo.yml", ADOPT),
                          label="adopt-request")
    assert code == 0, log
    assert args.get("archetype") not in {
        "application", "web-app", "dbt-project", "dlt-pipeline", "gitops", "docs",
    }, args


@case("repo-request is untouched by all of the above  [control case]")
def _():
    code, args, log = run(build_body(TEMPLATES / "new-repo.yml",
                                     {**BASE, "archetype": "application"}))
    assert code == 0, log
    assert args["repo_name"] == "acme-insights", args
    assert args["repo_description"] == BASE["repo_description"], args


# --------------------------------------- the two questions nobody was asked

def main() -> int:
    failed = []
    for name, fn in CASES:
        try:
            fn()
        except AssertionError as exc:
            failed.append((name, str(exc)))
            print(f"FAIL  {name}")
        else:
            print(f"ok    {name}")
    if failed:
        print()
        for name, why in failed:
            print(f"::error::{name}\n{why}\n")
        print(f"{len(failed)} of {len(CASES)} failed")
        return 1
    print(f"\nall {len(CASES)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
