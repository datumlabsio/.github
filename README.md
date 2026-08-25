# datumlabsio/.github — org defaults

This repo holds the files GitHub shows in every other repo in the org that does not have its own copy. It is one of the three org repos named in [DES §2](https://github.com/datumlabsio/datum-standards/blob/main/standards/engineering/README.md).

The three repos, and what each is for:

| Repo | Holds | The test |
|---|---|---|
| `datumlabsio/actions` | Reusable CI workflows and the linter configs they use | Does it run? |
| `datumlabsio/scaffolds` | One template per archetype — what a repo is at birth | Is it copied once, then owned locally? |
| **`datumlabsio/.github`** | Org defaults and the conventions docs | Does GitHub pick it up automatically? |

## What actually reaches other repos

This is worth being precise about, because it is easy to assume too much or too little.

**Served automatically, no commit in the other repo.** GitHub displays these wherever a repo has no file of its own. Nothing is copied, nothing is pushed, and no history changes. Remove a file here and the effect stops immediately.

- `PULL_REQUEST_TEMPLATE.md`
- `ISSUE_TEMPLATE/`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `CODE_OF_CONDUCT.md`
- `profile/README.md` (the org page at github.com/datumlabsio)

A repo with its own version of any of these keeps its own. The default only fills a gap.

**Not served anywhere.** These live here for this repo only, or as documentation:

- `CODEOWNERS` — GitHub reads this per repo. It cannot be inherited. Every repo needs its own; the convention is in [`docs/codeowners-conventions.md`](docs/codeowners-conventions.md).
- `.github/workflows/ci.yml` — this repo's own CI. A thin caller: `docs-ci` for the prose, `workflows-ci` for the automation. It validates `default.json` on every pull request, lints the workflows, and confirms its own pins resolve — all of which used to be done by hand.
- `.github/workflows/conformance-audit.yml` — the scheduled §12 audit. Report-only until B-30 settles which repos the standard binds. What to do when a finding lands: [`docs/conformance-drift.md`](docs/conformance-drift.md).
- `default.json` — the org-wide Renovate preset. Not served automatically either: a repo opts in with a three-line `renovate.json` that extends it, which its scaffold writes at birth. See [`docs/renovate.md`](docs/renovate.md).
- `CLAUDE.md` — not part of GitHub's default-file mechanism. Each repo carries its own, provided by its scaffold.
- Workflows — a repo gets CI by calling `datumlabsio/actions`, not from here.
- Linter and tool configs — those live in `datumlabsio/actions`.

## Layout

```
profile/README.md                   the public org page
.github/PULL_REQUEST_TEMPLATE.md    the PR checklist every repo inherits
.github/ISSUE_TEMPLATE/             issue forms, and the routing in config.yml
SECURITY.md                         reporting a vulnerability, and the secret-leak runbook
CONTRIBUTING.md                     how any repo in the org changes
SUPPORT.md                          where to ask for help
CODE_OF_CONDUCT.md
CODEOWNERS                          owners of this repo
CLAUDE.md                           context for agents working in this repo
```

## Changing something here

A change here shows up in every repo that has no file of its own, so it gets a PR and a review like any other change. Branch, PR, code-owner review. See [CONTRIBUTING.md](CONTRIBUTING.md).

Rules do not change here. Rules live in [`datumlabsio/datum-standards`](https://github.com/datumlabsio/datum-standards) and change by RFC. This repo carries the machinery, not the rules.
